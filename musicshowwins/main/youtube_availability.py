"""Keep published YouTube references in step with what YouTube still serves.

Reviewed clips, including fan uploads, can be deleted, made private or blocked
after publication. Production owns availability: this check only moves
references between ``active`` and ``unavailable`` and never adds, withdraws or
deletes one, so a clip that comes back is restored without another review.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import requests
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from main.models import WinReference

BATCH_SIZE = 50
PLAYABLE_PRIVACY = {"public", "unlisted"}


class YouTubeAvailabilityError(RuntimeError):
    pass


@dataclass
class AvailabilitySummary:
    checked: int = 0
    became_unavailable: int = 0
    restored: int = 0

    @property
    def changed(self) -> bool:
        return bool(self.became_unavailable or self.restored)


def _playable_ids(session: requests.Session, api_key: str, ids: list[str]) -> set[str]:
    try:
        response = session.get(
            f"{settings.YOUTUBE_API_BASE_URL}/videos",
            params={"part": "status", "id": ",".join(ids), "key": api_key},
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise YouTubeAvailabilityError("YouTube video lookup failed.") from exc
    items = payload.get("items")
    if not isinstance(items, list):
        raise YouTubeAvailabilityError("YouTube returned an unexpected response.")
    playable = set()
    for item in items:
        status = item.get("status") or {}
        # Rejected or failed uploads can still be listed while nobody can watch them.
        if status.get("privacyStatus") in PLAYABLE_PRIVACY and status.get(
            "uploadStatus", "processed"
        ) in {"processed", "uploaded"}:
            playable.add(item.get("id"))
    return playable


def check_youtube_references(
    api_key: str,
    *,
    dry_run: bool = False,
    session: requests.Session | None = None,
    now: datetime | None = None,
) -> AvailabilitySummary:
    session = session or requests.Session()
    now = now or timezone.now()
    references = list(
        WinReference.objects.filter(
            provider="youtube",
            status__in=(WinReference.Status.ACTIVE, WinReference.Status.UNAVAILABLE),
        )
        .exclude(external_id="")
        .order_by("pk")
    )
    summary = AvailabilitySummary(checked=len(references))
    video_ids = sorted({reference.external_id for reference in references})
    playable: set[str] = set()
    # Look everything up before writing so a failed batch never leaves a partial update.
    for start in range(0, len(video_ids), BATCH_SIZE):
        playable |= _playable_ids(
            session, api_key, video_ids[start : start + BATCH_SIZE]
        )

    with transaction.atomic():
        for reference in references:
            status = (
                WinReference.Status.ACTIVE
                if reference.external_id in playable
                else WinReference.Status.UNAVAILABLE
            )
            if status != reference.status:
                if status == WinReference.Status.UNAVAILABLE:
                    summary.became_unavailable += 1
                else:
                    summary.restored += 1
            if dry_run:
                continue
            reference.status = status
            reference.last_verified_at = now
            reference.save(update_fields=("status", "last_verified_at", "updated_at"))
    return summary
