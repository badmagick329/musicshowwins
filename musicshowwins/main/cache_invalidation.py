from __future__ import annotations

import requests
from django.conf import settings


class CacheInvalidationError(RuntimeError):
    pass


def invalidate_public_archive_cache() -> None:
    url = settings.CACHE_REVALIDATION_URL
    secret = settings.CACHE_REVALIDATION_SECRET
    if not url and not secret:
        return
    if not url or not secret:
        raise CacheInvalidationError("Cache invalidation is incompletely configured.")

    try:
        response = requests.post(
            url,
            headers={"Authorization": f"Bearer {secret}"},
            timeout=10,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise CacheInvalidationError(
            "Could not invalidate the public archive cache."
        ) from exc
