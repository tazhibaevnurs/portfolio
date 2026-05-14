from django.urls import path, include
from . import views

urlpatterns = [
    path('dashboard/', include('main.dashboard_urls')),
    path('', views.home, name='home'),
]
