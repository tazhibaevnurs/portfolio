# Data migration: дополнительный пул тегов (по умолчанию не на главной)

from django.db import migrations
from django.utils.text import slugify


def add_extra_tags(apps, schema_editor):
    TechTag = apps.get_model('main', 'TechTag')
    existing_slugs = set(TechTag.objects.values_list('slug', flat=True))

    def alloc_slug(name: str) -> str:
        base = slugify(name, allow_unicode=True) or 'tag'
        s = base
        n = 2
        while s in existing_slugs:
            s = f'{base}-{n}'
            n += 1
        existing_slugs.add(s)
        return s

    rows = [
        ('fullstack', 'REST API', 100),
        ('fullstack', 'GraphQL', 110),
        ('fullstack', 'gRPC', 120),
        ('fullstack', 'Kubernetes', 130),
        ('fullstack', 'Kafka', 140),
        ('fullstack', 'RabbitMQ', 150),
        ('fullstack', 'MongoDB', 160),
        ('fullstack', 'Elasticsearch', 170),
        ('fullstack', 'Terraform', 180),
        ('fullstack', 'WebSockets', 190),
        ('fullstack', 'JWT', 200),
        ('fullstack', 'OAuth2', 210),
        ('fullstack', 'Microservices', 220),
        ('fullstack', 'Memcached', 230),
        ('fullstack', 'MinIO', 240),
        ('fullstack', 'CDN', 250),
        ('python', 'Celery', 100),
        ('python', 'Django REST Framework', 110),
        ('python', 'Starlette', 120),
        ('python', 'Pydantic', 130),
        ('python', 'httpx', 140),
        ('python', 'Poetry', 150),
        ('python', 'uvicorn', 160),
        ('python', 'Ruff', 170),
        ('python', 'Black', 180),
        ('python', 'mypy', 190),
        ('python', 'Dramatiq', 200),
        ('frontend', 'Next.js', 100),
        ('frontend', 'Vite', 110),
        ('frontend', 'Webpack', 120),
        ('frontend', 'SCSS', 130),
        ('frontend', 'Svelte', 140),
        ('frontend', 'Astro', 150),
        ('frontend', 'Redux Toolkit', 160),
        ('frontend', 'Pinia', 170),
        ('frontend', 'Zustand', 180),
        ('frontend', 'Storybook', 190),
        ('frontend', 'WCAG', 200),
        ('ai', 'Hugging Face', 100),
        ('ai', 'Pinecone', 110),
        ('ai', 'LlamaIndex', 120),
        ('ai', 'RAG', 130),
        ('ai', 'scikit-learn', 140),
        ('ai', 'Anthropic API', 150),
        ('ai', 'Whisper', 160),
        ('ai', 'spaCy', 170),
        ('ai', 'Haystack', 180),
        ('qa', 'Cypress', 100),
        ('qa', 'k6', 110),
        ('qa', 'JMeter', 120),
        ('qa', 'SonarQube', 130),
        ('qa', 'factory_boy', 140),
        ('qa', 'Behave', 150),
        ('qa', 'coverage.py', 160),
        ('qa', 'Robot Framework', 170),
    ]

    for cat, name, order in rows:
        TechTag.objects.create(
            name=name,
            slug=alloc_slug(name),
            category=cat,
            show_on_home=False,
            sort_order=order,
        )


# Пары (category, name) — только записи этой миграции
REMOVED_PAIRS = [
    ('fullstack', 'REST API'),
    ('fullstack', 'GraphQL'),
    ('fullstack', 'gRPC'),
    ('fullstack', 'Kubernetes'),
    ('fullstack', 'Kafka'),
    ('fullstack', 'RabbitMQ'),
    ('fullstack', 'MongoDB'),
    ('fullstack', 'Elasticsearch'),
    ('fullstack', 'Terraform'),
    ('fullstack', 'WebSockets'),
    ('fullstack', 'JWT'),
    ('fullstack', 'OAuth2'),
    ('fullstack', 'Microservices'),
    ('fullstack', 'Memcached'),
    ('fullstack', 'MinIO'),
    ('fullstack', 'CDN'),
    ('python', 'Celery'),
    ('python', 'Django REST Framework'),
    ('python', 'Starlette'),
    ('python', 'Pydantic'),
    ('python', 'httpx'),
    ('python', 'Poetry'),
    ('python', 'uvicorn'),
    ('python', 'Ruff'),
    ('python', 'Black'),
    ('python', 'mypy'),
    ('python', 'Dramatiq'),
    ('frontend', 'Next.js'),
    ('frontend', 'Vite'),
    ('frontend', 'Webpack'),
    ('frontend', 'SCSS'),
    ('frontend', 'Svelte'),
    ('frontend', 'Astro'),
    ('frontend', 'Redux Toolkit'),
    ('frontend', 'Pinia'),
    ('frontend', 'Zustand'),
    ('frontend', 'Storybook'),
    ('frontend', 'WCAG'),
    ('ai', 'Hugging Face'),
    ('ai', 'Pinecone'),
    ('ai', 'LlamaIndex'),
    ('ai', 'RAG'),
    ('ai', 'scikit-learn'),
    ('ai', 'Anthropic API'),
    ('ai', 'Whisper'),
    ('ai', 'spaCy'),
    ('ai', 'Haystack'),
    ('qa', 'Cypress'),
    ('qa', 'k6'),
    ('qa', 'JMeter'),
    ('qa', 'SonarQube'),
    ('qa', 'factory_boy'),
    ('qa', 'Behave'),
    ('qa', 'coverage.py'),
    ('qa', 'Robot Framework'),
]


def remove_extra_tags(apps, schema_editor):
    TechTag = apps.get_model('main', 'TechTag')
    for cat, name in REMOVED_PAIRS:
        TechTag.objects.filter(category=cat, name=name).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0006_seed_tech_tags'),
    ]

    operations = [
        migrations.RunPython(add_extra_tags, remove_extra_tags),
    ]
