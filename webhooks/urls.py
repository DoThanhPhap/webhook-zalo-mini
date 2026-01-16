"""URL patterns for webhook endpoints."""
from django.urls import path
from . import views

urlpatterns = [
    path('webhook/zalo/', views.zalo_webhook, name='zalo_webhook'),
    path('health/', views.health_check, name='health_check'),
]
