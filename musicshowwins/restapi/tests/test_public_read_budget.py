from unittest.mock import patch

import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from restapi.models import PublicReadBudget
from restapi.throttling import InternalAwareAnonRateThrottle


@pytest.mark.django_db
def test_public_misses_share_budget_across_paths_queries_and_clients(settings):
    settings.INTERNAL_API_SECRET = "test-internal"
    public_headers = {
        "HTTP_X_KPOPWINS_INTERNAL_KEY": "test-internal",
        "HTTP_X_KPOPWINS_PUBLIC_READ": "1",
    }
    with (
        patch.object(InternalAwareAnonRateThrottle, "public_read_limit", 3),
        patch("restapi.throttling.time.time", return_value=120),
    ):
        for number in range(3):
            assert (
                APIClient()
                .get(
                    "/api/v1/artists",
                    {"search": f"unique-{number}"},
                    REMOTE_ADDR=f"203.0.113.{number + 1}",
                    **public_headers,
                )
                .status_code
                == 200
            )
        # A new client, endpoint and query cannot buy another allowance; the
        # catalogue query is never reached after the shared budget is spent.
        with patch("restapi.views.show_queryset") as catalogue:
            response = APIClient().get("/api/v1/shows?new=1", **public_headers)
        assert response.status_code == 429
        assert response["Retry-After"] == "60"
        catalogue.assert_not_called()
        assert PublicReadBudget.objects.get().count == 3
        # Private consumers and authenticated warming retain their allowance.
        assert (
            APIClient()
            .get("/api/v1/shows", HTTP_X_KPOPWINS_INTERNAL_KEY="test-internal")
            .status_code
            == 200
        )

    with patch("restapi.throttling.time.time", return_value=180):
        assert APIClient().get("/api/v1/shows", **public_headers).status_code == 200
    assert PublicReadBudget.objects.get().count == 1


@pytest.mark.django_db
def test_untrusted_public_marker_cannot_select_or_bypass_internal_budget(settings):
    cache.clear()
    settings.INTERNAL_API_SECRET = "test-internal"
    PublicReadBudget.objects.create(scope="frontend", window=2, count=600)
    with patch.object(InternalAwareAnonRateThrottle, "rate", "1/min", create=True):
        client = APIClient()
        headers = {"HTTP_X_KPOPWINS_PUBLIC_READ": "1", "REMOTE_ADDR": "203.0.113.99"}
        assert client.get("/api/v1/shows", **headers).status_code == 200
        assert client.get("/api/v1/shows", **headers).status_code == 429
    assert PublicReadBudget.objects.get().count == 600
    cache.clear()


@pytest.mark.django_db
def test_delayed_request_cannot_roll_back_shared_window(settings):
    settings.INTERNAL_API_SECRET = "test-internal"
    PublicReadBudget.objects.create(scope="frontend", window=3, count=600)
    with patch("restapi.throttling.time.time", return_value=120):
        response = APIClient().get(
            "/api/v1/shows",
            HTTP_X_KPOPWINS_INTERNAL_KEY="test-internal",
            HTTP_X_KPOPWINS_PUBLIC_READ="1",
        )
    assert response.status_code == 429
    budget = PublicReadBudget.objects.get()
    assert (budget.window, budget.count) == (3, 600)
