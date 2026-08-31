from __future__ import annotations

import json
import os
from io import StringIO
from unittest.mock import patch

import pytest

from kpopwins_operator.cli import main
from kpopwins_operator.database import insert_candidate
from kpopwins_operator.manifest import (
    MANIFEST_FIELDS,
    ManifestError,
    approved_document,
    serialize_document,
    write_atomic,
)

from .conftest import add_win


def candidate(
    *,
    show_slug="music-bank",
    win_date="2026-01-02",
    provider="youtube",
    external_id="abc123",
    url="https://www.youtube.com/watch?v=abc123",
    review_status="approved",
):
    return {
        "show_slug": show_slug,
        "win_date": win_date,
        "reference_type": "video",
        "provider": provider,
        "external_id": external_id,
        "url": url,
        "title": "Winner stage",
        "publisher_name": "Official channel",
        "publisher_external_id": "channel-id",
        "is_official": True,
        "status": "active",
        "published_at": "2026-01-02T12:00:00Z",
        "last_verified_at": "2026-08-31T12:00:00Z",
        "metadata": {"duration": 180},
        "review_status": review_status,
    }


def populate_candidates(connection):
    add_win(connection)
    add_win(
        connection,
        show_slug="inkigayo",
        win_date="2025-12-01",
        api_win_id=2,
    )
    add_win(
        connection,
        show_slug="the-show",
        win_date="2025-11-01",
        api_win_id=3,
        is_current=False,
    )
    insert_candidate(
        connection,
        candidate(
            show_slug="inkigayo",
            win_date="2025-12-01",
            provider="article-source",
            external_id="",
            url="https://example.com/article",
        ),
    )
    insert_candidate(connection, candidate())
    insert_candidate(
        connection,
        candidate(
            external_id="pending",
            url="https://example.com/pending",
            review_status="pending",
        ),
    )
    insert_candidate(
        connection,
        candidate(
            external_id="rejected",
            url="https://example.com/rejected",
            review_status="rejected",
        ),
    )
    insert_candidate(
        connection,
        candidate(
            show_slug="the-show",
            win_date="2025-11-01",
            external_id="old",
            url="https://example.com/non-current",
        ),
    )
    connection.commit()


def test_approved_export_is_deterministic_compatible_and_filtered(connection):
    populate_candidates(connection)

    first = approved_document(connection)
    second = approved_document(connection)

    assert serialize_document(first) == serialize_document(second)
    assert [item["win"]["show"] for item in first["references"]] == [
        "inkigayo",
        "music-bank",
    ]
    assert len(first["references"]) == 2
    assert set(first["references"][0]) == {"win", *MANIFEST_FIELDS}
    assert set(first["references"][0]["win"]) == {"show", "date"}
    assert first["references"][1]["metadata"] == {"duration": 180}
    assert all("review_status" not in item for item in first["references"])


def test_atomic_file_output_replaces_complete_destination(connection, tmp_path):
    populate_candidates(connection)
    content = serialize_document(approved_document(connection))
    destination = tmp_path / "manifests" / "references.json"
    destination.parent.mkdir()
    destination.write_text("old", encoding="utf-8")

    with patch("kpopwins_operator.manifest.os.replace", wraps=os.replace) as replace:
        write_atomic(destination, content)

    replace.assert_called_once()
    assert destination.read_text(encoding="utf-8") == content
    assert list(destination.parent.glob(".*.tmp")) == []


def test_json_only_stdout_mode(config, connection):
    populate_candidates(connection)
    output = StringIO()
    errors = StringIO()

    result = main(
        ["export-approved", "--output", "-"],
        environ={"KPOPWINS_OPERATOR_HOME": str(config.home)},
        stdout=output,
        stderr=errors,
    )

    assert result == 0
    document = json.loads(output.getvalue())
    assert document["version"] == 1
    assert len(document["references"]) == 2
    assert errors.getvalue() == ""


def test_default_export_path_stays_under_operator_home(config, connection):
    populate_candidates(connection)
    output = StringIO()

    result = main(
        ["export-approved"],
        environ={"KPOPWINS_OPERATOR_HOME": str(config.home)},
        stdout=output,
    )

    assert result == 0
    assert config.default_manifest_path.is_file()
    document = json.loads(config.default_manifest_path.read_text(encoding="utf-8"))
    assert document["version"] == 1
    assert str(config.default_manifest_path) in output.getvalue()


def test_export_normalizes_identity_fields_from_existing_sqlite_data(connection):
    add_win(connection)
    insert_candidate(connection, candidate())
    connection.execute(
        """
        UPDATE reference_candidates
        SET provider = ' YouTube ', external_id = ' abc123 ',
            url = ' https://example.com/reference ', title = ' Stage '
        """
    )

    reference = approved_document(connection)["references"][0]

    assert reference["provider"] == "youtube"
    assert reference["external_id"] == "abc123"
    assert reference["url"] == "https://example.com/reference"
    assert reference["title"] == "Stage"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("provider", "x" * 81),
        ("external_id", "x" * 256),
        ("url", "https://example.com/" + "x" * 2048),
        ("title", "x" * 501),
        ("publisher_name", "x" * 301),
        ("publisher_external_id", "x" * 256),
        ("url", "https://example.com:notaport/reference"),
    ],
)
def test_export_revalidates_malformed_existing_sqlite_data(connection, field, value):
    add_win(connection)
    insert_candidate(connection, candidate())
    connection.execute(
        f"UPDATE reference_candidates SET {field} = ?",
        (value,),
    )

    with pytest.raises(ManifestError):
        approved_document(connection)
