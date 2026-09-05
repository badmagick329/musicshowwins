from __future__ import annotations

import secrets

from django.conf import settings
from rest_framework.throttling import AnonRateThrottle


class InternalAwareAnonRateThrottle(AnonRateThrottle):
    def get_cache_key(self, request, view):
        configured = settings.INTERNAL_API_SECRET
        supplied = request.headers.get("X-KpopWins-Internal-Key", "")
        if (
            request.method == "GET"
            and configured
            and secrets.compare_digest(supplied, configured)
        ):
            return None
        return super().get_cache_key(request, view)
