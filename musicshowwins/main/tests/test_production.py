import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from django.test import Client


def settings_process(**environment):
    script = environment.pop("SCRIPT", "import musicshowwins.settings")
    env = os.environ.copy()
    env.update(environment)
    env["PYTHONPATH"] = str(Path.cwd() / "musicshowwins")
    return subprocess.run(
        [sys.executable, "-c", script],
        cwd=Path.cwd(),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.parametrize("secret", ["", "dev-only-insecure-secret-key"])
def test_production_settings_reject_empty_and_development_secrets(secret):
    result = settings_process(DEBUG="0", SECRET_KEY=secret)
    assert result.returncode != 0
    assert "SECRET_KEY must be set" in result.stderr


def test_production_settings_parse_hosts_origins_and_secure_database_options():
    script = (
        "import json; import musicshowwins.settings as s; "
        "print(json.dumps({'hosts': s.ALLOWED_HOSTS, "
        "'origins': s.CSRF_TRUSTED_ORIGINS, "
        "'proxy': s.SECURE_PROXY_SSL_HEADER, "
        "'session': s.SESSION_COOKIE_SECURE, 'csrf': s.CSRF_COOKIE_SECURE, "
        "'age': s.DATABASES['default']['CONN_MAX_AGE'], "
        "'health': s.DATABASES['default']['CONN_HEALTH_CHECKS']}))"
    )
    result = settings_process(
        SCRIPT=script,
        DEBUG="0",
        SECRET_KEY="test-only-production-secret-with-enough-entropy",
        ALLOWED_HOSTS="api.example.test, backend localhost",
        CSRF_TRUSTED_ORIGINS="https://api.example.test https://example.test",
        BASE_URL="https://unrelated.example.test",
    )
    assert result.returncode == 0, result.stderr
    values = json.loads(result.stdout)
    assert values == {
        "hosts": ["api.example.test", "backend", "localhost"],
        "origins": ["https://api.example.test", "https://example.test"],
        "proxy": ["HTTP_X_FORWARDED_PROTO", "https"],
        "session": True,
        "csrf": True,
        "age": 60,
        "health": True,
    }


@pytest.mark.django_db
def test_health_returns_success_after_database_query():
    response = Client().get("/health/")
    assert response.status_code == 200
    assert response.json() == {"ok": True}


@pytest.mark.django_db
def test_health_returns_generic_failure_when_database_is_unavailable():
    with patch(
        "musicshowwins.views.connection.cursor",
        side_effect=RuntimeError("secret-db-host"),
    ):
        response = Client().get("/health/")
    assert response.status_code == 503
    assert response.json() == {"ok": False}
    assert b"secret-db-host" not in response.content
