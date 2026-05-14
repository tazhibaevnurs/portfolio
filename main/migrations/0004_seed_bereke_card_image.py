from django.conf import settings
from django.core.files import File
from django.db import migrations


def seed_bereke_card_image(apps, schema_editor):
    Project = apps.get_model('main', 'Project')
    path = settings.MEDIA_ROOT / 'projects' / 'cards' / 'bereke-hero-default.jpg'
    if not path.is_file():
        return
    try:
        project = Project.objects.get(slug='bereke-kans')
    except Project.DoesNotExist:
        return
    if project.card_image:
        project.card_image.delete(save=False)
    with path.open('rb') as f:
        project.card_image.save('bereke-hero-default.jpg', File(f), save=True)
    Project.objects.filter(pk=project.pk).update(card_image_url='')


def unseed_bereke_card_image(apps, schema_editor):
    Project = apps.get_model('main', 'Project')
    try:
        project = Project.objects.get(slug='bereke-kans')
    except Project.DoesNotExist:
        return
    if project.card_image:
        project.card_image.delete(save=False)
        project.save()


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0003_project_card_images'),
    ]

    operations = [
        migrations.RunPython(seed_bereke_card_image, unseed_bereke_card_image),
    ]
