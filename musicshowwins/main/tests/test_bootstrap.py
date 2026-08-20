import json
from datetime import date

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db.models import Count

from main.models import (
    Artist,
    ArtistAlias,
    ImportIssue,
    ImportRun,
    MusicShow,
    Song,
    SourcePage,
    Win,
)


@pytest.mark.django_db
def test_bootstrap_restores_exact_domain_dataset(capsys):
    call_command("restore_bootstrap")

    assert MusicShow.objects.count() == 6
    assert Artist.objects.count() == 292
    assert Song.objects.count() == 882
    assert Win.objects.count() == 2905
    assert ArtistAlias.objects.count() == 4
    assert not SourcePage.objects.exists()
    assert not ImportRun.objects.exists()
    assert ImportIssue.objects.count() == 45
    assert (
        ImportIssue.objects.filter(resolution=ImportIssue.Resolution.OPEN).count() == 0
    )
    assert ImportIssue.objects.filter(resolved_at__isnull=True).count() == 0
    assert (
        ImportIssue.objects.filter(resolution=ImportIssue.Resolution.ACCEPTED).count()
        == 6
    )
    assert (
        ImportIssue.objects.filter(resolution=ImportIssue.Resolution.REJECTED).count()
        == 39
    )
    assert (
        ImportIssue.objects.filter(
            issue_type=ImportIssue.IssueType.LEGACY_DISCREPANCY
        ).count()
        == 12
    )
    assert (
        ImportIssue.objects.filter(
            issue_type=ImportIssue.IssueType.LEGACY_UNDATED
        ).count()
        == 33
    )

    assert set(ArtistAlias.objects.values_list("alias", "artist__name")) == {
        ("BigBang", "Big Bang"),
        ("Akdong Musician", "AKMU"),
        ("TXT", "Tomorrow X Together"),
        ("Kim Woo Seok", "Kim Woo-seok"),
    }
    assert not ArtistAlias.objects.filter(alias="Blackpink and Selena Gomez").exists()
    assert Win.objects.filter(source_type=Win.SourceType.LEGACY).count() == 2905
    assert Win.objects.filter(source_revision__isnull=False).count() == 0
    assert not Win.objects.filter(show__slug="music-core", date="2016-01-01").exists()
    assert not Win.objects.filter(
        song__artist__name__in=["BigBang", "Akdong Musician"]
    ).exists()
    assert not Artist.objects.filter(name__in=["Aespa[a]", "Jungkook ("]).exists()
    assert Artist.objects.filter(name="BLACKPINK and Selena Gomez").count() == 1
    assert (
        Song.objects.filter(artist__name="Zico", title="SPOT! (feat. JENNIE)").count()
        == 1
    )
    assert (
        Song.objects.filter(
            artist__name="Lee Young-ji", title="Small girl (feat. D.O.)"
        ).count()
        == 1
    )
    assert (
        Song.objects.filter(
            artist__name="Jimin",
            title="Smeraldo Garden Marching Band (feat. Loco)",
        ).count()
        == 1
    )
    assert set(
        Artist.objects.filter(
            name__in=[
                "Tomorrow X Together",
                "Jonghyun",
                "U-Know",
                "Kim Woo-seok",
                "TripleS",
                "Rosé and Bruno Mars",
                "Psy feat. Suga",
                "J-Hope & J. Cole",
                "Mad Clown ft. Hyolyn",
            ]
        ).values_list("name", flat=True)
    ) == {
        "Tomorrow X Together",
        "Jonghyun",
        "U-Know",
        "Kim Woo-seok",
        "TripleS",
        "Rosé and Bruno Mars",
        "Psy feat. Suga",
        "J-Hope & J. Cole",
        "Mad Clown ft. Hyolyn",
    }
    assert not Artist.objects.filter(
        name__in=["TXT", "Kim Jong-hyun", "U-Know Yunho", "Kim Woo Seok", "TripleS[c]"]
    ).exists()
    assert not Song.objects.filter(
        title__in=["Wish (Korean ver.)", "Pineaple Slice"]
    ).exists()
    assert not Song.objects.filter(title="Remember That (Spring Memories)").exists()
    assert not Song.objects.filter(title="Hello, My First Love").exists()
    assert not Song.objects.filter(title="Can’t You See Me?").exists()
    assert Song.objects.filter(title="Hello: My First Love").exists()
    assert Song.objects.filter(title="APT.").exists()
    assert not Song.objects.filter(title__startswith="\u201c").exists()
    assert (
        Win.objects.values("show_id", "date")
        .annotate(row_count=Count("id"))
        .filter(row_count__gt=1)
        .count()
        == 0
    )
    assert (
        ImportIssue.objects.filter(
            issue_type=ImportIssue.IssueType.LEGACY_DISCREPANCY,
            candidate__artist="BLACKPINK",
            candidate__retained__artist="Blackpink and Selena Gomez",
        ).count()
        == 3
    )
    undated = ImportIssue.objects.get(
        issue_type=ImportIssue.IssueType.LEGACY_UNDATED,
        candidate__song="Monster",
    )
    assert undated.candidate == {
        "show": "music-core",
        "year": 2016,
        "artist": "EXO",
        "song": "Monster",
        "expected_wins": 3,
    }
    assert Win.objects.values_list("date", flat=True).order_by("date").first() >= date(
        2014, 1, 1
    )
    assert Win.objects.values_list("date", flat=True).order_by("-date").first() == date(
        2025, 8, 12
    )
    assert Win.objects.filter(
        show__slug="music-core", song__title="Smoothie", date=date(2024, 4, 6)
    ).exists()
    assert not Win.objects.filter(
        show__slug="music-core", song__title="Smoothie", date=date(2024, 4, 7)
    ).exists()
    assert all(
        win.song.artist_id and win.show_id
        for win in Win.objects.select_related("song__artist", "show")
    )
    capsys.readouterr()


@pytest.mark.django_db
def test_bootstrap_requires_empty_domain_tables():
    MusicShow.objects.create(slug="music-bank", name="Music Bank")

    with pytest.raises(CommandError, match="empty domain tables"):
        call_command("restore_bootstrap")

    assert MusicShow.objects.count() == 1
    assert Artist.objects.count() == 0


def test_cleanup_manifest_replays_to_frozen_counts():
    from main.bootstrap import CLEAN_COUNTS, apply_cleanup

    with open("musicshowwins/main/data/bootstrap.json", encoding="utf-8") as file:
        payload = json.load(file)
    cleaned, issues = apply_cleanup(payload)

    assert {key: len(cleaned[key]) for key in CLEAN_COUNTS} == CLEAN_COUNTS
    assert len(issues) == 45
    assert all(
        not (row["show"] == "music-core" and row["date"] == "2016-01-01")
        for row in cleaned["wins"]
    )


def test_ambiguous_date_decision_quarantines_every_candidate():
    from main.bootstrap import _legacy_discrepancy_candidate, _retained_decision_row

    decision_rows = [
        {"artist": "Alpha", "song": "First", "action": "quarantine"},
        {"artist": "Beta", "song": "Second", "action": "quarantine"},
    ]
    source_row = {
        "show": "music-bank",
        "date": "2024-01-05",
        "artist": "Alpha",
        "title": "First",
    }

    assert _retained_decision_row(decision_rows) is None
    assert _legacy_discrepancy_candidate(source_row, None)["retained"] is None
