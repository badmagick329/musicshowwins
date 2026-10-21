from io import StringIO
from unittest.mock import Mock, call, patch

import pytest
import requests
from django.core.management import call_command

from main.cache_invalidation import (
    CacheInvalidationError,
    CacheInvalidationUnavailable,
    invalidate_public_archive_cache,
)


def test_cache_invalidation_is_optional_when_fully_unconfigured(settings):
    settings.CACHE_REVALIDATION_URL = ""
    settings.CACHE_REVALIDATION_SECRET = ""
    with patch("main.cache_invalidation.requests.post") as post:
        invalidate_public_archive_cache()
    post.assert_not_called()


def test_cache_invalidation_finishes_before_separate_authenticated_warming(settings):
    settings.CACHE_REVALIDATION_URL = "http://frontend:3000/api/revalidate"
    settings.CACHE_REVALIDATION_SECRET = "revalidation-secret"
    invalidated = Mock()
    invalidated.json.return_value = {"revalidated": True}
    warmed = Mock()
    warmed.json.return_value = {"warmed": True}

    def respond(*args, **kwargs):
        if kwargs["params"]["action"] == "invalidate":
            return invalidated
        # The invalidation response must be validated before warming starts.
        invalidated.raise_for_status.assert_called_once_with()
        invalidated.json.assert_called_once_with()
        return warmed

    with patch("main.cache_invalidation.requests.post", side_effect=respond) as post:
        invalidate_public_archive_cache()
    assert post.call_args_list == [
        call(
            "http://frontend:3000/api/revalidate",
            params={"action": action},
            headers={"Authorization": "Bearer revalidation-secret"},
            timeout=10,
        )
        for action in ("invalidate", "warm")
    ]
    warmed.raise_for_status.assert_called_once_with()


@pytest.mark.parametrize("payload", [{}, {"revalidated": False}, [], "invalid"])
def test_failed_invalidation_confirmation_never_starts_warming(settings, payload):
    settings.CACHE_REVALIDATION_URL = "http://frontend:3000/api/revalidate"
    settings.CACHE_REVALIDATION_SECRET = "revalidation-secret"
    response = Mock()
    response.json.return_value = payload
    with (
        patch("main.cache_invalidation.requests.post", return_value=response) as post,
        pytest.raises(CacheInvalidationError, match="did not confirm"),
    ):
        invalidate_public_archive_cache()
    post.assert_called_once()


def test_warming_failure_is_reported_after_successful_invalidation(settings):
    settings.CACHE_REVALIDATION_URL = "http://frontend:3000/api/revalidate"
    settings.CACHE_REVALIDATION_SECRET = "revalidation-secret"
    invalidated = Mock()
    invalidated.json.return_value = {"revalidated": True}
    warmed = Mock()
    warmed.raise_for_status.side_effect = requests.HTTPError("upstream failed")
    with (
        patch(
            "main.cache_invalidation.requests.post", side_effect=[invalidated, warmed]
        ),
        pytest.raises(CacheInvalidationError, match="Could not warm"),
    ):
        invalidate_public_archive_cache()


def test_cache_invalidation_reports_configuration_and_request_failures(settings):
    settings.CACHE_REVALIDATION_URL = "http://frontend:3000/api/revalidate"
    settings.CACHE_REVALIDATION_SECRET = ""
    with pytest.raises(CacheInvalidationError, match="incompletely configured"):
        invalidate_public_archive_cache()

    settings.CACHE_REVALIDATION_SECRET = "revalidation-secret"
    with (
        patch(
            "main.cache_invalidation.requests.post",
            side_effect=requests.ConnectionError,
        ),
        pytest.raises(CacheInvalidationUnavailable, match="endpoint is unavailable"),
    ):
        invalidate_public_archive_cache()

    with (
        patch(
            "main.cache_invalidation.requests.post",
            side_effect=requests.RequestException,
        ),
        pytest.raises(CacheInvalidationError, match="Could not invalidate"),
    ):
        invalidate_public_archive_cache()


def test_deployment_cache_refresh_reports_failure_without_raising():
    stderr = StringIO()
    with patch(
        "main.management.commands.refresh_public_cache.invalidate_public_archive_cache",
        side_effect=CacheInvalidationError("frontend unavailable"),
    ):
        call_command("refresh_public_cache", stderr=stderr)

    assert "Cache refresh failed: frontend unavailable" in stderr.getvalue()
