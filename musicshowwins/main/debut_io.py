from __future__ import annotations

import re
from datetime import date
from typing import Any

from django.db import transaction

from .models import Artist


class DebutDocumentError(ValueError):
    pass


DEBUT_PATTERN = re.compile(r"^\d{4}(?:-\d{2}(?:-\d{2})?)?$")
ENTRY_FIELDS = {"artist", "debut", "source"}
OPTIONAL_FIELDS = {"solo"}


def _validate_debut(value: Any, index: int) -> str:
    if not isinstance(value, str) or not DEBUT_PATTERN.match(value):
        raise DebutDocumentError(
            f"Entry {index}: debut must be YYYY, YYYY-MM or YYYY-MM-DD."
        )
    parts = [int(part) for part in value.split("-")]
    try:
        debut = date(parts[0], *(parts[1:] + [1, 1])[:2])
    except ValueError as exc:
        raise DebutDocumentError(f"Entry {index}: debut is not a real date.") from exc
    if not date(1950, 1, 1) <= debut <= date.today():
        raise DebutDocumentError(f"Entry {index}: debut is out of range.")
    return value


def _validate(document: Any) -> dict[str, tuple[str, bool]]:
    if (
        not isinstance(document, dict)
        or set(document) != {"version", "debuts"}
        or type(document["version"]) is not int
        or document["version"] != 1
        or not isinstance(document["debuts"], list)
    ):
        raise DebutDocumentError("Expected a version 1 debuts document.")
    debuts: dict[str, tuple[str, bool]] = {}
    for index, entry in enumerate(document["debuts"], 1):
        if (
            not isinstance(entry, dict)
            or not ENTRY_FIELDS <= set(entry) <= ENTRY_FIELDS | OPTIONAL_FIELDS
        ):
            raise DebutDocumentError(
                f"Entry {index}: must contain artist, debut, source and optional solo."
            )
        if entry.get("solo", True) is not True:
            raise DebutDocumentError(f"Entry {index}: solo must be true or omitted.")
        slug, source = entry["artist"], entry["source"]
        if not isinstance(slug, str) or not slug:
            raise DebutDocumentError(f"Entry {index}: artist must be a slug.")
        if not isinstance(source, str) or not source.strip():
            raise DebutDocumentError(f"Entry {index}: source is required.")
        if slug in debuts:
            raise DebutDocumentError(f"Entry {index}: duplicate artist {slug}.")
        debuts[slug] = (_validate_debut(entry["debut"], index), "solo" in entry)
    return debuts


def import_debuts(document: Any, *, dry_run: bool = False) -> int:
    """Make artist debuts match the reviewed file; returns the number changed.

    Artists missing from the file lose their debut, so removing a wrong entry
    withdraws the claim it supported.
    """
    debuts = _validate(document)
    artists = {artist.slug: artist for artist in Artist.objects.all()}
    unknown = sorted(set(debuts) - set(artists))
    if unknown:
        raise DebutDocumentError(f"Unknown artist slug: {unknown[0]}.")
    changed = [
        artist
        for slug, artist in artists.items()
        if (artist.debut, artist.debut_solo) != debuts.get(slug, ("", False))
    ]
    if dry_run:
        return len(changed)
    with transaction.atomic():
        for artist in changed:
            artist.debut, artist.debut_solo = debuts.get(artist.slug, ("", False))
        Artist.objects.bulk_update(changed, ["debut", "debut_solo"])
    return len(changed)
