from __future__ import annotations

from datetime import date, datetime, timezone

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

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
from main.wikipedia import (
    ImportSummary,
    RevisionPage,
    WikipediaFetchError,
    WikipediaImporter,
)


def wins_html(*rows: tuple[str, str, str]) -> str:
    body = "".join(
        f"<tr><td>{row_date}</td><td>{artist}</td><td>{song}</td></tr>"
        for row_date, artist, song in rows
    )
    return (
        "<table class='wikitable'><tr><th>Date</th><th>Artist</th>"
        f"<th>Song</th></tr>{body}</table>"
    )


class FakeClient:
    def __init__(self, *, revision="101", html=None, error=None):
        self.revision = str(revision)
        self.html = html or wins_html(("January 3", "New Artist", "New Song"))
        self.error = error
        self.html_calls = 0
        self.revision_calls = 0

    def latest_revision(self, title):
        self.revision_calls += 1
        if self.error:
            raise self.error
        return RevisionPage(title, self.revision)

    def html_for_revision(self, page):
        self.html_calls += 1
        return self.html


@pytest.fixture
def show(db):
    return MusicShow.objects.create(slug="music-bank", name="Music Bank")


def sync(show, client, *, year=2026, dry_run=False):
    return WikipediaImporter(client).sync(
        shows=[show.slug], years=[year], dry_run=dry_run
    )


@pytest.mark.django_db
def test_unchanged_revision_skips_html_and_source_write(show):
    client = FakeClient(revision="101")
    first = sync(show, client)
    source = SourcePage.objects.get(show=show, year=2026)
    last_synced = source.last_synced_at
    win_count = Win.objects.count()

    second = sync(show, client)

    assert first.wins_added == 1
    assert second.pages_processed == 1
    assert client.html_calls == 1
    assert Win.objects.count() == win_count
    source.refresh_from_db()
    assert source.latest_revision == "101"
    assert source.last_synced_at == last_synced


@pytest.mark.django_db
def test_dry_run_makes_no_persistent_changes(show):
    client = FakeClient()

    summary = sync(show, client, dry_run=True)

    assert summary.wins_added == 1
    assert ImportRun.objects.count() == 0
    assert SourcePage.objects.count() == 0
    assert Artist.objects.count() == 0
    assert Song.objects.count() == 0
    assert Win.objects.count() == 0
    assert ImportIssue.objects.count() == 0


@pytest.mark.django_db
def test_fetch_failure_records_failed_run_and_preserves_source(show):
    source = SourcePage.objects.create(
        show=show,
        year=2026,
        page_title="Existing title",
        latest_revision="100",
        last_synced_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
    )
    client = FakeClient(error=WikipediaFetchError("network down"))

    summary = sync(show, client)

    source.refresh_from_db()
    run = ImportRun.objects.get()
    assert summary.failures
    assert run.status == ImportRun.Status.FAILED
    assert source.page_title == "Existing title"
    assert source.latest_revision == "100"
    assert source.last_synced_at == datetime(2026, 8, 1, tzinfo=timezone.utc)
    assert ImportIssue.objects.filter(
        issue_type=ImportIssue.IssueType.FETCH_ERROR
    ).exists()


@pytest.mark.django_db
def test_invalid_page_records_failure_and_preserves_existing_revision(show):
    source = SourcePage.objects.create(
        show=show,
        year=2026,
        page_title="Existing title",
        latest_revision="100",
    )
    client = FakeClient(revision="101", html="<html><body>No wins table</body></html>")

    sync(show, client)

    source.refresh_from_db()
    assert source.latest_revision == "100"
    assert source.page_title == "Existing title"
    assert ImportRun.objects.get().status == ImportRun.Status.FAILED
    assert ImportIssue.objects.filter(
        issue_type=ImportIssue.IssueType.INVALID_SOURCE
    ).exists()


@pytest.mark.django_db
def test_new_win_has_source_provenance_and_rerun_is_idempotent(show):
    client = FakeClient(revision="101")

    first = sync(show, client)
    second = sync(show, client)

    win = Win.objects.get()
    assert first.wins_added == 1
    assert second.wins_added == 0
    assert win.source_type == Win.SourceType.WIKIPEDIA
    assert win.source_revision == "101"
    assert win.source_page.year == 2026
    assert Artist.objects.count() == 1
    assert Song.objects.count() == 1


@pytest.mark.django_db
def test_existing_different_winner_is_quarantined_and_counted(show):
    old_artist = Artist.objects.create(name="Existing Artist")
    old_song = Song.objects.create(artist=old_artist, title="Existing Song")
    Win.objects.create(show=show, song=old_song, date=date(2026, 1, 3))
    client = FakeClient(
        html=wins_html(("January 3", "Different Artist", "Different Song"))
    )

    summary = sync(show, client)

    run = ImportRun.objects.get()
    assert summary.conflicts_found == 1
    assert run.conflicts_found == 1
    assert Win.objects.count() == 1
    assert not Artist.objects.filter(name="Different Artist").exists()
    assert ImportIssue.objects.filter(
        issue_type=ImportIssue.IssueType.CONFLICT
    ).exists()


@pytest.mark.django_db
def test_source_missing_win_is_reported_without_deletion(show):
    old_artist = Artist.objects.create(name="Historical Artist")
    old_song = Song.objects.create(artist=old_artist, title="Historical Song")
    old_win = Win.objects.create(show=show, song=old_song, date=date(2026, 1, 3))
    client = FakeClient(html=wins_html(("January 10", "New Artist", "New Song")))

    sync(show, client)

    assert Win.objects.filter(pk=old_win.pk).exists()
    assert ImportIssue.objects.filter(
        issue_type=ImportIssue.IssueType.MISSING_WIN
    ).exists()


@pytest.mark.django_db
def test_alias_resolution_and_unseen_collaboration_are_exact(show):
    canonical = Artist.objects.create(name="Big Bang")
    ArtistAlias.objects.create(alias="BigBang", artist=canonical)
    client = FakeClient(
        revision="102",
        html=wins_html(
            ("January 3", "BigBang", "Fantastic Baby"),
            ("January 10", "Alpha and Beta feat. Gamma", "Joint Song"),
        ),
    )

    sync(show, client)

    assert Artist.objects.filter(name="Big Bang").count() == 1
    assert not Artist.objects.filter(name="BigBang").exists()
    collaboration = Artist.objects.get(name="Alpha and Beta feat. Gamma")
    assert collaboration.songs.get(title="Joint Song")


@pytest.mark.django_db
def test_quoted_wikipedia_song_matches_unquoted_canonical_title(show):
    artist = Artist.objects.create(name="Quoted Artist")
    song = Song.objects.create(artist=artist, title="Friday")
    client = FakeClient(
        revision="103",
        html=wins_html(("January 3", "Quoted Artist", '"Friday"')),
    )

    first = sync(show, client)
    second = sync(show, client)

    assert first.wins_added == 1
    assert second.wins_added == 0
    assert Song.objects.get(pk=song.pk).title == "Friday"
    assert Song.objects.filter(artist=artist).count() == 1
    assert Win.objects.get().song_id == song.pk


class CapturingImporter:
    def __init__(self):
        self.calls = []

    def sync(self, **kwargs):
        self.calls.append(kwargs)
        return ImportSummary()


@pytest.mark.django_db
def test_command_defaults_to_current_previous_year_and_active_shows(
    monkeypatch, capsys
):
    MusicShow.objects.create(slug="music-bank", name="Music Bank", active=True)
    MusicShow.objects.create(slug="inkigayo", name="Inkigayo", active=False)

    class FixedDate:
        @classmethod
        def today(cls):
            return date(2026, 8, 17)

    import main.management.commands.sync_wikipedia as command_module

    importer = CapturingImporter()
    monkeypatch.setattr(command_module, "WikipediaImporter", lambda: importer)
    monkeypatch.setattr(command_module, "date", FixedDate)

    call_command("sync_wikipedia")

    assert importer.calls == [
        {"shows": ["music-bank"], "years": [2025, 2026], "dry_run": False}
    ]
    capsys.readouterr()


@pytest.mark.django_db
def test_command_accepts_repeatable_filters_and_rejects_invalid_values(monkeypatch):
    MusicShow.objects.create(slug="music-bank", name="Music Bank", active=True)
    MusicShow.objects.create(slug="inkigayo", name="Inkigayo", active=False)
    import main.management.commands.sync_wikipedia as command_module

    importer = CapturingImporter()
    monkeypatch.setattr(command_module, "WikipediaImporter", lambda: importer)

    call_command(
        "sync_wikipedia",
        years=[2024, 2025],
        shows=["inkigayo", "music-bank"],
        dry_run=True,
    )
    assert importer.calls[-1] == {
        "shows": ["inkigayo", "music-bank"],
        "years": [2024, 2025],
        "dry_run": True,
    }

    with pytest.raises(CommandError, match="Unknown show"):
        call_command("sync_wikipedia", shows=["missing"])
    with pytest.raises(CommandError, match="before 2014"):
        call_command("sync_wikipedia", years=[2013])
