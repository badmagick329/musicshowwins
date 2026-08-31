from __future__ import annotations

import pytest

from kpopwins_operator.channel_verification import (
    apply_verified_channels,
    verify_channels,
)
from kpopwins_operator.ingestion import ingest_channels
from kpopwins_operator.registry import ChannelEntry
from kpopwins_operator.youtube import PlaylistPage, ResolvedChannel, Video, YouTubeError


class ResolveClient:
    def __init__(self, channel_ids):
        self.channel_ids = iter(channel_ids)

    def resolve_handle(self, handle):
        channel_id = next(self.channel_ids)
        return ResolvedChannel(channel_id, f"Title {handle}", f"UU-{channel_id}")


def entry(show="music-bank", handle="@KBSKpop", allow=False):
    return ChannelEntry(show, handle, ("music bank", "뮤직뱅크"), allow)


def test_verification_is_dry_until_applied_and_rejects_unallowed_channel_collision(
    connection,
):
    verified = verify_channels([entry()], ResolveClient(["UC1"]))
    assert (
        connection.execute("SELECT COUNT(*) FROM youtube_channels").fetchone()[0] == 0
    )
    apply_verified_channels(
        connection,
        verified,
        verified_at="2026-08-31T12:00:00Z",
        full_registry=True,
    )
    row = connection.execute("SELECT * FROM youtube_channels").fetchone()
    assert (row["show_slug"], row["channel_id"], row["uploads_playlist_id"]) == (
        "music-bank",
        "UC1",
        "UU-UC1",
    )

    with pytest.raises(YouTubeError, match="duplicate channel ID"):
        verify_channels(
            [entry(), entry("music-core", "@MBCkpop")],
            ResolveClient(["UCX", "UCX"]),
        )
    allowed = verify_channels(
        [entry(allow=True), entry("music-core", "@MBCkpop", True)],
        ResolveClient(["UCX", "UCX"]),
    )
    assert len(allowed) == 2


def add_channel(connection):
    connection.execute(
        """
        INSERT INTO youtube_channels (
            show_slug, configured_handle, channel_id, channel_title,
            uploads_playlist_id, verified_at
        ) VALUES ('music-bank', '@KBSKpop', 'UC1', 'KBS Kpop', 'UU1', 'now')
        """
    )
    connection.execute(
        "INSERT INTO youtube_ingestion_state (channel_id) VALUES ('UC1')"
    )
    connection.commit()


def video(identifier, *, channel="UC1", published="2026-01-02T00:00:00Z"):
    return Video(
        identifier,
        channel,
        f"Video {identifier}",
        "Description",
        published,
        "PT3M",
        "public",
        True,
        "none",
    )


class IngestClient:
    def __init__(self, pages, videos):
        self.pages = list(pages)
        self.video_results = list(videos)
        self.tokens = []
        self.batches = []

    def playlist_page(self, playlist_id, token):
        assert playlist_id == "UU1"
        self.tokens.append(token)
        return self.pages.pop(0)

    def videos(self, identifiers):
        self.batches.append(list(identifiers))
        result = self.video_results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


def test_initial_ingestion_resumes_checkpoint_and_marks_omissions_unavailable(
    connection,
):
    add_channel(connection)
    first = IngestClient(
        [
            PlaylistPage(
                ("v1", "v2"),
                {"v1": "2026-01-02T00:00:00Z", "v2": "2026-01-01T00:00:00Z"},
                "PAGE2",
            )
        ],
        [[video("v1"), video("v2")]],
    )
    counts = ingest_channels(
        connection,
        first,
        handle=None,
        max_pages=1,
        restart=False,
        timestamp="2026-08-31T12:00:00Z",
    )
    assert counts.added == 2 and counts.more_remaining
    state = connection.execute("SELECT * FROM youtube_ingestion_state").fetchone()
    assert state["next_page_token"] == "PAGE2"
    assert not state["initial_scan_complete"]

    second = IngestClient(
        [
            PlaylistPage(
                ("v2", "old"),
                {"v2": "2014-01-01T00:00:00Z", "old": "2013-11-30T00:00:00Z"},
                "PAGE3",
            )
        ],
        [[]],
    )
    counts = ingest_channels(
        connection,
        second,
        handle=None,
        max_pages=2,
        restart=False,
        timestamp="2026-09-01T12:00:00Z",
    )
    assert second.tokens == ["PAGE2"]
    assert counts.unavailable == 1
    assert (
        connection.execute(
            "SELECT availability_status FROM youtube_videos WHERE video_id='v2'"
        ).fetchone()[0]
        == "unavailable"
    )
    state = connection.execute("SELECT * FROM youtube_ingestion_state").fetchone()
    assert state["initial_scan_complete"] == 1
    assert state["next_page_token"] is None


def test_failed_page_leaves_checkpoint_and_video_rows_unchanged(connection):
    add_channel(connection)
    connection.execute(
        "UPDATE youtube_ingestion_state SET next_page_token = 'KEEP' "
        "WHERE channel_id='UC1'"
    )
    connection.commit()
    client = IngestClient(
        [PlaylistPage(("bad",), {"bad": "2026-01-01T00:00:00Z"}, "NEXT")],
        [[video("bad", channel="WRONG")]],
    )
    with pytest.raises(ValueError, match="unexpected channel"):
        ingest_channels(
            connection,
            client,
            handle=None,
            max_pages=1,
            restart=False,
            timestamp="2026-08-31T12:00:00Z",
        )
    state = connection.execute("SELECT * FROM youtube_ingestion_state").fetchone()
    assert state["next_page_token"] == "KEEP"
    assert connection.execute("SELECT COUNT(*) FROM youtube_videos").fetchone()[0] == 0


def test_restart_discards_saved_initial_checkpoint(connection):
    add_channel(connection)
    connection.execute(
        "UPDATE youtube_ingestion_state SET next_page_token='OLD' "
        "WHERE channel_id='UC1'"
    )
    connection.commit()
    client = IngestClient([PlaylistPage((), {}, None)], [[]])
    ingest_channels(
        connection,
        client,
        handle="@KBSKpop",
        max_pages=1,
        restart=True,
        timestamp="2026-08-31T12:00:00Z",
    )
    assert client.tokens == [None]


def test_incremental_ingestion_stops_after_first_all_known_page(connection):
    add_channel(connection)
    connection.execute(
        "UPDATE youtube_ingestion_state SET initial_scan_complete=1 "
        "WHERE channel_id='UC1'"
    )
    existing = video("known")
    connection.execute(
        """
        INSERT INTO youtube_videos (
            video_id, channel_id, title, description, published_at, duration,
            privacy_status, embeddable, live_broadcast_state,
            availability_status, first_seen_at, last_seen_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', 'old', 'old')
        """,
        (
            existing.video_id,
            existing.channel_id,
            existing.title,
            existing.description,
            existing.published_at,
            existing.duration,
            existing.privacy_status,
            int(existing.embeddable),
            existing.live_broadcast_state,
        ),
    )
    connection.commit()
    client = IngestClient(
        [PlaylistPage(("known",), {"known": "2026-01-02T00:00:00Z"}, "NOT-USED")],
        [[existing]],
    )
    counts = ingest_channels(
        connection,
        client,
        handle=None,
        max_pages=10,
        restart=False,
        timestamp="2026-08-31T12:00:00Z",
    )
    assert counts.pages == 1
    assert client.tokens == [None]


def test_historical_cutoff_marks_initial_scan_complete(connection):
    add_channel(connection)
    client = IngestClient(
        [PlaylistPage(("old",), {"old": "2013-11-30T23:59:59Z"}, "OLDER-PAGE")],
        [[]],
    )
    counts = ingest_channels(
        connection,
        client,
        handle=None,
        max_pages=10,
        restart=False,
        timestamp="2026-08-31T12:00:00Z",
    )
    assert counts.discovered == 0
    state = connection.execute("SELECT * FROM youtube_ingestion_state").fetchone()
    assert state["initial_scan_complete"] == 1
    assert state["next_page_token"] is None


def test_ingestion_batches_video_lookups_at_fifty_ids(connection):
    add_channel(connection)
    identifiers = tuple(f"v{index}" for index in range(51))
    published = {identifier: "2026-01-01T00:00:00Z" for identifier in identifiers}
    client = IngestClient(
        [PlaylistPage(identifiers, published, None)],
        [
            [video(identifier) for identifier in identifiers[:50]],
            [video(identifiers[50])],
        ],
    )
    counts = ingest_channels(
        connection,
        client,
        handle=None,
        max_pages=1,
        restart=False,
        timestamp="2026-08-31T12:00:00Z",
    )
    assert [len(batch) for batch in client.batches] == [50, 1]
    assert counts.added == 51
