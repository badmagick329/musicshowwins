from __future__ import annotations

import json
from io import StringIO

import pytest

from kpopwins_operator.cli import main
from kpopwins_operator.database import insert_candidate
from kpopwins_operator.reddit import REDDIT_ENTRY_POINT, canonical_watch_url
from kpopwins_operator.reddit_import import (
    RedditOfficialImportError,
    import_official_links,
    load_official_audit_links,
)

TIMESTAMP = "2026-09-05T12:00:00Z"


def report_document(*, episodes=None):
    return {
        "version": 1,
        "source": {"entry_point": REDDIT_ENTRY_POINT},
        "collection_complete": True,
        "episodes": episodes or [],
    }


def audit_link(video_id, **changes):
    link = {
        "provider": "youtube",
        "classification": "new_official",
        "external_id": video_id,
        "canonical_url": canonical_watch_url(video_id),
    }
    link.update(changes)
    return link


def episode(show_slug, win_date, links, *, has_local_win=True):
    return {
        "show_slug": show_slug,
        "win_date": win_date,
        "episode_url": f"https://www.reddit.com/r/kpop/wiki/{show_slug}/{win_date}",
        "has_local_win": has_local_win,
        "links": links,
    }


def write_report(path, document):
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


def add_current_state(
    connection,
    show_slug,
    win_date,
    video_id,
    *,
    win_current=True,
    video_status="active",
    channel_active=True,
    video_channel_title=None,
):
    channel_id = f"UC-{show_slug}"
    connection.execute(
        """
        INSERT INTO wins (
            show_slug, win_date, api_win_id, artist_name, song_title,
            is_current, last_seen_at
        ) VALUES (?, ?, ?, 'Artist', 'Song', ?, ?)
        """,
        (
            show_slug,
            win_date,
            abs(hash((show_slug, win_date))) % 1_000_000,
            win_current,
            TIMESTAMP,
        ),
    )
    connection.execute(
        """
        INSERT INTO youtube_channels (
            show_slug, configured_handle, channel_id, channel_title,
            uploads_playlist_id, verified_at, is_active
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (show_slug, configured_handle) DO UPDATE SET
            is_active = excluded.is_active
        """,
        (
            show_slug,
            f"@{show_slug}",
            channel_id,
            f"Channel {show_slug}",
            f"UU-{show_slug}",
            TIMESTAMP,
            channel_active,
        ),
    )
    connection.execute(
        """
        INSERT INTO youtube_videos (
            video_id, channel_id, channel_title, title, description,
            published_at, duration, privacy_status, embeddable,
            live_broadcast_state, availability_status, first_seen_at,
            last_seen_at
        ) VALUES (?, ?, ?, ?, 'Description', '2026-01-02T03:04:05Z',
                  'PT3M', 'public', 1, 'none', ?, ?, ?)
        """,
        (
            video_id,
            channel_id,
            (
                f"Channel {show_slug}"
                if video_channel_title is None
                else video_channel_title
            ),
            f"Title {video_id}",
            video_status,
            TIMESTAMP,
            TIMESTAMP,
        ),
    )
    connection.commit()


@pytest.mark.parametrize(
    "document",
    [
        [],
        {**report_document(), "version": 2},
        {**report_document(), "source": {"entry_point": "https://example.test"}},
        {**report_document(), "collection_complete": False},
        {**report_document(), "collection_complete": 1},
        {**report_document(), "episodes": {}},
        {**report_document(), "episodes": [None]},
        {**report_document(), "episodes": [{"links": {}}]},
        {**report_document(), "episodes": [{"links": [None]}]},
    ],
)
def test_rejects_unsupported_malformed_and_incomplete_reports(tmp_path, document):
    path = write_report(tmp_path / "audit.json", document)
    with pytest.raises(ValueError):
        load_official_audit_links(path)


def test_rejects_invalid_json_and_excludes_invalid_official_url(tmp_path):
    invalid_json = tmp_path / "invalid.json"
    invalid_json.write_text("{", encoding="utf-8")
    with pytest.raises(ValueError, match="not valid JSON"):
        load_official_audit_links(invalid_json)

    malformed = report_document(
        episodes=[
            episode(
                "music-bank",
                "2026-01-02",
                [audit_link("video000001", canonical_url="https://example.test")],
            )
        ]
    )
    path = write_report(tmp_path / "malformed.json", malformed)
    assert load_official_audit_links(path) == []


def test_filters_and_deduplicates_deterministically_without_changing_report(tmp_path):
    document = report_document(
        episodes=[
            episode("the-show", "2026-01-03", [audit_link("video000003")]),
            episode(
                "music-bank",
                "2026-01-02",
                [
                    audit_link("video000002", classification="new_unverified"),
                    audit_link("video000001"),
                    audit_link("video000001"),
                    audit_link("", canonical_url=""),
                    audit_link("video000004", provider="naver"),
                    audit_link("video000005", classification="known_unavailable"),
                ],
            ),
            episode(
                "inkigayo",
                "2026-01-01",
                [audit_link("video000006")],
                has_local_win=False,
            ),
        ]
    )
    path = write_report(tmp_path / "audit.json", document)
    before = path.read_bytes()

    entries = load_official_audit_links(path)

    assert [(entry.show_slug, entry.win_date, entry.video_id) for entry in entries] == [
        ("music-bank", "2026-01-02", "video000001"),
        ("the-show", "2026-01-03", "video000003"),
    ]
    assert path.read_bytes() == before


def test_import_creates_pending_candidate_with_current_metadata(connection, tmp_path):
    add_current_state(connection, "music-bank", "2026-01-02", "video000001")
    path = write_report(
        tmp_path / "audit.json",
        report_document(
            episodes=[episode("music-bank", "2026-01-02", [audit_link("video000001")])]
        ),
    )

    before_report = path.read_bytes()
    entries = load_official_audit_links(path)
    counts = import_official_links(
        connection,
        entries,
        limit=None,
        dry_run=False,
        timestamp=TIMESTAMP,
    )

    assert (counts.eligible, counts.selected, counts.created, counts.existing) == (
        1,
        1,
        1,
        0,
    )
    row = connection.execute("SELECT * FROM reference_candidates").fetchone()
    assert row["reference_type"] == "video"
    assert row["provider"] == "youtube"
    assert row["external_id"] == "video000001"
    assert row["url"] == canonical_watch_url("video000001")
    assert row["title"] == "Title video000001"
    assert row["publisher_name"] == "Channel music-bank"
    assert row["publisher_external_id"] == "UC-music-bank"
    assert row["is_official"] == 1
    assert row["status"] == "active"
    assert row["published_at"] == "2026-01-02T03:04:05Z"
    assert row["last_verified_at"] == TIMESTAMP
    assert row["review_status"] == "pending"
    assert row["created_at"] == row["updated_at"] == TIMESTAMP
    assert json.loads(row["metadata"]) == {
        "reddit_audit": {
            "classification": "new_official",
            "episode_url": ("https://www.reddit.com/r/kpop/wiki/music-bank/2026-01-02"),
        }
    }
    assert path.read_bytes() == before_report

    rerun = import_official_links(
        connection,
        entries,
        limit=None,
        dry_run=False,
        timestamp="2026-09-06T12:00:00Z",
    )
    assert (rerun.created, rerun.existing) == (0, 1)
    assert (
        connection.execute("SELECT COUNT(*) FROM reference_candidates").fetchone()[0]
        == 1
    )


def test_import_falls_back_to_verified_channel_title(connection, tmp_path):
    add_current_state(
        connection,
        "music-bank",
        "2026-01-02",
        "video000001",
        video_channel_title="",
    )
    path = write_report(
        tmp_path / "audit.json",
        report_document(
            episodes=[episode("music-bank", "2026-01-02", [audit_link("video000001")])]
        ),
    )

    import_official_links(
        connection,
        load_official_audit_links(path),
        limit=None,
        dry_run=False,
        timestamp=TIMESTAMP,
    )

    row = connection.execute(
        "SELECT publisher_name FROM reference_candidates"
    ).fetchone()
    assert row["publisher_name"] == "Channel music-bank"


def test_dry_run_and_limit_use_same_validation_and_deterministic_prefix(
    connection, tmp_path
):
    items = [
        ("the-show", "2026-01-03", "video000003"),
        ("music-bank", "2026-01-02", "video000002"),
        ("music-bank", "2026-01-01", "video000001"),
    ]
    for item in items:
        add_current_state(connection, *item)
    path = write_report(
        tmp_path / "audit.json",
        report_document(
            episodes=[
                episode(show, date, [audit_link(video)]) for show, date, video in items
            ]
        ),
    )

    counts = import_official_links(
        connection,
        load_official_audit_links(path),
        limit=2,
        dry_run=True,
        timestamp=TIMESTAMP,
    )

    assert (counts.eligible, counts.selected, counts.created, counts.existing) == (
        3,
        2,
        2,
        0,
    )
    assert (
        connection.execute("SELECT COUNT(*) FROM reference_candidates").fetchone()[0]
        == 0
    )

    import_official_links(
        connection,
        load_official_audit_links(path),
        limit=2,
        dry_run=False,
        timestamp=TIMESTAMP,
    )
    rows = connection.execute(
        "SELECT show_slug, win_date, external_id FROM reference_candidates "
        "ORDER BY show_slug, win_date, external_id"
    )
    assert [tuple(row) for row in rows] == [
        ("music-bank", "2026-01-01", "video000001"),
        ("music-bank", "2026-01-02", "video000002"),
    ]


def _existing_candidate(show_slug, win_date, video_id, review_status):
    return {
        "show_slug": show_slug,
        "win_date": win_date,
        "reference_type": "video",
        "provider": "youtube",
        "external_id": video_id,
        "url": canonical_watch_url(video_id),
        "title": "Reviewed title",
        "publisher_name": "Reviewed publisher",
        "publisher_external_id": "UC-reviewed",
        "is_official": False,
        "status": "active",
        "published_at": None,
        "last_verified_at": None,
        "metadata": {"keep": True},
        "review_status": review_status,
    }


def test_reruns_preserve_existing_pending_approved_and_rejected_candidates(
    connection, tmp_path
):
    statuses = ("pending", "approved", "rejected")
    episodes = []
    for index, status in enumerate(statuses, start=1):
        win_date = f"2026-01-0{index}"
        video_id = f"video00000{index}"
        add_current_state(connection, "music-bank", win_date, video_id)
        candidate = _existing_candidate("music-bank", win_date, video_id, status)
        if status == "rejected":
            candidate["external_id"] = ""
        insert_candidate(
            connection,
            candidate,
            timestamp="2026-09-01T00:00:00Z",
        )
        episodes.append(episode("music-bank", win_date, [audit_link(video_id)]))
    connection.commit()
    before = list(connection.execute("SELECT * FROM reference_candidates ORDER BY id"))
    path = write_report(tmp_path / "audit.json", report_document(episodes=episodes))

    counts = import_official_links(
        connection,
        load_official_audit_links(path),
        limit=None,
        dry_run=False,
        timestamp=TIMESTAMP,
    )

    after = list(connection.execute("SELECT * FROM reference_candidates ORDER BY id"))
    assert (counts.created, counts.existing) == (0, 3)
    assert [tuple(row) for row in after] == [tuple(row) for row in before]


@pytest.mark.parametrize("stale_kind", ["win", "missing_video", "video", "channel"])
def test_stale_report_validation_fails_before_any_insert(
    connection, tmp_path, stale_kind
):
    add_current_state(connection, "inkigayo", "2026-01-01", "video000001")
    add_current_state(
        connection,
        "music-bank",
        "2026-01-02",
        "video000002",
        win_current=stale_kind != "win",
        video_status="unavailable" if stale_kind == "video" else "active",
        channel_active=stale_kind != "channel",
    )
    if stale_kind == "missing_video":
        connection.execute("DELETE FROM youtube_videos WHERE video_id = 'video000002'")
        connection.commit()
    path = write_report(
        tmp_path / "audit.json",
        report_document(
            episodes=[
                episode("inkigayo", "2026-01-01", [audit_link("video000001")]),
                episode("music-bank", "2026-01-02", [audit_link("video000002")]),
            ]
        ),
    )

    with pytest.raises(RedditOfficialImportError, match="Stale Reddit audit"):
        import_official_links(
            connection,
            load_official_audit_links(path),
            limit=None,
            dry_run=False,
            timestamp=TIMESTAMP,
        )
    assert (
        connection.execute("SELECT COUNT(*) FROM reference_candidates").fetchone()[0]
        == 0
    )


def test_cli_input_override_prints_summary_without_external_calls(
    config, connection, tmp_path
):
    add_current_state(connection, "music-bank", "2026-01-02", "video000001")
    path = write_report(
        tmp_path / "custom.json",
        report_document(
            episodes=[episode("music-bank", "2026-01-02", [audit_link("video000001")])]
        ),
    )
    output = StringIO()

    result = main(
        ["reddit", "import-official", "--input", str(path), "--dry-run"],
        environ={"KPOPWINS_OPERATOR_HOME": str(config.home)},
        stdout=output,
        stderr=StringIO(),
        now=TIMESTAMP,
    )

    assert result == 0
    assert output.getvalue() == (
        "eligible=1 selected=1 created=1 existing=0 dry-run=yes\n"
    )
    assert (
        connection.execute("SELECT COUNT(*) FROM reference_candidates").fetchone()[0]
        == 0
    )
