"""Fast, isolated settings used by the pytest and CI suites."""

from .settings import *  # noqa: F401,F403

DEBUG = False
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}
CSRF_TRUSTED_ORIGINS = []
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
