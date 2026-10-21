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
OPTIONAL_FIELDS = {"solo", "note"}
OMITTED_FIELDS = {"artist", "reason"}


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


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _validate(document: Any) -> tuple[dict[str, tuple[str, bool]], set[str]]:
    """Return the debuts by slug and the slugs deliberately left without one.

    `omitted` records artists whose debut review could not establish a date, so
    a later edit does not fill them from Wikidata without fresh review.
    """
    if (
        not isinstance(document, dict)
        or set(document) != {"version", "debuts", "omitted"}
        or type(document["version"]) is not int
        or document["version"] != 2
        or not isinstance(document["debuts"], list)
        or not isinstance(document["omitted"], list)
    ):
        raise DebutDocumentError("Expected a version 2 debuts document.")
    debuts: dict[str, tuple[str, bool]] = {}
    for index, entry in enumerate(document["debuts"], 1):
        if (
            not isinstance(entry, dict)
            or not ENTRY_FIELDS <= set(entry) <= ENTRY_FIELDS | OPTIONAL_FIELDS
        ):
            raise DebutDocumentError(
                f"Entry {index}: must contain artist, debut, source "
                "and optional solo and note."
            )
        if entry.get("solo", True) is not True:
            raise DebutDocumentError(f"Entry {index}: solo must be true or omitted.")
        slug, source = entry["artist"], entry["source"]
        if not isinstance(slug, str) or not slug:
            raise DebutDocumentError(f"Entry {index}: artist must be a slug.")
        if not _text(source):
            raise DebutDocumentError(f"Entry {index}: source is required.")
        if "note" in entry and not _text(entry["note"]):
            raise DebutDocumentError(f"Entry {index}: note must be text.")
        if slug in debuts:
            raise DebutDocumentError(f"Entry {index}: duplicate artist {slug}.")
        debuts[slug] = (_validate_debut(entry["debut"], index), "solo" in entry)
    omitted: set[str] = set()
    for index, entry in enumerate(document["omitted"], 1):
        if (
            not isinstance(entry, dict)
            or set(entry) != OMITTED_FIELDS
            or not _text(entry["artist"])
            or not _text(entry["reason"])
        ):
            raise DebutDocumentError(
                f"Omitted {index}: must contain artist and reason."
            )
        if entry["artist"] in debuts or entry["artist"] in omitted:
            raise DebutDocumentError(
                f"Omitted {index}: duplicate artist {entry['artist']}."
            )
        omitted.add(entry["artist"])
    return debuts, omitted


def import_debuts(document: Any, *, dry_run: bool = False) -> int:
    """Make artist debuts match the reviewed file; returns the number changed.

    Artists missing from `debuts` lose their debut, so removing a wrong entry
    withdraws the claim it supported. Omitted slugs must still exist, so a merge
    cannot leave a stale judgement behind.
    """
    debuts, omitted = _validate(document)
    artists = {artist.slug: artist for artist in Artist.objects.all()}
    unknown = sorted((set(debuts) | omitted) - set(artists))
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
