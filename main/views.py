from django.shortcuts import render

from main.models import ClientBenefit, Project, TechTag


def home(request):
    projects = Project.objects.filter(is_visible=True).order_by(
        'sort_order', '-created_at'
    )
    label_map = dict(TechTag.CATEGORY_CHOICES)
    categories_obj = {}
    for cat in TechTag.CATEGORY_ORDER:
        qs = TechTag.objects.filter(category=cat, show_on_home=True).order_by(
            'sort_order', 'name'
        )
        if qs.exists():
            categories_obj[cat] = {
                'title': label_map[cat],
                'tags': list(qs.values_list('name', flat=True)),
            }

    tech_stack = {
        'title': 'Технологический стек',
        'subtitle': (
            'Современные инструменты для создания масштабируемых '
            'и высокопроизводительных решений'
        ),
        'categories': categories_obj,
    }
    client_benefits = ClientBenefit.objects.filter(is_active=True).order_by(
        'sort_order', 'pk'
    )
    return render(
        request,
        'index.html',
        {
            'projects': projects,
            'tech_stack': tech_stack,
            'client_benefits': client_benefits,
        },
    )
