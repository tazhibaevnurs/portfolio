# Data migration: популярные MCP-серверы (Model Context Protocol)

from django.db import migrations
from django.utils.text import slugify

# Категория AI; show_on_home=False — выбор в дашборде
ROWS = [
    ('ai', 'MCP: Filesystem', 500),
    ('ai', 'MCP: Git', 510),
    ('ai', 'MCP: GitHub', 520),
    ('ai', 'MCP: GitLab', 530),
    ('ai', 'MCP: Google Drive', 540),
    ('ai', 'MCP: Gmail', 550),
    ('ai', 'MCP: Slack', 560),
    ('ai', 'MCP: Discord', 570),
    ('ai', 'MCP: Microsoft Teams', 580),
    ('ai', 'MCP: PostgreSQL', 590),
    ('ai', 'MCP: SQLite', 600),
    ('ai', 'MCP: MySQL', 610),
    ('ai', 'MCP: Redis', 620),
    ('ai', 'MCP: MongoDB', 630),
    ('ai', 'MCP: Snowflake', 640),
    ('ai', 'MCP: Elasticsearch', 650),
    ('ai', 'MCP: Brave Search', 660),
    ('ai', 'MCP: Fetch', 670),
    ('ai', 'MCP: Puppeteer', 680),
    ('ai', 'MCP: Playwright', 690),
    ('ai', 'MCP: Memory', 700),
    ('ai', 'MCP: Sequential Thinking', 710),
    ('ai', 'MCP: Time', 720),
    ('ai', 'MCP: Firecrawl', 730),
    ('ai', 'MCP: Context7', 740),
    ('ai', 'MCP: Supabase', 750),
    ('ai', 'MCP: Stripe', 760),
    ('ai', 'MCP: Sentry', 770),
    ('ai', 'MCP: Notion', 780),
    ('ai', 'MCP: Linear', 790),
    ('ai', 'MCP: Figma', 800),
    ('ai', 'MCP: Jira', 810),
    ('ai', 'MCP: Confluence', 820),
    ('ai', 'MCP: Kubernetes', 830),
    ('ai', 'MCP: Docker', 840),
    ('ai', 'MCP: AWS', 850),
    ('ai', 'MCP: Cloudflare', 860),
    ('ai', 'MCP: Vercel', 870),
    ('ai', 'MCP: Netlify', 880),
    ('ai', 'MCP: Grafana', 890),
    ('ai', 'MCP: Prometheus', 900),
    ('ai', 'MCP: Datadog', 910),
    ('ai', 'MCP: Twilio', 920),
    ('ai', 'MCP: Airtable', 930),
    ('ai', 'MCP: Shopify', 940),
    ('ai', 'MCP: HubSpot', 950),
    ('ai', 'MCP: Perplexity', 960),
    ('ai', 'MCP: Obsidian', 970),
    ('ai', 'MCP: Apify', 980),
    ('ai', 'MCP: Browserbase', 990),
    ('ai', 'MCP: n8n', 1000),
    ('ai', 'MCP: Zapier', 1010),
    ('ai', 'MCP: Turborepo', 1020),
    ('ai', 'MCP: Nx', 1030),
]


def add_mcp_tags(apps, schema_editor):
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


def remove_mcp_tags(apps, schema_editor):
    TechTag = apps.get_model('main', 'TechTag')
    for cat, name, _ in ROWS:
        TechTag.objects.filter(category=cat, name=name).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0008_vibe_coder_tech_tags'),
    ]

    operations = [
        migrations.RunPython(add_mcp_tags, remove_mcp_tags),
    ]
