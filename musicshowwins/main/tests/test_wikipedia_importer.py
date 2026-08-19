from __future__ import annotations

import json
from datetime import date, datetime, timezone

import pytest
import requests
from django.core.management import call_command
from django.core.management.base import CommandError

from main.models import (
    Artist,
    ArtistAlias,
    ImportIssue,
    ImportRun,
    MusicShow,
    Song,
    SourceApproval,
    SourcePage,
    Win,
)
from main.wikipedia import (
    DEFAULT_USER_AGENT,
    ImportSummary,
    PageReport,
    RevisionPage,
    WikipediaClient,
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
    if not dry_run:
        SourceApproval.objects.update_or_create(
            show=show,
            year=year,
            defaults={"approved": True, "approved_by": "test"},
        )
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


class FakeResponse:
    def __init__(self, status_code=200, payload=None, headers=None):
        self.status_code = status_code
        self.payload = payload if payload is not None else {"ok": True}
        self.headers = headers or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = []

    def get(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        response = next(self.responses)
        if isinstance(response, BaseException):
            raise response
        return response


def test_wikipedia_client_uses_public_issue_user_agent_by_default(settings):
    settings.WIKI_AGENT = DEFAULT_USER_AGENT
    client = WikipediaClient(session=FakeSession([]))

    assert client.headers["User-Agent"] == DEFAULT_USER_AGENT


@pytest.mark.parametrize(
    "first",
    [
        FakeResponse(status_code=429, headers={"Retry-After": "0"}),
        FakeResponse(status_code=500),
        requests.Timeout("timed out"),
        FakeResponse(
            payload={"error": {"code": "maxlag", "info": "Waiting for replica"}}
        ),
    ],
)
def test_wikipedia_client_retries_transient_failures(first):
    session = FakeSession([first, FakeResponse(payload={"success": 1})])
    delays = []
    client = WikipediaClient(
        session=session, max_retries=1, backoff_factor=3, sleep=delays.append
    )

    assert client._request({"action": "query"}) == {"success": 1}
    assert len(session.calls) == 2
    if isinstance(first, FakeResponse) and first.status_code == 429:
        assert delays == [0]
    else:
        assert delays == [3]


@pytest.mark.django_db
def test_dry_run_page_report_has_reconciliation_counts(show):
    artist = Artist.objects.create(name="New Artist")
    song = Song.objects.create(artist=artist, title="New Song")
    Win.objects.create(show=show, song=song, date=date(2026, 1, 3))
    client = FakeClient()

    summary = sync(show, client, dry_run=True)

    assert summary.as_dict()["pages"] == [
        {
            "show": "music-bank",
            "year": 2026,
            "page_title": "List of Music Bank Chart winners (2026)",
            "revision": "101",
            "status": "unapproved",
            "source_rows": 1,
            "exact_matches": 1,
            "additions": 0,
            "conflicts": 0,
            "missing_legacy": 0,
            "failure": None,
            "addition_candidates": [],
            "conflict_candidates": [],
            "missing_legacy_candidates": [],
        }
    ]
    assert ImportRun.objects.count() == 0


@pytest.mark.django_db
def test_dry_run_page_report_lists_reconciliation_candidates_without_writes(show):
    old_artist = Artist.objects.create(name="Old Artist")
    old_song = Song.objects.create(artist=old_artist, title="Old Song")
    Win.objects.create(show=show, song=old_song, date=date(2026, 1, 3))
    client = FakeClient(
        html=wins_html(
            ("January 3", "Incoming Artist", "Incoming Song"),
            ("January 10", "Added Artist", "Added Song"),
        )
    )

    summary = sync(show, client, dry_run=True)
    page = summary.as_dict()["pages"][0]

    assert page["addition_candidates"] == [
        {"date": "2026-01-10", "artist": "Added Artist", "song": "Added Song"}
    ]
    assert page["conflict_candidates"] == [
        {
            "date": "2026-01-03",
            "incoming": {"artist": "Incoming Artist", "song": "Incoming Song"},
            "existing": [{"artist": "Old Artist", "song": "Old Song"}],
        }
    ]
    assert page["missing_legacy_candidates"] == [
        {"date": "2026-01-03", "artist": "Old Artist", "song": "Old Song"}
    ]
    assert summary.wins_added == 1
    assert summary.conflicts_found == 1
    assert summary.missing_legacy == 1
    assert ImportRun.objects.count() == 0
    assert ImportIssue.objects.count() == 0
    assert Artist.objects.count() == 1
    assert Song.objects.count() == 1
    assert Win.objects.count() == 1


@pytest.mark.django_db
def test_music_core_2016_is_reported_as_known_unavailable(show):
    music_core = MusicShow.objects.create(slug="music-core", name="Music Core")
    client = FakeClient(error=WikipediaFetchError("must not fetch"))

    summary = sync(music_core, client, year=2016, dry_run=True)

    assert summary.failures == []
    assert summary.page_reports == [
        PageReport(
            show="music-core",
            year=2016,
            page_title="List of Show! Music Core Chart winners (2016)",
            status="unavailable",
        )
    ]
    assert client.revision_calls == 0


@pytest.mark.django_db
def test_command_json_is_machine_readable_and_strict_rejects_reconciliation(
    monkeypatch, capsys
):
    MusicShow.objects.create(slug="music-bank", name="Music Bank", active=True)
    import main.management.commands.sync_wikipedia as command_module

    class CapturingImporter:
        def sync(self, **kwargs):
            return ImportSummary(
                wins_added=1,
                page_reports=[
                    PageReport(
                        show="music-bank",
                        year=2026,
                        page_title="Music Bank",
                        status="processed",
                        additions=1,
                    )
                ],
            )

    monkeypatch.setattr(command_module, "WikipediaImporter", CapturingImporter)
    with pytest.raises(CommandError, match="Strict reconciliation"):
        call_command("sync_wikipedia", format="json", strict=True, dry_run=True)

    output = capsys.readouterr().out.strip()
    assert json.loads(output)["wins_added"] == 1


@pytest.mark.django_db
def test_command_raises_on_source_failures(monkeypatch):
    MusicShow.objects.create(slug="music-bank", name="Music Bank", active=True)
    import main.management.commands.sync_wikipedia as command_module

    class CapturingImporter:
        def sync(self, **kwargs):
            return ImportSummary(failures=["music-bank/2026: unavailable"])

    monkeypatch.setattr(command_module, "WikipediaImporter", CapturingImporter)
    with pytest.raises(CommandError, match="source failures"):
        call_command("sync_wikipedia", dry_run=True)


@pytest.mark.django_db
def test_new_source_is_denied_until_explicitly_approved(show):
    client = FakeClient(
        html=wins_html(("January 3", "TBA", "TBA")), revision="2027"
    )

    summary = WikipediaImporter(client).sync(
        shows=[show.slug], years=[2026], dry_run=False
    )

    assert summary.unapproved_pages == 1
    assert summary.page_reports[0].status == "unapproved"
    assert summary.page_reports[0].additions == 1
    assert not SourcePage.objects.exists()
    assert not SourceApproval.objects.exists()
    assert not ImportIssue.objects.exists()
    assert not Win.objects.exists()
    assert not Artist.objects.exists()
    assert not Song.objects.exists()


@pytest.mark.django_db
def test_existing_source_page_without_approval_remains_denied(show):
    source = SourcePage.objects.create(
        show=show,
        year=2026,
        page_title="Existing title",
        latest_revision="100",
    )
    client = FakeClient(revision="101")

    summary = WikipediaImporter(client).sync(
        shows=[show.slug], years=[2026], dry_run=False
    )

    source.refresh_from_db()
    assert summary.page_reports[0].status == "unapproved"
    assert summary.wins_added == 0
    assert source.latest_revision == "100"
    assert Win.objects.count() == 0
    assert ImportIssue.objects.count() == 0


@pytest.mark.django_db
def test_approved_source_can_write_after_manual_approval(show):
    client = FakeClient(html=wins_html(("January 3", "TBA", "TBA")))
    call_command("approve_wikipedia_source", show=show.slug, year=2026)

    summary = WikipediaImporter(client).sync(
        shows=[show.slug], years=[2026], dry_run=False
    )

    assert summary.wins_added == 1
    assert summary.unapproved_pages == 0
    assert Win.objects.get().song.artist.name == "TBA"
    assert SourceApproval.objects.get(show=show, year=2026).approved


@pytest.mark.django_db
def test_unapproved_dry_run_parses_placeholder_without_mutation(show):
    client = FakeClient(html=wins_html(("January 3", "TBA", "TBD")))
    summary = WikipediaImporter(client).sync(
        shows=[show.slug], years=[2026], dry_run=True
    )

    assert summary.page_reports[0].status == "unapproved"
    assert summary.wins_added == 1
    assert ImportRun.objects.count() == 0
    assert SourcePage.objects.count() == 0
    assert SourceApproval.objects.count() == 0
    assert Win.objects.count() == 0


@pytest.mark.django_db
def test_unapproved_malformed_source_fails_without_issue_or_source(show):
    client = FakeClient(html="<table><tr><th>Date</th></tr></table>")
    summary = WikipediaImporter(client).sync(
        shows=[show.slug], years=[2026], dry_run=False
    )

    assert summary.failures
    assert ImportRun.objects.get().status == ImportRun.Status.FAILED
    assert ImportIssue.objects.count() == 0
    assert SourcePage.objects.count() == 0


@pytest.mark.django_db
def test_strict_real_sync_rejects_unapproved_page(show, monkeypatch):
    client = FakeClient()
    import main.management.commands.sync_wikipedia as command_module

    monkeypatch.setattr(
        command_module, "WikipediaImporter", lambda: WikipediaImporter(client)
    )
    with pytest.raises(CommandError, match="Strict reconciliation"):
        call_command("sync_wikipedia", shows=[show.slug], years=[2026], strict=True)

    assert SourcePage.objects.count() == 0
    assert Win.objects.count() == 0


@pytest.mark.django_db
def test_approval_command_can_revoke_source(show):
    call_command("approve_wikipedia_source", show=show.slug, year=2027)
    call_command(
        "approve_wikipedia_source", show=show.slug, year=2027, revoke=True
    )

    approval = SourceApproval.objects.get(show=show, year=2027)
    assert not approval.approved
