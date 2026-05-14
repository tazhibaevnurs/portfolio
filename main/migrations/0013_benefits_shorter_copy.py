# Короче тексты выгод + акценты (<strong>); правка через safe в шаблоне.

from django.db import migrations

# HTML в body — только курируемый контент из дашборда/миграций.
BODIES = {
    0: (
        '<strong>Объём и сроки</strong> согласуем до старта. '
        '<strong>Короткие статусы</strong> — меньше сюрпризов по бюджету и дедлайнам.'
    ),
    1: (
        'От идеи до продакшена или точечно: <strong>backend, фронт, интеграции, AI</strong>. '
        'Зоны ответственности фиксируем письменно.'
    ),
    2: (
        '<strong>Ревью и тесты на критичных путях</strong>, кратко API и деплой. '
        'Меньше долга — проще развивать продукт дальше.'
    ),
    3: (
        '<strong>MVP и короткие итерации</strong> под метрики бизнеса — '
        'не «полгода без релиза».'
    ),
    4: (
        'Python, Django, FastAPI, облако, CI/CD, AI. '
        '<strong>Инструменты и trade-off</strong> — простым языком, без лишней «магии».'
    ),
    5: (
        '<strong>Один основной контакт</strong>, чек-листы по задачам. '
        'Slack, Telegram, Jira — как договоримся.'
    ),
}


def shorten_benefits(apps, schema_editor):
    ClientBenefit = apps.get_model('main', 'ClientBenefit')
    for sort_order, body in BODIES.items():
        ClientBenefit.objects.filter(sort_order=sort_order).update(body=body)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0012_project_pagespeed_quality_fields'),
    ]

    operations = [
        migrations.RunPython(shorten_benefits, noop),
    ]
