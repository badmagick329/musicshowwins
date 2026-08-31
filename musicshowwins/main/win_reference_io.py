from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime

from .models import MusicShow, Win, WinReference

DOCUMENT_VERSION = 1
TEXT_FIELDS = {
    "provider": 80,
    "external_id": 255,
    "url": 2048,
    "title": 500,
    "publisher_name": 300,
    "publisher_external_id": 255,
}
REFERENCE_FIELDS = {
    "win",
    "reference_type",
    *TEXT_FIELDS,
    "is_official",
    "status",
    "published_at",
    "last_verified_at",
    "metadata",
}
MUTABLE_FIELDS = (
    "reference_type",
    "provider",
    "external_id",
    "url",
    "title",
    "publisher_name",
    "publisher_external_id",
    "is_official",
    "status",
    "published_at",
    "last_verified_at",
    "metadata",
)


class ReferenceDocumentError(ValueError):
    pass


@dataclass(frozen=True)
class ValidatedReference:
    index: int
    win: Win
    values: dict[str, Any]


@dataclass(frozen=True)
class PlannedReference:
    record: ValidatedReference
    instance: WinReference | None
    changed_fields: tuple[str, ...]


def _error(index: int, message: str) -> ReferenceDocumentError:
    return ReferenceDocumentError(f"Reference {index}: {message}")


def _text(
    data: dict[str, Any],
    field: str,
    index: int,
    *,
    required: bool = False,
) -> str:
    value = data.get(field, "")
    if value is None and not required:
        value = ""
    if not isinstance(value, str):
        raise _error(index, f"{field} must be a string.")
    value = value.strip()
    if required and not value:
        raise _error(index, f"{field} is required.")
    if len(value) > TEXT_FIELDS[field]:
        raise _error(index, f"{field} is too long.")
    return value


def _datetime(data: dict[str, Any], field: str, index: int) -> datetime | None:
    value = data.get(field)
    if value in (None, ""):
        return None
    if not isinstance(value, str):
        raise _error(index, f"{field} must be an ISO 8601 datetime or null.")
    parsed = parse_datetime(value.strip())
    if parsed is None or timezone.is_naive(parsed):
        raise _error(index, f"{field} must be an ISO 8601 datetime with a timezone.")
    return parsed


def _choice(
    data: dict[str, Any],
    field: str,
    choices: set[str],
    index: int,
    *,
    default: str | None = None,
) -> str:
    value = data.get(field, default)
    if not isinstance(value, str) or value.strip() not in choices:
        raise _error(index, f"{field} is invalid.")
    return value.strip()


def _validate_record(raw: Any, index: int) -> tuple[str, object, dict[str, Any]]:
    if not isinstance(raw, dict):
        raise _error(index, "must be an object.")
    unknown = set(raw) - REFERENCE_FIELDS
    if unknown:
        raise _error(index, f"contains unknown field {sorted(unknown)[0]}.")

    win_data = raw.get("win")
    if not isinstance(win_data, dict):
        raise _error(index, "win must be an object.")
    unknown_win = set(win_data) - {"show", "date"}
    if unknown_win:
        raise _error(index, f"win contains unknown field {sorted(unknown_win)[0]}.")
    show_slug = win_data.get("show")
    date_value = win_data.get("date")
    if not isinstance(show_slug, str) or not show_slug.strip():
        raise _error(index, "win.show is required.")
    if not isinstance(date_value, str):
        raise _error(index, "win.date must use YYYY-MM-DD.")
    show_slug = show_slug.strip()
    win_date = parse_date(date_value.strip())
    if win_date is None or win_date.isoformat() != date_value.strip():
        raise _error(index, "win.date must use YYYY-MM-DD.")

    reference_type = _choice(
        raw,
        "reference_type",
        set(WinReference.ReferenceType.values),
        index,
    )
    status = _choice(
        raw,
        "status",
        set(WinReference.Status.values),
        index,
        default=WinReference.Status.ACTIVE,
    )
    is_official = raw.get("is_official", False)
    if not isinstance(is_official, bool):
        raise _error(index, "is_official must be a boolean.")
    metadata = raw.get("metadata", {})
    if not isinstance(metadata, dict):
        raise _error(index, "metadata must be an object.")

    values = {
        "reference_type": reference_type,
        "provider": _text(raw, "provider", index, required=True).lower(),
        "external_id": _text(raw, "external_id", index),
        "url": _text(raw, "url", index, required=True),
        "title": _text(raw, "title", index),
        "publisher_name": _text(raw, "publisher_name", index),
        "publisher_external_id": _text(raw, "publisher_external_id", index),
        "is_official": is_official,
        "status": status,
        "published_at": _datetime(raw, "published_at", index),
        "last_verified_at": _datetime(raw, "last_verified_at", index),
        "metadata": metadata,
    }
    try:
        URLValidator(schemes=("http", "https"))(values["url"])
    except ValidationError as exc:
        raise _error(index, "url must be a valid HTTP or HTTPS URL.") from exc
    return show_slug, win_date, values


def validate_document(document: Any) -> list[ValidatedReference]:
    if not isinstance(document, dict):
        raise ReferenceDocumentError("The document must be a JSON object.")
    unknown = set(document) - {"version", "references"}
    if unknown:
        raise ReferenceDocumentError(
            f"The document contains unknown field {sorted(unknown)[0]}."
        )
    version = document.get("version")
    if type(version) is not int or version != DOCUMENT_VERSION:
        raise ReferenceDocumentError("Unsupported document version; expected 1.")
    references = document.get("references")
    if not isinstance(references, list):
        raise ReferenceDocumentError("references must be an array.")

    validated: list[ValidatedReference] = []
    url_keys: set[tuple[int, str]] = set()
    external_keys: set[tuple[int, str, str]] = set()
    for index, raw in enumerate(references, start=1):
        show_slug, win_date, values = _validate_record(raw, index)
        show = MusicShow.objects.filter(slug=show_slug).first()
        if show is None:
            raise _error(index, "music show does not exist.")
        win = Win.objects.filter(show=show, date=win_date).first()
        if win is None:
            raise _error(index, "win does not exist.")

        url_key = (win.pk, values["url"])
        if url_key in url_keys:
            raise _error(index, "duplicates a URL in this document.")
        url_keys.add(url_key)
        if values["external_id"]:
            external_key = (
                win.pk,
                values["provider"],
                values["external_id"],
            )
            if external_key in external_keys:
                raise _error(
                    index,
                    "duplicates a provider and external ID in this document.",
                )
            external_keys.add(external_key)
        validated.append(ValidatedReference(index=index, win=win, values=values))
    return validated


def _plan_import(records: list[ValidatedReference]) -> list[PlannedReference]:
    win_ids = {record.win.pk for record in records}
    existing = list(
        WinReference.objects.select_for_update()
        .filter(win_id__in=win_ids)
        .order_by("pk")
    )
    by_url = {(item.win_id, item.url): item for item in existing}
    by_external = {
        (item.win_id, item.provider, item.external_id): item
        for item in existing
        if item.external_id
    }
    claimed: set[int] = set()
    plans: list[PlannedReference] = []
    desired_existing: dict[int, dict[str, Any]] = {}

    for record in records:
        values = record.values
        url_match = by_url.get((record.win.pk, values["url"]))
        external_match = None
        if values["external_id"]:
            external_match = by_external.get(
                (record.win.pk, values["provider"], values["external_id"])
            )
        if url_match and external_match and url_match.pk != external_match.pk:
            raise _error(record.index, "matches two existing references.")
        instance = url_match or external_match
        if instance and instance.pk in claimed:
            raise _error(record.index, "matches an earlier reference in this document.")
        if instance:
            claimed.add(instance.pk)
            changed = tuple(
                field
                for field in MUTABLE_FIELDS
                if getattr(instance, field) != values[field]
            )
            desired_existing[instance.pk] = values
        else:
            changed = MUTABLE_FIELDS
        plans.append(
            PlannedReference(
                record=record,
                instance=instance,
                changed_fields=changed,
            )
        )

    final_states: list[tuple[int, dict[str, Any], int]] = []
    for instance in existing:
        values = desired_existing.get(
            instance.pk,
            {field: getattr(instance, field) for field in MUTABLE_FIELDS},
        )
        final_states.append((instance.win_id, values, instance.pk))
    for plan in plans:
        if plan.instance is None:
            final_states.append(
                (plan.record.win.pk, plan.record.values, -plan.record.index)
            )

    urls: dict[tuple[int, str], int] = {}
    external_ids: dict[tuple[int, str, str], int] = {}
    for win_id, values, identifier in final_states:
        url_key = (win_id, values["url"])
        if url_key in urls:
            raise ReferenceDocumentError(
                "The import would create duplicate URLs for one win."
            )
        urls[url_key] = identifier
        if values["external_id"]:
            external_key = (win_id, values["provider"], values["external_id"])
            if external_key in external_ids:
                raise ReferenceDocumentError(
                    "The import would create duplicate provider and external IDs "
                    "for one win."
                )
            external_ids[external_key] = identifier
    return plans


def import_document(document: Any, *, dry_run: bool = False) -> tuple[int, int, int]:
    with transaction.atomic():
        records = validate_document(document)
        plans = _plan_import(records)
        created = updated = unchanged = 0
        if dry_run:
            for plan in plans:
                if plan.instance is None:
                    created += 1
                elif plan.changed_fields:
                    updated += 1
                else:
                    unchanged += 1
            return created, updated, unchanged

        for plan in plans:
            if plan.instance is None:
                WinReference.objects.create(win=plan.record.win, **plan.record.values)
                created += 1
            elif plan.changed_fields:
                for field in plan.changed_fields:
                    setattr(plan.instance, field, plan.record.values[field])
                plan.instance.save(update_fields=(*plan.changed_fields, "updated_at"))
                updated += 1
            else:
                unchanged += 1
        return created, updated, unchanged


def _export_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat().replace("+00:00", "Z")


def export_document() -> dict[str, Any]:
    references = WinReference.objects.select_related("win__show").order_by(
        "win__show__slug",
        "win__date",
        "provider",
        "external_id",
        "url",
    )
    return {
        "version": DOCUMENT_VERSION,
        "references": [
            {
                "win": {
                    "show": reference.win.show.slug,
                    "date": reference.win.date.isoformat(),
                },
                "reference_type": reference.reference_type,
                "provider": reference.provider,
                "external_id": reference.external_id,
                "url": reference.url,
                "title": reference.title,
                "publisher_name": reference.publisher_name,
                "publisher_external_id": reference.publisher_external_id,
                "is_official": reference.is_official,
                "status": reference.status,
                "published_at": _export_datetime(reference.published_at),
                "last_verified_at": _export_datetime(reference.last_verified_at),
                "metadata": reference.metadata,
            }
            for reference in references
        ],
    }
