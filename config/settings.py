"""Django settings for Zalo Webhook project."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# Ensure logs directory exists
LOGS_DIR = BASE_DIR / 'logs'
LOGS_DIR.mkdir(exist_ok=True)

# Security
SECRET_KEY = os.getenv('SECRET_KEY', 'insecure-dev-key-change-in-production')
DEBUG = os.getenv('DEBUG', 'False').lower() in ('true', '1', 'yes')
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# Application definition
INSTALLED_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'webhooks',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'webhooks.middleware.RequestLoggingMiddleware',
    'webhooks.middleware.RateLimitMiddleware',
    'django.middleware.common.CommonMiddleware',
]

ROOT_URLCONF = 'config.urls'
WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

# Database - PostgreSQL
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DATABASE_NAME', 'webhook_db'),
        'USER': os.getenv('DATABASE_USER', 'webhook_user'),
        'PASSWORD': os.getenv('DATABASE_PASSWORD', 'webhook_pass'),
        'HOST': os.getenv('DATABASE_HOST', 'localhost'),
        'PORT': os.getenv('DATABASE_PORT', '5432'),
    }
}

# Cache - Redis
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Ho_Chi_Minh'
USE_I18N = True
USE_TZ = True

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Zalo Webhook Configuration
ZALO_APP_ID = os.getenv('ZALO_APP_ID', '')
ZALO_OA_SECRET_KEY = os.getenv('ZALO_OA_SECRET_KEY', '')
WEBHOOK_TIMESTAMP_TOLERANCE = int(os.getenv('WEBHOOK_TIMESTAMP_TOLERANCE', '300'))
RATE_LIMIT_PER_MINUTE = int(os.getenv('RATE_LIMIT_PER_MINUTE', '100'))
SKIP_SIGNATURE_VERIFICATION = os.getenv('SKIP_SIGNATURE_VERIFICATION', 'false').lower() in ('true', '1', 'yes')

# Security Headers (production)
SECURE_SSL_REDIRECT = not DEBUG
SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'webhooks.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'webhooks': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
    },
}
