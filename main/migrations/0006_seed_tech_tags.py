# Generated manually

from django.db import migrations
from django.utils.text import slugify


def seed_tech_tags(apps, schema_editor):
    TechTag = apps.get_model('main', 'TechTag')
    used_slugs = set()

    def next_slug(name: str) -> str:
        base = slugify(name, allow_unicode=True) or 'tag'
        s = base
        n = 2
        while s in used_slugs:
            s = f'{base}-{n}'
            n += 1
        used_slugs.add(s)
        return s

    # (category, [(name, sort_order), ...])
    blocks = [
        (
            'fullstack',
            [
                ('Django', 10),
                ('PostgreSQL', 20),
                ('Redis', 30),
                ('Docker', 40),
                ('Nginx', 50),
                ('AWS', 60),
                ('CI/CD', 70),
            ],
        ),
        (
            'python',
            [
                ('Python 3.10+', 10),
                ('FastAPI', 20),
                ('Flask', 30),
                ('SQLAlchemy', 40),
                ('AioHTTP', 50),
            ],
        ),
        (
            'frontend',
            [
                ('JavaScript', 10),
                ('React', 20),
                ('Vue.js', 30),
                ('HTML5/CSS3', 40),
                ('Tailwind', 50),
                ('TypeScript', 60),
            ],
        ),
        (
            'ai',
            [
                ('OpenAI API', 10),
                ('GPT-4', 20),
                ('LangChain', 30),
                ('TensorFlow', 40),
                ('NLP', 50),
                ('Vector DB', 60),
            ],
        ),
        (
            'qa',
            [
                ('pytest', 10),
                ('Selenium', 20),
                ('Postman', 30),
                ('Playwright', 40),
                ('Allure', 50),
                ('Locust', 60),
            ],
        ),
    ]

    for cat, items in blocks:
        for name, order in items:
            TechTag.objects.create(
                name=name,
                slug=next_slug(name),
                category=cat,
                show_on_home=True,
                sort_order=order,
            )


def unseed_tech_tags(apps, schema_editor):
    TechTag = apps.get_model('main', 'TechTag')
    TechTag.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0005_tech_tag'),
    ]

    operations = [
        migrations.RunPython(seed_tech_tags, unseed_tech_tags),
    ]
