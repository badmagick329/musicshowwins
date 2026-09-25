import json
from datetime import date
from io import StringIO
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from main.models import Artist, MusicShow, Song, Win


@pytest.fixture
def wins(db):
    show = MusicShow.objects.create(slug="music-bank", name="Music Bank")
    song = Song.objects.create(
        artist=Artist.objects.create(name="Alpha"), title="First"
    )
    return [
        Win.objects.create(show=show, song=song, date=date(2026, 1, day))
        for day in (2, 9, 16)
    ]


def run(tmp_path, entries, *args):
    path = tmp_path / "presence.json"
    path.write_text(json.dumps({"version": 1, "wins": entries}), encoding="utf-8")
    output = StringIO()
    with patch(
        "main.management.commands.import_win_presence.invalidate_public_archive_cache"
    ) as refresh:
        call_command("import_win_presence", str(path), *args, stdout=output)
    return output.getvalue(), refresh


def test_sets_named_wins_keeps_others_and_reports_missing(wins, tmp_path):
    wins[2].performed = True
    wins[2].save()
    entries = [
        {"show": "music-bank", "date": "2026-01-02", "performed": False},
        {"show": "music-bank", "date": "2026-01-09", "performed": True},
        {"show": "music-bank", "date": "2027-01-01", "performed": False},
    ]

    dry, _ = run(tmp_path, entries, "--dry-run")
    assert dry == "Dry run: updated 2, unchanged 0, missing wins 1.\n"
    assert {win.performed for win in Win.objects.exclude(pk=wins[2].pk)} == {None}

    output, refresh = run(tmp_path, entries)
    assert output == "updated 2, unchanged 0, missing wins 1.\n"
    assert refresh.call_count == 1
    assert [Win.objects.get(pk=win.pk).performed for win in wins] == [False, True, True]

    rerun, refresh = run(tmp_path, entries)
    assert rerun == "updated 0, unchanged 2, missing wins 1.\n"
    assert refresh.call_count == 0


@pytest.mark.parametrize(
    "entry",
    [
        {"show": "music-bank", "date": "2026-01-02", "performed": "no"},
        {"show": "music-bank", "date": "2026-1-2", "performed": False},
        {"show": "music-bank", "date": "2026-01-02"},
    ],
)
def test_rejects_invalid_entries_without_writing(wins, tmp_path, entry):
    with pytest.raises(CommandError):
        run(tmp_path, [entry])
    assert set(Win.objects.values_list("performed", flat=True)) == {None}


def test_api_exposes_performed(wins, client):
    wins[0].performed = False
    wins[0].save()
    results = client.get("/api/v1/wins/?show=music-bank").json()["results"]
    assert {item["date"]: item["performed"] for item in results} == {
        "2026-01-16": None,
        "2026-01-09": None,
        "2026-01-02": False,
    }
