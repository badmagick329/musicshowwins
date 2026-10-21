from __future__ import annotations

import requests
from django.conf import settings


class CacheInvalidationError(RuntimeError):
    pass


class CacheInvalidationUnavailable(CacheInvalidationError):
    """The frontend endpoint could not be reached."""


def invalidate_public_archive_cache() -> None:
    url = settings.CACHE_REVALIDATION_URL
    secret = settings.CACHE_REVALIDATION_SECRET
    if not url and not secret:
        return
    if not url or not secret:
        raise CacheInvalidationError("Cache invalidation is incompletely configured.")

    # Next flushes tag invalidation at request completion. Warming in that same
    # request creates entries that the pending invalidation immediately expires.
    for action, confirmation in (("invalidate", "revalidated"), ("warm", "warmed")):
        try:
            response = requests.post(
                url,
                params={"action": action},
                headers={"Authorization": f"Bearer {secret}"},
                timeout=10,
            )
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict) or payload.get(confirmation) is not True:
                raise CacheInvalidationError(
                    f"Frontend did not confirm cache action '{action}'."
                )
        except (requests.ConnectionError, requests.Timeout) as exc:
            raise CacheInvalidationUnavailable(
                f"The frontend cache endpoint is unavailable during '{action}'."
            ) from exc
        except (requests.RequestException, ValueError) as exc:
            raise CacheInvalidationError(
                f"Could not {action} the public archive cache."
            ) from exc
