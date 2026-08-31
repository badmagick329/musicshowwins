from __future__ import annotations

import hashlib
from datetime import date, datetime, timedelta

RETRY_DELAYS = (90, 180, 365, 730)


def no_match_retry_at(
    show_slug: str,
    win_date: date,
    provider: str,
    attempt_number: int,
    confirmed_at: datetime,
) -> datetime:
    if attempt_number < 1:
        raise ValueError("attempt_number must be at least 1")
    base_days = RETRY_DELAYS[min(attempt_number - 1, len(RETRY_DELAYS) - 1)]
    stagger_source = (
        f"{show_slug}|{win_date.isoformat()}|{provider}|{attempt_number}"
    ).encode()
    stagger_days = int.from_bytes(hashlib.sha256(stagger_source).digest()[:4]) % 30
    return confirmed_at + timedelta(days=base_days + stagger_days)
