from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.db import transaction

from .models import Win, WinMoment, WinReference, normalize_key


class MomentDocumentError(ValueError):
    pass


@dataclass(frozen=True)
class ResolvedMoment:
    entry: dict[str, Any]
    win: Win


MOMENT_FIELDS = {
    "matching_state",
    "status",
    "pending_reason",
    "event",
    "heading",
    "body",
    "citations",
}
CITATION_FIELDS = {"provider", "publisher_name", "title", "url"}
TEXT_LIMITS = {
    "heading": 300,
    "body": None,
    "provider": 80,
    "publisher_name": 300,
    "title": 500,
    "url": 2048,
}


def validate_selected_citations(
    win_id: int, status: str, citations, *, require_active: bool
) -> None:
    citations = list(citations)
    if any(citation.win_id != win_id for citation in citations):
        raise ValueError("Every citation must belong to the same win as the moment.")
    if (
        status == WinMoment.Status.PUBLISHED
        and require_active
        and not any(
            citation.reference_type == WinReference.ReferenceType.ARTICLE
            and citation.status == WinReference.Status.ACTIVE
            for citation in citations
        )
    ):
        raise ValueError("Publishing requires an active article citation.")


def _required_text(data: dict[str, Any], field: str, index: int) -> str:
    value = data.get(field)
    if not isinstance(value, str) or not value.strip():
        raise MomentDocumentError(f"Entry {index}: {field} must be a non-empty string.")
    value = value.strip()
    limit = TEXT_LIMITS[field]
    if limit is not None and len(value) > limit:
        raise MomentDocumentError(f"Entry {index}: {field} is too long.")
    return value


def _validate_entry(raw: Any, index: int) -> dict[str, Any]:
    """Use the same normalized values for validation, resolution and persistence."""
    if not isinstance(raw, dict):
        raise MomentDocumentError(f"Entry {index}: must be an object.")
    unknown = set(raw) - MOMENT_FIELDS
    if unknown:
        raise MomentDocumentError(
            f"Entry {index}: contains unknown field {sorted(unknown)[0]}."
        )
    matching_state = raw.get("matching_state")
    if matching_state not in ("matched", "pending"):
        raise MomentDocumentError(f"Entry {index}: state must be matched or pending.")
    if raw.get("status") not in WinMoment.Status.values:
        raise MomentDocumentError(f"Entry {index}: status must be draft or published.")
    event = raw.get("event")
    if not isinstance(event, dict) or set(event) != {
        "show",
        "date",
        "artist",
        "song",
    }:
        raise MomentDocumentError(
            f"Entry {index}: event must contain show, date, artist and song."
        )
    for field in ("show", "date", "artist", "song"):
        if not isinstance(event[field], str) or not event[field].strip():
            raise MomentDocumentError(f"Entry {index}: event.{field} is required.")
    event = {field: value.strip() for field, value in event.items()}
    try:
        event_date = date.fromisoformat(event["date"])
    except ValueError as exc:
        raise MomentDocumentError(
            f"Entry {index}: event.date must use YYYY-MM-DD."
        ) from exc
    if event_date.isoformat() != event["date"]:
        raise MomentDocumentError(f"Entry {index}: event.date must use YYYY-MM-DD.")
    for field, limit in (("show", 80), ("artist", 200), ("song", 300)):
        if len(event[field]) > limit:
            raise MomentDocumentError(f"Entry {index}: event.{field} is too long.")
    heading = _required_text(raw, "heading", index)
    body = _required_text(raw, "body", index)
    citations = raw.get("citations")
    if not isinstance(citations, list) or not citations:
        raise MomentDocumentError(
            f"Entry {index}: citations must be a non-empty array."
        )
    normalized_citations = []
    for citation_index, citation in enumerate(citations, 1):
        if not isinstance(citation, dict) or set(citation) != CITATION_FIELDS:
            raise MomentDocumentError(
                f"Entry {index}, citation {citation_index}: invalid fields."
            )
        citation = {
            field: _required_text(citation, field, index) for field in CITATION_FIELDS
        }
        citation["provider"] = citation["provider"].lower()
        try:
            URLValidator(schemes=("http", "https"))(citation["url"])
        except ValidationError as exc:
            raise MomentDocumentError(
                f"Entry {index}, citation {citation_index}: "
                "url must be a valid HTTP or HTTPS URL."
            ) from exc
        normalized_citations.append(citation)
    if matching_state == "pending" and (
        not isinstance(raw.get("pending_reason"), str)
        or not raw["pending_reason"].strip()
    ):
        raise MomentDocumentError(
            f"Entry {index}: pending_reason is required for pending content."
        )
    return {
        **raw,
        "event": {**event, "date": event_date},
        "heading": heading,
        "body": body,
        "citations": normalized_citations,
    }


def _resolve(entry: dict[str, Any], index: int) -> ResolvedMoment:
    event = entry["event"]
    event_date = event["date"]
    try:
        win = Win.objects.select_related("show", "song__artist").get(
            show__slug=event["show"], date=event_date
        )
    except Win.DoesNotExist as exc:
        raise MomentDocumentError(
            f"Entry {index}: unresolved event {event['show']} on {event_date}."
        ) from exc
    if normalize_key(win.song.artist.name) != normalize_key(
        event["artist"]
    ) or normalize_key(win.song.title) != normalize_key(event["song"]):
        raise MomentDocumentError(
            f"Entry {index}: event winner does not match "
            f"{event['artist']} — {event['song']}."
        )
    return ResolvedMoment(entry, win)


def _resolve_entries(
    entries: list[dict[str, Any]], artists: set[str] | None
) -> list[ResolvedMoment]:
    """Resolve all selected events before writes and reject competing moment copy."""
    if artists:
        known_artists = {normalize_key(entry["event"]["artist"]) for entry in entries}
        unknown = artists - known_artists
        if unknown:
            raise MomentDocumentError(f"Unknown selected artist: {sorted(unknown)[0]}.")

    resolved = []
    seen_events = set()
    for index, entry in enumerate(entries, 1):
        event = entry["event"]
        if artists and normalize_key(event["artist"]) not in artists:
            continue
        if entry["matching_state"] == "pending":
            if artists:
                raise MomentDocumentError(
                    f"Selected artist {event['artist']} is pending: "
                    f"{entry['pending_reason']}"
                )
            continue
        identity = (event["show"], event["date"])
        if identity in seen_events:
            raise MomentDocumentError(
                f"Entry {index}: duplicate event {event['show']} on {event['date']}."
            )
        seen_events.add(identity)
        resolved.append(_resolve(entry, index))
    return resolved


def import_moments(
    document: Any,
    *,
    artists: set[str] | None = None,
    dry_run: bool = False,
    update_existing: bool = False,
):
    if (
        not isinstance(document, dict)
        or set(document) != {"version", "moments"}
        or type(document.get("version")) is not int
        or document.get("version") != 1
        or not isinstance(document.get("moments"), list)
    ):
        raise MomentDocumentError("Expected a version 1 moments document.")
    entries = [
        _validate_entry(raw, index) for index, raw in enumerate(document["moments"], 1)
    ]
    resolved = _resolve_entries(entries, artists)
    if dry_run:
        existing_win_ids = set(
            WinMoment.objects.filter(
                win_id__in=[item.win.pk for item in resolved]
            ).values_list("win_id", flat=True)
        )
        created = sum(item.win.pk not in existing_win_ids for item in resolved)
        updated = len(resolved) - created if update_existing else 0
        unchanged = len(resolved) - created - updated
        return created, updated, unchanged
    created = updated = unchanged = 0
    with transaction.atomic():
        for item in resolved:
            entry, win = item.entry, item.win
            moment = WinMoment.objects.select_for_update().filter(win=win).first()
            if moment is not None and not update_existing:
                unchanged += 1
                continue
            was_created = moment is None
            if was_created:
                moment = WinMoment.objects.create(
                    win=win,
                    heading=entry["heading"],
                    body=entry["body"],
                )
            else:
                moment.heading = entry["heading"]
                moment.body = entry["body"]
                moment.save(update_fields=("heading", "body", "updated_at"))
            refs = []
            for citation in entry["citations"]:
                ref, _ = WinReference.objects.update_or_create(
                    win=win,
                    url=citation["url"],
                    defaults={
                        "reference_type": WinReference.ReferenceType.ARTICLE,
                        "provider": citation["provider"],
                        "title": citation["title"],
                        "publisher_name": citation["publisher_name"],
                        "status": WinReference.Status.ACTIVE,
                    },
                )
                refs.append(ref)
            moment.citations.set(refs)
            desired_status = entry["status"]
            if desired_status == WinMoment.Status.PUBLISHED:
                validate_selected_citations(
                    win.pk,
                    desired_status,
                    refs,
                    require_active=True,
                )
            if moment.status != desired_status:
                moment.status = desired_status
                moment.save(update_fields=("status", "updated_at"))
            created += int(was_created)
            updated += int(not was_created)
    return created, updated, unchanged
