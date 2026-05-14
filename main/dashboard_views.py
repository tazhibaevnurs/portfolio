from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.views.decorators.http import require_http_methods, require_POST

from main.forms import ClientBenefitForm, ProjectDashboardForm
from main.models import ClientBenefit, PortfolioSettings, Project, TechTag
from main.services.enrichment import enrich_project, save_generated_cv
from main.services.pagespeed import fetch_pagespeed_report


class DashboardLoginView(LoginView):
    template_name = 'dashboard/login.html'
    redirect_authenticated_user = True
    success_url = reverse_lazy('dashboard_project_list')


@login_required
@require_POST
def dashboard_logout(request):
    logout(request)
    return redirect('dashboard_login')


@login_required
def project_list(request):
    projects = Project.objects.all().order_by('sort_order', '-created_at')
    return render(
        request,
        'dashboard/project_list.html',
        {'projects': projects},
    )


@login_required
@require_http_methods(['GET', 'POST'])
def project_create(request):
    if request.method == 'POST':
        form = ProjectDashboardForm(request.POST, request.FILES)
        if form.is_valid():
            project = form.save()
            if request.POST.get('skip_llm'):
                messages.success(request, 'Сохранено без вызова LLM.')
                return redirect('dashboard_project_edit', slug=project.slug)
            ok, msg = enrich_project(project)
            if ok:
                messages.success(request, msg)
            else:
                messages.warning(
                    request,
                    f'Проект сохранён, но LLM не смог заполнить карточку: {msg}',
                )
            return redirect('dashboard_project_edit', slug=project.slug)
    else:
        form = ProjectDashboardForm()
    return render(
        request,
        'dashboard/project_form.html',
        {
            'form': form,
            'title': 'Новый проект',
            'is_create': True,
        },
    )


@login_required
@require_http_methods(['GET', 'POST'])
def project_edit(request, slug):
    project = get_object_or_404(Project, slug=slug)
    if request.method == 'POST':
        form = ProjectDashboardForm(request.POST, request.FILES, instance=project)
        if form.is_valid():
            project = form.save()
            if request.POST.get('skip_llm'):
                messages.success(request, 'Сохранено без вызова LLM.')
                return redirect('dashboard_project_edit', slug=project.slug)
            ok, msg = enrich_project(project)
            if ok:
                messages.success(request, msg)
            else:
                messages.warning(
                    request,
                    f'Сохранено. LLM: {msg}',
                )
            return redirect('dashboard_project_edit', slug=project.slug)
    else:
        form = ProjectDashboardForm(instance=project)
    return render(
        request,
        'dashboard/project_form.html',
        {
            'form': form,
            'project': project,
            'title': f'Редактирование: {project.title}',
            'is_create': False,
        },
    )


@login_required
@require_POST
def project_refresh_pagespeed(request, slug):
    project = get_object_or_404(Project, slug=slug)
    snapshot, err = fetch_pagespeed_report((project.demo_url or '').strip())
    if err:
        messages.error(request, err)
    else:
        project.pagespeed_report = snapshot or {}
        project.save(update_fields=['pagespeed_report', 'updated_at'])
        messages.success(
            request,
            'Метрики PageSpeed обновлены (мобильная и десктопная оценка Lighthouse).',
        )
    return redirect('dashboard_project_edit', slug=project.slug)


@login_required
@require_http_methods(['GET', 'POST'])
def project_delete(request, slug):
    project = get_object_or_404(Project, slug=slug)
    if request.method == 'POST':
        project.delete()
        messages.success(request, 'Проект удалён.')
        return redirect('dashboard_project_list')
    return render(
        request,
        'dashboard/project_confirm_delete.html',
        {'project': project},
    )


@login_required
@require_http_methods(['GET', 'POST'])
def cv_dashboard(request):
    settings_obj = PortfolioSettings.load()
    if request.method == 'POST':
        ok, msg = save_generated_cv()
        if ok:
            messages.success(request, msg)
        else:
            messages.error(request, msg)
        settings_obj = PortfolioSettings.load()
        return HttpResponseRedirect(reverse('dashboard_cv'))
    return render(
        request,
        'dashboard/cv.html',
        {'settings': settings_obj},
    )


def _tech_category_context(cat_key: str) -> dict:
    label_map = dict(TechTag.CATEGORY_CHOICES)
    return {
        'key': cat_key,
        'label': label_map[cat_key],
        'visible': TechTag.objects.filter(
            category=cat_key, show_on_home=True
        ).order_by('sort_order', 'name'),
        'hidden': TechTag.objects.filter(
            category=cat_key, show_on_home=False
        ).order_by('sort_order', 'name'),
    }


@login_required
@require_http_methods(['GET', 'POST'])
def tech_stack_dashboard(request):
    is_ajax = (
        request.POST.get('ajax') == '1'
        or request.headers.get('X-Requested-With', '').lower() == 'xmlhttprequest'
    )

    if request.method == 'POST':
        action = (request.POST.get('action') or '').strip()
        try:
            tag_id = int(request.POST.get('tag_id'))
        except (TypeError, ValueError):
            msg = 'Некорректный тег.'
            if is_ajax:
                return JsonResponse({'ok': False, 'message': msg}, status=400)
            messages.error(request, msg)
            return redirect('dashboard_tech_stack')

        try:
            tag = TechTag.objects.get(pk=tag_id)
        except TechTag.DoesNotExist:
            msg = 'Тег не найден.'
            if is_ajax:
                return JsonResponse({'ok': False, 'message': msg}, status=404)
            messages.error(request, msg)
            return redirect('dashboard_tech_stack')
        if action == 'add':
            tag.show_on_home = True
            tag.save(update_fields=['show_on_home'])
            msg = f'«{tag.name}» снова на главной.'
        elif action == 'remove':
            tag.show_on_home = False
            tag.save(update_fields=['show_on_home'])
            msg = f'«{tag.name}» убран с главной.'
        else:
            msg = 'Неизвестное действие.'
            if is_ajax:
                return JsonResponse({'ok': False, 'message': msg}, status=400)
            messages.error(request, msg)
            return redirect('dashboard_tech_stack')

        cat_key = tag.category
        if is_ajax:
            cat_ctx = _tech_category_context(cat_key)
            html = render_to_string(
                'dashboard/partials/tech_category_controls.html',
                {'cat': cat_ctx},
                request=request,
            )
            return JsonResponse(
                {
                    'ok': True,
                    'message': msg,
                    'category': cat_key,
                    'html': html,
                }
            )

        messages.success(request, msg)
        return redirect('dashboard_tech_stack')

    label_map = dict(TechTag.CATEGORY_CHOICES)
    categories = []
    for key in TechTag.CATEGORY_ORDER:
        categories.append(_tech_category_context(key))
    return render(
        request,
        'dashboard/tech_stack.html',
        {'categories': categories},
    )


@login_required
def benefit_list(request):
    benefits = ClientBenefit.objects.all().order_by('sort_order', 'pk')
    return render(
        request,
        'dashboard/benefits_list.html',
        {'benefits': benefits},
    )


@login_required
@require_http_methods(['GET', 'POST'])
def benefit_create(request):
    if request.method == 'POST':
        form = ClientBenefitForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Преимущество добавлено.')
            return redirect('dashboard_benefit_list')
    else:
        form = ClientBenefitForm()
    return render(
        request,
        'dashboard/benefit_form.html',
        {'form': form, 'title': 'Новое преимущество', 'is_create': True},
    )


@login_required
@require_http_methods(['GET', 'POST'])
def benefit_edit(request, pk):
    benefit = get_object_or_404(ClientBenefit, pk=pk)
    if request.method == 'POST':
        form = ClientBenefitForm(request.POST, instance=benefit)
        if form.is_valid():
            form.save()
            messages.success(request, 'Сохранено.')
            return redirect('dashboard_benefit_list')
    else:
        form = ClientBenefitForm(instance=benefit)
    return render(
        request,
        'dashboard/benefit_form.html',
        {
            'form': form,
            'benefit': benefit,
            'title': f'Редактирование: {benefit.title}',
            'is_create': False,
        },
    )


@login_required
@require_http_methods(['GET', 'POST'])
def benefit_delete(request, pk):
    benefit = get_object_or_404(ClientBenefit, pk=pk)
    if request.method == 'POST':
        title = benefit.title
        benefit.delete()
        messages.success(request, f'«{title}» удалено.')
        return redirect('dashboard_benefit_list')
    return render(
        request,
        'dashboard/benefit_confirm_delete.html',
        {'benefit': benefit},
    )
