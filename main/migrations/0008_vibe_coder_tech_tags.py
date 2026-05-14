# Data migration: теги «вайбкодера» (AI-ассистенты, быстрый шип, современный стек)

from django.db import migrations
from django.utils.text import slugify


# (category, name, sort_order) — по умолчанию не на главной (как в 0007)
ROWS = [
    ('ai', 'Cursor', 300),
    ('ai', 'GitHub Copilot', 310),
    ('ai', 'Windsurf', 320),
    ('ai', 'ChatGPT', 330),
    ('ai', 'MCP', 340),
    ('ai', 'Prompt engineering', 350),
    ('ai', 'CodeRabbit', 360),
    ('ai', 'Claude Code', 370),
    ('fullstack', 'Replit', 300),
    ('fullstack', 'Bolt.new', 310),
    ('fullstack', 'Lovable', 320),
    ('fullstack', 'v0', 330),
    ('fullstack', 'Supabase', 340),
    ('fullstack', 'Railway', 350),
    ('fullstack', 'Vercel', 360),
    ('fullstack', 'Neon', 370),
    ('fullstack', 'Convex', 380),
    ('fullstack', 'T3 Stack', 390),
    ('fullstack', 'Resend', 400),
    ('fullstack', 'PlanetScale', 410),
    ('fullstack', 'PocketBase', 420),
    ('frontend', 'shadcn/ui', 300),
    ('frontend', 'Radix UI', 310),
    ('frontend', 'Framer Motion', 320),
    ('frontend', 'Motion', 330),
    ('frontend', 'TanStack Query', 340),
    ('frontend', 'Chakra UI', 350),
    ('python', 'uv', 300),
    ('python', 'Polars', 310),
    ('python', 'Hatch', 320),
    ('qa', 'Vitest', 300),
    ('qa', 'MSW', 310),
    ('fullstack', 'Bun', 430),
    ('fullstack', 'Deno', 440),
    ('fullstack', 'SvelteKit', 450),
    ('ai', 'Aider', 380),
    ('ai', 'Continue.dev', 390),
]


def add_vibe_tags(apps, schema_editor):
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

    for cat, name, order in ROWS:
        TechTag.objects.create(
            name=name,
            slug=alloc_slug(name),
            category=cat,
            show_on_home=False,
            sort_order=order,
        )


def remove_vibe_tags(apps, schema_editor):
    TechTag = apps.get_model('main', 'TechTag')
    for cat, name, _ in ROWS:
        TechTag.objects.filter(category=cat, name=name).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0007_extra_tech_tags'),
    ]

    operations = [
        migrations.RunPython(add_vibe_tags, remove_vibe_tags),
    ]
