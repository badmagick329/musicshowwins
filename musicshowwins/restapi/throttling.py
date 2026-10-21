from __future__ import annotations

import time

from django.conf import settings
from django.db.models import F
from django.utils.crypto import constant_time_compare
from rest_framework.throttling import AnonRateThrottle

from .models import PublicReadBudget


class InternalAwareAnonRateThrottle(AnonRateThrottle):
    public_read_limit = 600
    public_read_window_seconds = 60

    def allow_request(self, request, view):
        configured = settings.INTERNAL_API_SECRET
        supplied = request.headers.get("X-KpopWins-Internal-Key", "")
        if (
            request.method == "GET"
            and configured
            and constant_time_compare(supplied, configured)
            and request.headers.get("X-KpopWins-Public-Read") == "1"
        ):
            now = time.time()
            window = int(now // self.public_read_window_seconds)
            self.public_retry_after = max(
                1, (window + 1) * self.public_read_window_seconds - now
            )
            budgets = PublicReadBudget.objects
            budgets.get_or_create(scope="frontend", defaults={"window": window})
            # Conditional updates make both rollover and reservation atomic in
            # PostgreSQL. A delayed old request cannot reset a newer window.
            budgets.filter(scope="frontend", window__lt=window).update(
                window=window, count=0
            )
            return bool(
                budgets.filter(
                    scope="frontend", window=window, count__lt=self.public_read_limit
                ).update(count=F("count") + 1)
            )
        return super().allow_request(request, view)

    def wait(self):
        if hasattr(self, "public_retry_after"):
            return self.public_retry_after
        return super().wait()

    def get_cache_key(self, request, view):
        configured = settings.INTERNAL_API_SECRET
        supplied = request.headers.get("X-KpopWins-Internal-Key", "")
        if (
            request.method == "GET"
            and configured
            and constant_time_compare(supplied, configured)
        ):
            return None
        return super().get_cache_key(request, view)
