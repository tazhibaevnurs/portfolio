from __future__ import annotations

from django.conf import settings
from django.utils import timezone

from main.models import Project
from main.services.llm import complete_json
from main.services.repo_fetch import fetch_github_context

# Поля карточки, которые LLM может заполнить; совпадают с JSON-ключами (кроме demo_url ↔ demo_link).
LLM_CARD_FIELD_KEYS = (
    'display_title',
    'category',
    'summary',
    'stat1_value',
    'stat1_label',
    'stat2_value',
    'stat2_label',
    'tech_tags',
    'demo_url',
    'icon_emoji',
)
_ALL_CARD_FROZEN = frozenset(LLM_CARD_FIELD_KEYS)


PROJECT_SYSTEM = """Ты помощник для оформления карточек портфолио разработчика.
Отвечай СТРОГО одним JSON-объектом без Markdown и пояснений. Ключи:
{
  "display_title": "короткий привлекательный заголовок на русском",
  "category": "одна строка категории на английском или короткий tech-ярлык",
  "summary": "2-4 предложения для карточки на сайте на русском, деловой тон",
  "stat1_value": "короткое значение метрики",
  "stat1_label": "подпись метрики на русском",
  "stat2_value": "вторая метрика",
  "stat2_label": "подпись",
  "tech_tags": ["до 6 технологий строками"],
  "demo_link": "если видишь URL сайта или Play Store — вставь, иначе пустая строка",
  "icon_emoji": "один подходящий эмодзи"
}
Если demo_link неизвестен — используй пустую строку. tech_tags — массив из 3-6 строк."""


def enrich_project(project: Project) -> tuple[bool, str]:
    """Fetch repo context, call LLM, save fields. Returns (success, message)."""
    frozen = frozenset(project.llm_frozen_fields or [])
    if frozen >= _ALL_CARD_FROZEN:
        project.llm_last_error = ''
        project.save(update_fields=['llm_last_error', 'updated_at'])
        return True, 'Все поля карточки отмечены «Не менять LLM» — запрос к API не отправлялся.'

    repo_ctx = ''
    if project.git_repository_url:
        token = getattr(settings, 'GITHUB_TOKEN', '') or None
        repo_ctx = fetch_github_context(project.git_repository_url, github_token=token)

    user_text = f"""Внутреннее название: {project.title}
Заметки автора (важно учесть):
{project.author_notes or '(нет)'}
URL репозитория: {project.git_repository_url or '(нет)'}

Контекст из репозитория (может быть пустым, если репозиторий недоступен):
{(repo_ctx or '(контекст не получен — опирайся на заметки и название)')[:45_000]}
"""

    data, err = complete_json(PROJECT_SYSTEM, user_text)
    if err:
        project.llm_last_error = err
        project.save(update_fields=['llm_last_error', 'updated_at'])
        return False, err

    def pick(key: str, default: str = '') -> str:
        v = data.get(key)
        if v is None:
            return default
        return str(v).strip() or default

    tags = data.get('tech_tags')
    if not isinstance(tags, list):
        tags = []
    tags = [str(t).strip() for t in tags if str(t).strip()][:8]

    if 'display_title' not in frozen:
        project.display_title = pick('display_title', project.title)[:200]
    if 'category' not in frozen:
        project.category = pick('category')[:120]
    if 'summary' not in frozen:
        project.summary = pick('summary')[:4000]
    if 'stat1_value' not in frozen:
        project.stat1_value = pick('stat1_value')[:40]
    if 'stat1_label' not in frozen:
        project.stat1_label = pick('stat1_label')[:80]
    if 'stat2_value' not in frozen:
        project.stat2_value = pick('stat2_value')[:40]
    if 'stat2_label' not in frozen:
        project.stat2_label = pick('stat2_label')[:80]
    if 'tech_tags' not in frozen:
        project.tech_tags = tags
    if 'demo_url' not in frozen:
        demo = pick('demo_link')
        if demo and (demo.startswith('http://') or demo.startswith('https://')):
            project.demo_url = demo[:600]
        elif not project.demo_url:
            project.demo_url = ''
    if 'icon_emoji' not in frozen:
        project.icon_emoji = pick('icon_emoji', '🚀')[:12] or '🚀'
    project.enriched_at = timezone.now()
    project.llm_last_error = ''
    project.save()
    skipped = ', '.join(sorted(frozen)) if frozen else ''
    msg = 'Поля успешно заполнены LLM.'
    if skipped:
        msg += f' (без изменения зафиксированных: {skipped})'
    return True, msg


CV_SYSTEM = """Ты карьерный консультант для IT-резюме.
Составь профессиональное резюме разработчика на РУССКОМ языке в формате Markdown.
Структура: краткое резюме (2-3 предложения), ключевые компетенции (список), опыт/проекты (по каждому проекту 2-4 пункта достижений), стек технологий.
Без выдуманных компаний — опирайся только на переданные данные проектов.
Верни СТРОГО JSON с единственным ключом: {"markdown": "..."} — текст резюме внутри строки с переносами \\n."""


def generate_cv_markdown() -> tuple[str | None, str | None]:
    """Build CV from all projects in DB. Returns (markdown, error)."""
    projects = list(Project.objects.all().order_by('sort_order', '-created_at'))
    lines: list[str] = []
    for p in projects:
        title = p.display_title or p.title
        st = ', '.join(p.tech_tags or [])
        sumy = p.summary or p.author_notes
        on_site = 'показывается на главной' if p.is_visible else 'скрыт на главной'
        lines.append(f'- {title} ({on_site}): {sumy or "—"}. Стек: {st}')

    payload = '\n'.join(lines) if lines else '(в базе пока нет проектов)'

    user = f"""Проекты в базе данных:\n{payload}\n"""

    data, err = complete_json(CV_SYSTEM, user)
    if err:
        return None, err

    md = data.get('markdown')
    if isinstance(md, str) and md.strip():
        return md.strip(), None

    # fallback if model returned loose JSON
    if data and not md:
        try:
            import json as json_lib

            raw = json_lib.dumps(data, ensure_ascii=False)
            if len(raw) > 100:
                return raw, None
        except Exception:
            pass
    return None, 'В ответе LLM нет поля markdown.'


def save_generated_cv() -> tuple[bool, str]:
    from main.models import PortfolioSettings

    md, err = generate_cv_markdown()
    if err or md is None:
        return False, err or 'Неизвестная ошибка CV.'

    settings_obj = PortfolioSettings.load()
    settings_obj.cv_markdown = md
    settings_obj.cv_updated_at = timezone.now()
    settings_obj.save()
    return True, 'Резюме (CV) обновлено. Откройте «Резюме и настройки портфолио» для просмотра.'
