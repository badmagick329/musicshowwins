from __future__ import annotations

import ipaddress
import json
import re
from datetime import date, datetime
from typing import Any
from urllib.parse import urlsplit

TEXT_LIMITS = {
    "provider": 80,
    "external_id": 255,
    "url": 2048,
    "title": 500,
    "publisher_name": 300,
    "publisher_external_id": 255,
}
REFERENCE_TYPES = {"video", "article", "other"}
REFERENCE_STATUSES = {"active", "unavailable"}
REVIEW_STATUSES = {"pending", "approved", "rejected"}
DOMAIN_LABEL = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$", re.I)
DOMAIN_SUFFIX = re.compile(r"^(?:[a-z]{2,63}|xn--[a-z0-9-]{1,59})$", re.I)


class CandidateValidationError(ValueError):
    pass


def _text(
    candidate: dict[str, Any],
    field: str,
    *,
    default: str = "",
    required: bool = False,
) -> str:
    value = candidate.get(field, default)
    if not isinstance(value, str):
        raise CandidateValidationError(f"Candidate {field} must be text.")
    value = value.strip()
    if required and not value:
        raise CandidateValidationError(f"Candidate {field} is required.")
    limit = TEXT_LIMITS.get(field)
    if limit is not None and len(value) > limit:
        raise CandidateValidationError(
            f"Candidate {field} exceeds the {limit}-character limit."
        )
    return value


def _datetime_text(candidate: dict[str, Any], field: str) -> str | None:
    value = candidate.get(field)
    if value is None:
        return None
    if not isinstance(value, str):
        raise CandidateValidationError(f"Candidate {field} must be a datetime or null.")
    value = value.strip()
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CandidateValidationError(f"Candidate {field} is invalid.") from exc
    if parsed.tzinfo is None:
        raise CandidateValidationError(f"Candidate {field} must include a timezone.")
    return value


def validate_http_url(url: str) -> None:
    if any(character.isspace() for character in url):
        raise CandidateValidationError(
            "Candidate url must be a valid HTTP or HTTPS URL."
        )
    try:
        parsed = urlsplit(url)
        host = parsed.hostname
        parsed.port
    except ValueError as exc:
        raise CandidateValidationError(
            "Candidate url must be a valid HTTP or HTTPS URL."
        ) from exc
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc or not host:
        raise CandidateValidationError(
            "Candidate url must be a valid HTTP or HTTPS URL."
        )
    try:
        ipaddress.ip_address(host)
        return
    except ValueError:
        pass
    if host.lower() == "localhost":
        return
    try:
        ascii_host = host.encode("idna").decode("ascii")
    except UnicodeError as exc:
        raise CandidateValidationError(
            "Candidate url must be a valid HTTP or HTTPS URL."
        ) from exc
    if len(ascii_host) > 253 or ascii_host.endswith("."):
        raise CandidateValidationError(
            "Candidate url must be a valid HTTP or HTTPS URL."
        )
    labels = ascii_host.split(".")
    if (
        len(labels) < 2
        or any(DOMAIN_LABEL.fullmatch(label) is None for label in labels)
        or DOMAIN_SUFFIX.fullmatch(labels[-1]) is None
    ):
        raise CandidateValidationError(
            "Candidate url must be a valid HTTP or HTTPS URL."
        )


def normalize_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(candidate, dict):
        raise CandidateValidationError("Candidate must be an object.")
    show_slug = _text(candidate, "show_slug", required=True)
    win_date = _text(candidate, "win_date", required=True)
    try:
        parsed_date = date.fromisoformat(win_date)
    except ValueError as exc:
        raise CandidateValidationError("Candidate win_date is invalid.") from exc
    if parsed_date.isoformat() != win_date:
        raise CandidateValidationError("Candidate win_date is invalid.")
    reference_type = _text(candidate, "reference_type", required=True)
    if reference_type not in REFERENCE_TYPES:
        raise CandidateValidationError("Candidate reference_type is invalid.")
    status = _text(candidate, "status", default="active", required=True)
    if status not in REFERENCE_STATUSES:
        raise CandidateValidationError("Candidate status is invalid.")
    review_status = _text(candidate, "review_status", default="pending", required=True)
    if review_status not in REVIEW_STATUSES:
        raise CandidateValidationError("Candidate review_status is invalid.")
    is_official = candidate.get("is_official", False)
    if not isinstance(is_official, bool):
        raise CandidateValidationError("Candidate is_official must be a boolean.")
    metadata = candidate.get("metadata", {})
    if not isinstance(metadata, dict):
        raise CandidateValidationError("Candidate metadata must be a JSON object.")
    try:
        json.dumps(metadata)
    except (TypeError, ValueError) as exc:
        raise CandidateValidationError(
            "Candidate metadata must be JSON serializable."
        ) from exc

    normalized = {
        "show_slug": show_slug,
        "win_date": win_date,
        "reference_type": reference_type,
        "provider": _text(candidate, "provider", required=True).lower(),
        "external_id": _text(candidate, "external_id"),
        "url": _text(candidate, "url", required=True),
        "title": _text(candidate, "title"),
        "publisher_name": _text(candidate, "publisher_name"),
        "publisher_external_id": _text(candidate, "publisher_external_id"),
        "is_official": is_official,
        "status": status,
        "published_at": _datetime_text(candidate, "published_at"),
        "last_verified_at": _datetime_text(candidate, "last_verified_at"),
        "metadata": metadata,
        "review_status": review_status,
    }
    validate_http_url(normalized["url"])
    return normalized
