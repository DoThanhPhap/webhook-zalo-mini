"""Pytest configuration for Django tests."""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')


def pytest_configure():
    """Configure Django settings for tests."""
    from django.conf import settings

    # Override database for testing (use SQLite for speed)
    settings.DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': ':memory:',
        }
    }

    # Disable Redis for tests
    settings.CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        }
    }

    django.setup()
