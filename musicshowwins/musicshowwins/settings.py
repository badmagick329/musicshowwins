"""Django settings for the music show wins project."""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

# The Django project remains under ``musicshowwins/`` while project metadata and
# environment files live at the repository root.
BASE_DIR = Path(__file__).resolve().parent.parent
BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:8000")
WIKI_AGENT = os.environ.get(
    "WIKI_AGENT",
    "KpopWins/0.1 (https://github.com/badmagick329/musicshowwins/issues)",
)
DB_HOST = os.environ.get("DB_HOST", "127.0.0.1")
DISCORD_CORRECTIONS_WEBHOOK_URL = os.environ.get("DISCORD_CORRECTIONS_WEBHOOK_URL", "")


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.1/howto/deployment/checklist/

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-insecure-secret-key")
DEBUG = os.environ.get("DEBUG", "1").lower() in {"1", "true", "yes", "on"}


def split_environment_list(value: str) -> list[str]:
    return value.replace(",", " ").split()


if not DEBUG and (
    not SECRET_KEY.strip() or SECRET_KEY == "dev-only-insecure-secret-key"
):
    raise ImproperlyConfigured(
        "SECRET_KEY must be set to a non-development value when DEBUG=0"
    )

ALLOWED_HOSTS = split_environment_list(
    os.environ.get("ALLOWED_HOSTS", "127.0.0.1 localhost")
)

PAGE_SIZE = 100

# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "drf_spectacular",
    "main",
    "restapi",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "musicshowwins.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [(BASE_DIR / "templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "musicshowwins.wsgi.application"
CSRF_TRUSTED_ORIGINS = split_environment_list(
    os.environ.get("CSRF_TRUSTED_ORIGINS", BASE_URL)
)


# Database
# https://docs.djangoproject.com/en/4.1/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": os.environ.get("DB_ENGINE", "django.db.backends.postgresql"),
        "NAME": os.environ.get("DB_NAME", "musicshowwins"),
        "USER": os.environ.get("DB_USER", "musicshowwins"),
        "PASSWORD": os.environ.get("DB_PASSWORD", "musicshowwins"),
        "HOST": DB_HOST,
        "PORT": os.environ.get("DB_PORT", "5432"),
        "CONN_MAX_AGE": 60 if not DEBUG else 0,
        "CONN_HEALTH_CHECKS": not DEBUG,
    }
}

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": PAGE_SIZE,
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "DEFAULT_THROTTLE_CLASSES": ["rest_framework.throttling.AnonRateThrottle"],
    "DEFAULT_THROTTLE_RATES": {"anon": "60/min"},
    "NUM_PROXIES": 1 if not DEBUG else None,
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Music Show Wins API",
    "DESCRIPTION": "Read-only K-pop music show wins data.",
    "VERSION": "1.0.0",
}

# Password validation
# https://docs.djangoproject.com/en/4.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
        ),
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

USE_X_FORWARDED_HOST = True
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# Internationalization
# https://docs.djangoproject.com/en/4.1/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.1/howto/static-files/

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
if not DEBUG:
    STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
        },
    }

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        }
    },
}

# Default primary key field type
# https://docs.djangoproject.com/en/4.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
