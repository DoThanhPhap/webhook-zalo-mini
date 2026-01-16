"""URL configuration for Zalo Webhook project."""
from django.urls import path, include

urlpatterns = [
    path('', include('webhooks.urls')),
]
