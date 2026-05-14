from django.contrib import admin
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import path

from main.models import PortfolioSettings, Project
from main.services.enrichment import enrich_project, save_generated_cv


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    change_list_template = 'admin/main/project/change_list.html'
    list_display = (
        'title',
        'display_title',
        'is_visible',
        'sort_order',
        'enriched_at',
        'git_repository_url',
    )
    list_filter = ('is_visible',)
    list_editable = ('sort_order', 'is_visible')
    search_fields = ('title', 'display_title', 'slug', 'author_notes')
    actions = ('action_enrich_with_llm',)

    fieldsets = (
        (
            'Проект',
            {
                'fields': (
                    'title',
                    'slug',
                    'author_notes',
                    'git_repository_url',
                    'is_visible',
                    'sort_order',
                ),
            },
        ),
        (
            'Карточка на сайте (заполнить вручную или через LLM)',
            {
                'fields': (
                    'display_title',
                    'category',
                    'summary',
                    ('stat1_value', 'stat1_label'),
                    ('stat2_value', 'stat2_label'),
                    'tech_tags',
                    'demo_url',
                    'card_image',
                    'card_image_url',
                    'icon_emoji',
                ),
            },
        ),
        (
            'Состояние LLM',
            {
                'fields': ('enriched_at', 'llm_last_error', 'llm_frozen_fields'),
                'classes': ('collapse',),
            },
        ),
    )
    readonly_fields = ('enriched_at', 'llm_last_error')

    @admin.action(description='Заполнить карточку через LLM (репозиторий + заметки)')
    def action_enrich_with_llm(self, request, queryset):
        ok = err = 0
        for obj in queryset:
            success, msg = enrich_project(obj)
            if success:
                ok += 1
            else:
                err += 1
                self.message_user(request, f'{obj}: {msg}', level=messages.ERROR)
        if ok:
            self.message_user(
                request,
                f'LLM: успешно {ok} из {queryset.count()}.',
                level=messages.SUCCESS,
            )

    def get_urls(self):
        urls = super().get_urls()
        return [
            path(
                'generate-cv/',
                self.admin_site.admin_view(self._generate_cv),
                name='main_project_generate_cv',
            ),
        ] + urls

    def _generate_cv(self, request):
        if request.method != 'POST':
            return redirect('admin:main_project_changelist')
        success, msg = save_generated_cv()
        if success:
            self.message_user(request, msg, level=messages.SUCCESS)
        else:
            self.message_user(request, msg, level=messages.ERROR)
        return redirect('admin:main_project_changelist')

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['show_cv_button'] = True
        return super().changelist_view(request, extra_context=extra_context)


@admin.register(PortfolioSettings)
class PortfolioSettingsAdmin(admin.ModelAdmin):
    readonly_fields = ('cv_updated_at',)

    def has_add_permission(self, request):
        return not PortfolioSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    fieldsets = (
        (
            None,
            {
                'fields': ('cv_markdown', 'cv_updated_at'),
                'description': 'CV создаётся кнопкой «Сгенерировать CV» в списке проектов.',
            },
        ),
    )
