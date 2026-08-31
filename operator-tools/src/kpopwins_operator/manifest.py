from __future__ import annotations

import json
import os
import sqlite3
import tempfile
from pathlib import Path
from typing import Any

from .validation import CandidateValidationError, normalize_candidate

MANIFEST_FIELDS = (
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


class ManifestError(ValueError):
    pass


def validate_document(document: Any) -> dict[str, Any]:
    if not isinstance(document, dict) or set(document) != {"version", "references"}:
        raise ManifestError("Manifest must contain version and references.")
    if document["version"] != 1 or type(document["version"]) is not int:
        raise ManifestError("Manifest version must be 1.")
    references = document["references"]
    if not isinstance(references, list):
        raise ManifestError("Manifest references must be an array.")
    url_keys: set[tuple[str, str, str]] = set()
    external_keys: set[tuple[str, str, str, str]] = set()
    normalized_references = []
    for reference in references:
        if not isinstance(reference, dict) or set(reference) != {
            "win",
            *MANIFEST_FIELDS,
        }:
            raise ManifestError("Manifest reference fields are invalid.")
        win = reference["win"]
        if not isinstance(win, dict) or set(win) != {"show", "date"}:
            raise ManifestError("Manifest win identity is invalid.")
        try:
            normalized = normalize_candidate(
                {
                    "show_slug": win.get("show"),
                    "win_date": win.get("date"),
                    **{field: reference[field] for field in MANIFEST_FIELDS},
                    "review_status": "approved",
                }
            )
        except CandidateValidationError as exc:
            raise ManifestError(str(exc)) from exc
        normalized_reference = {
            "win": {
                "show": normalized["show_slug"],
                "date": normalized["win_date"],
            },
            **{field: normalized[field] for field in MANIFEST_FIELDS},
        }
        identity = (
            normalized["show_slug"],
            normalized["win_date"],
        )
        url_key = (*identity, normalized["url"])
        if url_key in url_keys:
            raise ManifestError("Manifest contains a duplicate URL for one win.")
        url_keys.add(url_key)
        if normalized["external_id"]:
            external_key = (
                *identity,
                normalized["provider"],
                normalized["external_id"],
            )
            if external_key in external_keys:
                raise ManifestError(
                    "Manifest contains a duplicate provider identifier for one win."
                )
            external_keys.add(external_key)
        normalized_references.append(normalized_reference)
    return {"version": 1, "references": normalized_references}


def approved_document(connection: sqlite3.Connection) -> dict[str, Any]:
    rows = connection.execute(
        """
        SELECT candidate.*
        FROM reference_candidates AS candidate
        JOIN wins
          ON wins.show_slug = candidate.show_slug
         AND wins.win_date = candidate.win_date
        WHERE candidate.review_status = 'approved' AND wins.is_current = 1
        ORDER BY candidate.show_slug, candidate.win_date, candidate.provider,
                 candidate.external_id, candidate.url
        """
    )
    references = []
    for row in rows:
        references.append(
            {
                "win": {"show": row["show_slug"], "date": row["win_date"]},
                "reference_type": row["reference_type"],
                "provider": row["provider"],
                "external_id": row["external_id"],
                "url": row["url"],
                "title": row["title"],
                "publisher_name": row["publisher_name"],
                "publisher_external_id": row["publisher_external_id"],
                "is_official": bool(row["is_official"]),
                "status": row["status"],
                "published_at": row["published_at"],
                "last_verified_at": row["last_verified_at"],
                "metadata": json.loads(row["metadata"]),
            }
        )
    document = validate_document({"version": 1, "references": references})
    document["references"].sort(
        key=lambda reference: (
            reference["win"]["show"],
            reference["win"]["date"],
            reference["provider"],
            reference["external_id"],
            reference["url"],
        )
    )
    return document


def serialize_document(document: dict[str, Any]) -> str:
    normalized = validate_document(document)
    return json.dumps(normalized, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def write_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary.write(content)
            temporary.flush()
            os.fsync(temporary.fileno())
            temporary_path = Path(temporary.name)
        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()
