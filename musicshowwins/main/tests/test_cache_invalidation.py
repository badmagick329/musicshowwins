from unittest.mock import Mock, patch

import pytest
import requests

from main.cache_invalidation import (
    CacheInvalidationError,
    invalidate_public_archive_cache,
)


def test_cache_invalidation_is_optional_when_fully_unconfigured(settings):
    settings.CACHE_REVALIDATION_URL = ""
    settings.CACHE_REVALIDATION_SECRET = ""
    with patch("main.cache_invalidation.requests.post") as post:
        invalidate_public_archive_cache()
    post.assert_not_called()


def test_cache_invalidation_posts_bearer_secret(settings):
    settings.CACHE_REVALIDATION_URL = "http://frontend:3000/api/revalidate"
    settings.CACHE_REVALIDATION_SECRET = "revalidation-secret"
    response = Mock()
    with patch("main.cache_invalidation.requests.post", return_value=response) as post:
        invalidate_public_archive_cache()
    post.assert_called_once_with(
        "http://frontend:3000/api/revalidate",
        headers={"Authorization": "Bearer revalidation-secret"},
        timeout=10,
    )
    response.raise_for_status.assert_called_once_with()


def test_cache_invalidation_reports_configuration_and_request_failures(settings):
    settings.CACHE_REVALIDATION_URL = "http://frontend:3000/api/revalidate"
    settings.CACHE_REVALIDATION_SECRET = ""
    with pytest.raises(CacheInvalidationError, match="incompletely configured"):
        invalidate_public_archive_cache()

    settings.CACHE_REVALIDATION_SECRET = "revalidation-secret"
    with (
        patch(
            "main.cache_invalidation.requests.post",
            side_effect=requests.RequestException,
        ),
        pytest.raises(CacheInvalidationError, match="Could not invalidate"),
    ):
        invalidate_public_archive_cache()
