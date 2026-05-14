from django.urls import path

from main.dashboard_views import (
    DashboardLoginView,
    benefit_create,
    benefit_delete,
    benefit_edit,
    benefit_list,
    cv_dashboard,
    dashboard_logout,
    project_create,
    project_delete,
    project_edit,
    project_list,
    project_refresh_pagespeed,
    tech_stack_dashboard,
)

urlpatterns = [
    path('login/', DashboardLoginView.as_view(), name='dashboard_login'),
    path('logout/', dashboard_logout, name='dashboard_logout'),
    path('', project_list, name='dashboard_project_list'),
    path('projects/new/', project_create, name='dashboard_project_create'),
    # str: поддерживает Unicode (slug из slugify(..., allow_unicode=True))
    path(
        'projects/<str:slug>/edit/',
        project_edit,
        name='dashboard_project_edit',
    ),
    path(
        'projects/<str:slug>/delete/',
        project_delete,
        name='dashboard_project_delete',
    ),
    path(
        'projects/<str:slug>/pagespeed/',
        project_refresh_pagespeed,
        name='dashboard_project_pagespeed',
    ),
    path('cv/', cv_dashboard, name='dashboard_cv'),
    path('tech-stack/', tech_stack_dashboard, name='dashboard_tech_stack'),
    path('benefits/', benefit_list, name='dashboard_benefit_list'),
    path('benefits/new/', benefit_create, name='dashboard_benefit_create'),
    path(
        'benefits/<int:pk>/edit/',
        benefit_edit,
        name='dashboard_benefit_edit',
    ),
    path(
        'benefits/<int:pk>/delete/',
        benefit_delete,
        name='dashboard_benefit_delete',
    ),
]
