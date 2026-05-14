from urllib.parse import quote

from django.db import models
from django.utils.text import slugify


class Project(models.Model):
    """Проект портфолио: видимость на главной + данные с LLM."""

    title = models.CharField(max_length=200, verbose_name='Название (в админке)')
    slug = models.SlugField(
        max_length=220,
        unique=True,
        blank=True,
        help_text='Пусто — создаётся из названия.',
    )

    author_notes = models.TextField(
        blank=True,
        verbose_name='Ваше описание проекта',
        help_text='Что важно рассказать посетителю — учитывается при генерации.',
    )
    git_repository_url = models.URLField(
        max_length=600,
        blank=True,
        verbose_name='URL Git-репозитория',
        help_text='Публичный GitHub/GitLab. По нему подтягивается контекст для LLM.',
    )

    is_visible = models.BooleanField(
        default=True,
        verbose_name='Показывать на главной странице',
    )
    sort_order = models.PositiveIntegerField(
        default=0,
        verbose_name='Порядок сортировки',
        help_text='Меньшее значение — выше в списке.',
    )

    display_title = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='Заголовок на сайте',
    )
    category = models.CharField(max_length=120, blank=True, verbose_name='Категория')
    summary = models.TextField(blank=True, verbose_name='Краткое описание (карточка)')

    stat1_value = models.CharField(max_length=40, blank=True, verbose_name='Показатель 1 — значение')
    stat1_label = models.CharField(max_length=80, blank=True, verbose_name='Показатель 1 — подпись')
    stat2_value = models.CharField(max_length=40, blank=True, verbose_name='Показатель 2 — значение')
    stat2_label = models.CharField(max_length=80, blank=True, verbose_name='Показатель 2 — подпись')

    tech_tags = models.JSONField(
        default=list,
        blank=True,
        verbose_name='Стек (теги)',
        help_text='JSON-массив строк, например: ["Django", "PostgreSQL"]',
    )
    demo_url = models.URLField(
        max_length=600,
        blank=True,
        verbose_name='Ссылка «Посмотреть проект»',
    )
    deployment_platforms = models.JSONField(
        default=list,
        blank=True,
        verbose_name='Платформы',
        help_text='Хостинг, CI/CD, облако (список строк). Показываются на карточке рядом с качеством.',
    )
    pagespeed_report = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='PageSpeed Insights',
        help_text='Мобильная и десктопная оценка Lighthouse через API (как на pagespeed.web.dev).',
    )
    pagespeed_public_report_url = models.URLField(
        max_length=2000,
        blank=True,
        verbose_name='Прямая ссылка на отчёт PageSpeed',
        help_text='Скопируйте URL из адресной строки после анализа на pagespeed.web.dev (необязательно).',
    )
    pagespeed_cwv_note = models.CharField(
        max_length=500,
        blank=True,
        verbose_name='Формулировка про Core Web Vitals',
        help_text='Одна строка для карточки; если пусто — берётся текст из ответа API.',
    )
    pagespeed_diag_good = models.TextField(
        blank=True,
        verbose_name='Что уже хорошо',
        help_text='2–4 короткие фразы; если пусто — подсказки из ответа API.',
    )
    pagespeed_diag_bad = models.TextField(
        blank=True,
        verbose_name='Узкие места',
        help_text='2–4 фразы; если пусто — автоматический выбор из Lighthouse.',
    )
    pagespeed_profile_note = models.CharField(
        max_length=400,
        blank=True,
        verbose_name='Контекст типа проекта',
        help_text='Честное сравнение: например лендинг vs тяжёлый SPA — разные профили метрик.',
    )
    card_image = models.ImageField(
        upload_to='projects/cards/',
        blank=True,
        null=True,
        verbose_name='Скриншот / изображение карточки',
        help_text='Показывается сверху карточки вместо эмодзи. Рекомендуем 1200×600 или широкий кроп.',
    )
    card_image_url = models.URLField(
        max_length=800,
        blank=True,
        verbose_name='Или URL картинки',
        help_text='Если файл не загружен: прямая ссылка на изображение (например с вашего CDN).',
    )
    icon_emoji = models.CharField(max_length=12, default='🚀', blank=True, verbose_name='Иконка (эмодзи)')

    llm_frozen_fields = models.JSONField(
        default=list,
        blank=True,
        verbose_name='Поля карточки без перезаписи LLM',
        help_text='Список имён полей: LLM при обогащении не меняет их.',
    )

    llm_last_error = models.TextField(blank=True, editable=False, verbose_name='Последняя ошибка LLM')
    enriched_at = models.DateTimeField(null=True, blank=True, editable=False, verbose_name='Обогащено LLM')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['sort_order', '-created_at']
        verbose_name = 'Проект'
        verbose_name_plural = 'Проекты'

    def __str__(self):
        return self.display_title or self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title, allow_unicode=True) or 'project'
            slug = base
            n = 2
            while Project.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f'{base}-{n}'
                n += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def card_title(self):
        return self.display_title or self.title

    def link_href(self):
        return self.demo_url or self.git_repository_url or '#'

    def hero_visual_url(self) -> str:
        """URL для превью карточки: загруженный файл или внешняя ссылка."""
        if self.card_image:
            return self.card_image.url
        return (self.card_image_url or '').strip()

    def pagespeed_analysis_url(self) -> str:
        """Ссылка на отчёт в интерфейсе PageSpeed (ручная проверка тем же инструментом)."""
        u = (self.pagespeed_report or {}).get('tested_url') or (self.demo_url or '').strip()
        if not u:
            return ''
        return f'https://pagespeed.web.dev/analysis?url={quote(u, safe="")}'

    def pagespeed_external_url(self) -> str:
        """Полный отчёт: ручной URL или страница анализа по demo URL."""
        return (self.pagespeed_public_report_url or '').strip() or self.pagespeed_analysis_url()

    def pagespeed_mobile_scores(self) -> dict:
        r = self.pagespeed_report or {}
        mobile = r.get('mobile') or {}
        return mobile.get('scores') or {}

    def pagespeed_desktop_scores(self) -> dict:
        r = self.pagespeed_report or {}
        desktop = r.get('desktop') or {}
        return desktop.get('scores') or {}

    def pagespeed_has_scores(self) -> bool:
        m = self.pagespeed_mobile_scores()
        d = self.pagespeed_desktop_scores()
        if any(v is not None for v in m.values()):
            return True
        return any(v is not None for v in d.values())

    @staticmethod
    def _lines_block(text: str) -> list[str]:
        return [ln.strip() for ln in (text or '').splitlines() if ln.strip()]

    def pagespeed_good_bullets(self) -> list[str]:
        manual = self._lines_block(self.pagespeed_diag_good)
        if manual:
            return manual[:4]
        return list((self.pagespeed_report or {}).get('diagnostics', {}).get('good') or [])[:4]

    def pagespeed_bad_bullets(self) -> list[str]:
        manual = self._lines_block(self.pagespeed_diag_bad)
        if manual:
            return manual[:4]
        return list((self.pagespeed_report or {}).get('diagnostics', {}).get('attention') or [])[:4]

    def pagespeed_cwv_line(self) -> str:
        if (self.pagespeed_cwv_note or '').strip():
            return (self.pagespeed_cwv_note or '').strip()
        cwv = (self.pagespeed_report or {}).get('cwv') or {}
        return (cwv.get('summary') or '').strip()

    def pagespeed_measured_at_display(self) -> str:
        raw = (self.pagespeed_report or {}).get('fetched_at')
        if not raw:
            return ''
        # ISO string from API snapshot — показываем дату как есть (UTC).
        if 'T' in raw:
            return raw.split('T')[0]
        return raw[:10] if len(raw) >= 10 else raw

    def show_pagespeed_block(self) -> bool:
        """Показать блок PageSpeed: оценки, CWV, диагностика или ссылка на отчёт."""
        return bool(
            self.pagespeed_has_scores()
            or self.pagespeed_cwv_line()
            or self.pagespeed_good_bullets()
            or self.pagespeed_bad_bullets()
            or (self.pagespeed_public_report_url or '').strip()
            or (self.pagespeed_profile_note or '').strip()
        )

    def pagespeed_lab_hint(self) -> str:
        if not self.pagespeed_has_scores():
            return ''
        r = self.pagespeed_report or {}
        cwv = r.get('cwv') or {}
        if cwv.get('field_available'):
            return ''
        return (
            'Оценки Lighthouse — лабораторные (как в инструменте разработчика), '
            'а не поведение реальных пользователей в сети.'
        )

    PSI_GAUGE_KEYS = (
        ('performance', 'Производительность'),
        ('accessibility', 'Специальные возможности'),
        ('best_practices', 'Рекомендации'),
        ('seo', 'Поисковая оптимизация'),
    )

    @staticmethod
    def _pagespeed_score_tier(value) -> str:
        if value is None:
            return 'na'
        if value >= 90:
            return 'good'
        if value >= 50:
            return 'mid'
        return 'low'

    def pagespeed_gauge_sections(self) -> list[dict]:
        """Блоки «как в PageSpeed»: подпись стратегии + 4 кольца с оценками 0–100."""
        sections: list[dict] = []
        strategies = (
            (self.pagespeed_mobile_scores(), 'Мобильная версия'),
            (self.pagespeed_desktop_scores(), 'Десктоп'),
        )
        for scores, title in strategies:
            if not any(v is not None for v in scores.values()):
                continue
            items = []
            for key, label in self.PSI_GAUGE_KEYS:
                val = scores.get(key)
                items.append(
                    {
                        'label': label,
                        'value': val,
                        'tier': self._pagespeed_score_tier(val),
                    }
                )
            sections.append({'title': title, 'items': items})
        return sections


class PortfolioSettings(models.Model):
    """Singleton: сгенерированное CV и служебные поля."""

    cv_markdown = models.TextField(
        blank=True,
        verbose_name='Резюме (Markdown)',
        help_text='Генерируется из видимых проектов через кнопку в разделе проектов.',
    )
    cv_updated_at = models.DateTimeField(null=True, blank=True, verbose_name='CV обновлено')

    class Meta:
        verbose_name = 'Резюме и настройки портфолио'
        verbose_name_plural = 'Резюме и настройки портфолио'

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return 'Настройки портфолио'


class TechTag(models.Model):
    """Тег технологического стека: пул тегов по категориям и флаг показа на главной."""

    CATEGORY_FULLSTACK = 'fullstack'
    CATEGORY_AI = 'ai'
    CATEGORY_QA = 'qa'
    CATEGORY_PYTHON = 'python'
    CATEGORY_FRONTEND = 'frontend'

    CATEGORY_CHOICES = (
        (CATEGORY_FULLSTACK, 'Full Stack'),
        (CATEGORY_AI, 'AI'),
        (CATEGORY_QA, 'QA'),
        (CATEGORY_PYTHON, 'Python'),
        (CATEGORY_FRONTEND, 'Front-end'),
    )

    CATEGORY_ORDER = (
        CATEGORY_FULLSTACK,
        CATEGORY_AI,
        CATEGORY_QA,
        CATEGORY_PYTHON,
        CATEGORY_FRONTEND,
    )

    name = models.CharField(max_length=120, verbose_name='Название')
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    category = models.CharField(
        max_length=16,
        choices=CATEGORY_CHOICES,
        db_index=True,
        verbose_name='Категория',
    )
    show_on_home = models.BooleanField(
        default=True,
        verbose_name='Показывать на главной',
    )
    sort_order = models.PositiveIntegerField(
        default=0,
        verbose_name='Порядок',
    )

    class Meta:
        ordering = ['category', 'sort_order', 'name']
        verbose_name = 'Тег стека'
        verbose_name_plural = 'Теги стека'

    def __str__(self):
        return f'{self.name} ({self.get_category_display()})'

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name, allow_unicode=True) or 'tag'
            slug = base
            n = 2
            while TechTag.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f'{base}-{n}'
                n += 1
            self.slug = slug
        super().save(*args, **kwargs)


class ClientBenefit(models.Model):
    """Блок «выгоды для заказчика» на главной: редактируется из HTML-дашборда."""

    title = models.CharField(max_length=220, verbose_name='Заголовок')
    body = models.TextField(
        verbose_name='Описание',
        help_text='2–4 предложения. Можно с абзацами.',
    )
    icon = models.CharField(
        max_length=16,
        blank=True,
        verbose_name='Иконка (эмодзи)',
        help_text='Необязательно: один символ или эмодзи.',
    )
    sort_order = models.PositiveIntegerField(
        default=0,
        verbose_name='Порядок',
        help_text='Меньше — выше в списке.',
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Показывать на сайте',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['sort_order', 'pk']
        verbose_name = 'Преимущество для клиента'
        verbose_name_plural = 'Преимущества для клиента'

    def __str__(self):
        return self.title
