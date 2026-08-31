import json
from copy import deepcopy
from datetime import date
from io import StringIO
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from main.models import Artist, MusicShow, Song, Win, WinReference


@pytest.fixture
def reference_win(db):
    show = MusicShow.objects.create(slug="music-bank", name="Music Bank")
    artist = Artist.objects.create(name="Alpha")
    song = Song.objects.create(artist=artist, title="First")
    return Win.objects.create(show=show, song=song, date=date(2026, 1, 2))


@pytest.fixture
def reference_document():
    return {
        "version": 1,
        "references": [
            {
                "win": {"show": "music-bank", "date": "2026-01-02"},
                "reference_type": " video ",
                "provider": " YouTube ",
                "external_id": " abc123 ",
                "url": " https://www.youtube.com/watch?v=abc123 ",
                "title": " Winner stage ",
                "publisher_name": " KBS Kpop ",
                "publisher_external_id": " channel-id ",
                "is_official": True,
                "status": " active ",
                "published_at": "2026-01-02T12:00:00Z",
                "last_verified_at": "2026-08-31T12:00:00Z",
                "metadata": {"duration": 180},
            }
        ],
    }


def _import_file(tmp_path, document, **options):
    path = tmp_path / "references.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    output = StringIO()
    call_command("import_win_references", str(path), stdout=output, **options)
    return output.getvalue()


def test_imports_valid_file_and_normalizes_text(
    reference_win, reference_document, tmp_path
):
    output = _import_file(tmp_path, reference_document)

    reference = WinReference.objects.get()
    assert reference.win == reference_win
    assert reference.provider == "youtube"
    assert reference.external_id == "abc123"
    assert reference.title == "Winner stage"
    assert reference.publisher_name == "KBS Kpop"
    assert reference.metadata == {"duration": 180}
    assert "created 1, updated 0, unchanged 0" in output


def test_imports_from_stdin(reference_win, reference_document):
    output = StringIO()
    with patch("sys.stdin", StringIO(json.dumps(reference_document))):
        call_command("import_win_references", "-", stdout=output)

    assert WinReference.objects.count() == 1
    assert "created 1" in output.getvalue()


def test_identical_reimport_is_unchanged(reference_win, reference_document, tmp_path):
    _import_file(tmp_path, reference_document)
    original = WinReference.objects.get()
    original_updated_at = original.updated_at

    output = _import_file(tmp_path, reference_document)

    original.refresh_from_db()
    assert original.updated_at == original_updated_at
    assert "created 0, updated 0, unchanged 1" in output


def test_updates_by_url_and_by_provider_external_id(
    reference_win, reference_document, tmp_path
):
    _import_file(tmp_path, reference_document)
    by_url = deepcopy(reference_document)
    by_url["references"][0]["title"] = "Updated title"
    by_url["references"][0]["metadata"] = {"quality": "hd"}
    assert "updated 1" in _import_file(tmp_path, by_url)

    by_external_id = deepcopy(by_url)
    by_external_id["references"][0]["url"] = "https://example.com/new-location"
    by_external_id["references"][0]["publisher_name"] = "Updated publisher"
    assert "updated 1" in _import_file(tmp_path, by_external_id)

    reference = WinReference.objects.get()
    assert reference.title == "Updated title"
    assert reference.metadata == {"quality": "hd"}
    assert reference.url == "https://example.com/new-location"
    assert reference.publisher_name == "Updated publisher"


def test_invalid_later_record_rolls_back_complete_import(
    reference_win, reference_document, tmp_path
):
    invalid = deepcopy(reference_document["references"][0])
    invalid["win"] = {"show": "missing", "date": "2026-01-02"}
    document = {
        "version": 1,
        "references": [reference_document["references"][0], invalid],
    }

    with pytest.raises(CommandError, match="Reference 2"):
        _import_file(tmp_path, document)

    assert WinReference.objects.count() == 0


@pytest.mark.parametrize(
    ("win_data", "message"),
    [
        ({"show": "missing", "date": "2026-01-02"}, "music show"),
        ({"show": "music-bank", "date": "2026-01-03"}, "win does not exist"),
    ],
)
def test_missing_show_and_win_failures(
    reference_win, reference_document, tmp_path, win_data, message
):
    document = deepcopy(reference_document)
    document["references"][0]["win"] = win_data

    with pytest.raises(CommandError, match=message):
        _import_file(tmp_path, document)


def test_rejects_unsupported_version(reference_win, reference_document, tmp_path):
    document = deepcopy(reference_document)
    document["version"] = 2
    with pytest.raises(CommandError, match="Unsupported document version"):
        _import_file(tmp_path, document)


def test_rejects_malformed_json(reference_win, tmp_path):
    path = tmp_path / "references.json"
    path.write_text("{not-json", encoding="utf-8")
    with pytest.raises(CommandError, match="Invalid JSON"):
        call_command("import_win_references", str(path))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("reference_type", "stream"),
        ("status", "missing"),
        ("is_official", "yes"),
        ("url", "ftp://example.com/reference"),
        ("published_at", "not-a-date"),
        ("metadata", []),
    ],
)
def test_rejects_malformed_fields(
    reference_win, reference_document, tmp_path, field, value
):
    document = deepcopy(reference_document)
    document["references"][0][field] = value
    with pytest.raises(CommandError, match="Reference 1"):
        _import_file(tmp_path, document)


@pytest.mark.parametrize("duplicate_kind", ["url", "external_id"])
def test_rejects_duplicates_within_document(
    reference_win, reference_document, tmp_path, duplicate_kind
):
    first = reference_document["references"][0]
    second = deepcopy(first)
    if duplicate_kind == "url":
        second["external_id"] = "different"
    else:
        second["url"] = "https://example.com/different"
    document = {"version": 1, "references": [first, second]}

    with pytest.raises(CommandError, match="duplicates"):
        _import_file(tmp_path, document)
    assert WinReference.objects.count() == 0


def test_dry_run_leaves_database_unchanged(reference_win, reference_document, tmp_path):
    output = _import_file(tmp_path, reference_document, dry_run=True)
    assert WinReference.objects.count() == 0
    assert "Dry run: created 1" in output


def test_export_is_deterministic_and_stably_ordered(reference_win):
    earlier_show = MusicShow.objects.create(slug="inkigayo", name="Inkigayo")
    earlier_win = Win.objects.create(
        show=earlier_show,
        song=reference_win.song,
        date=date(2025, 1, 1),
    )
    WinReference.objects.create(
        win=reference_win,
        reference_type="article",
        provider="z-provider",
        url="https://example.com/z",
        status="unavailable",
    )
    WinReference.objects.create(
        win=earlier_win,
        reference_type="video",
        provider="a-provider",
        external_id="first",
        url="https://example.com/a",
    )

    first_output = StringIO()
    second_output = StringIO()
    call_command("export_win_references", stdout=first_output)
    call_command("export_win_references", stdout=second_output)

    assert first_output.getvalue() == second_output.getvalue()
    document = json.loads(first_output.getvalue())
    assert document["version"] == 1
    assert [item["win"]["show"] for item in document["references"]] == [
        "inkigayo",
        "music-bank",
    ]
    assert document["references"][1]["status"] == "unavailable"
    assert "id" not in document["references"][0]


def test_export_import_round_trip(reference_win, reference_document, tmp_path):
    _import_file(tmp_path, reference_document)
    exported = StringIO()
    call_command("export_win_references", stdout=exported)
    expected = json.loads(exported.getvalue())

    WinReference.objects.all().delete()
    output = StringIO()
    with patch("sys.stdin", StringIO(exported.getvalue())):
        call_command("import_win_references", "-", stdout=output)
    round_tripped = StringIO()
    call_command("export_win_references", stdout=round_tripped)

    assert json.loads(round_tripped.getvalue()) == expected
    assert WinReference.objects.count() == 1
