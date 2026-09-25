"""Apply the operator's winner-presence manifest to catalogue wins.

The manifest is derived offline from r/kpop episode lineups, so it is untrusted
input and is validated here. It only sets ``Win.performed`` for wins it names;
wins it omits keep their value, and wins missing from this catalogue are
reported rather than failing the import, because presence is a supplementary
fact and the operator catalogue can briefly run ahead of production.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from django.db import transaction
from django.utils.dateparse import parse_date

from main.models import Win

DOCUMENT_VERSION = 1


class PresenceDocumentError(ValueError):
    pass


@dataclass
class PresenceSummary:
    updated: int = 0
    unchanged: int = 0
    missing: int = 0


def _validate(document: Any) -> dict[tuple[str, date], bool]:
    if not isinstance(document, dict) or set(document) != {"version", "wins"}:
        raise PresenceDocumentError(
            "The document must be an object with version and wins."
        )
    if type(document["version"]) is not int or document["version"] != DOCUMENT_VERSION:
        raise PresenceDocumentError("Unsupported document version; expected 1.")
    if not isinstance(document["wins"], list):
        raise PresenceDocumentError("wins must be an array.")
    entries: dict[tuple[str, date], bool] = {}
    for index, raw in enumerate(document["wins"], start=1):
        if (
            not isinstance(raw, dict)
            or set(raw) != {"show", "date", "performed"}
            or not isinstance(raw["show"], str)
            or not isinstance(raw["date"], str)
            or not isinstance(raw["performed"], bool)
        ):
            raise PresenceDocumentError(
                f"Win {index} must have text show and date and a boolean performed."
            )
        win_date = parse_date(raw["date"])
        if win_date is None or win_date.isoformat() != raw["date"]:
            raise PresenceDocumentError(f"Win {index}: date must use YYYY-MM-DD.")
        key = (raw["show"], win_date)
        if key in entries:
            raise PresenceDocumentError(f"Win {index} duplicates an earlier entry.")
        entries[key] = raw["performed"]
    return entries


def import_presence(document: Any, *, dry_run: bool = False) -> PresenceSummary:
    entries = _validate(document)
    summary = PresenceSummary()
    with transaction.atomic():
        wins = {
            (win.show.slug, win.date): win
            for win in Win.objects.select_related("show").select_for_update(
                of=("self",)
            )
        }
        for key, performed in entries.items():
            win = wins.get(key)
            if win is None:
                summary.missing += 1
            elif win.performed == performed:
                summary.unchanged += 1
            else:
                summary.updated += 1
                if not dry_run:
                    win.performed = performed
                    win.save(update_fields=("performed",))
    return summary
