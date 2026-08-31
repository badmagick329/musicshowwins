from __future__ import annotations

import json
from datetime import date
from io import StringIO

import pytest

from kpopwins_operator.candidate_review import (
    list_candidates,
    review_candidates,
    show_candidate,
)
from kpopwins_operator.cli import main
from kpopwins_operator.database import due_searches, insert_candidate
from kpopwins_operator.manifest import approved_document
from kpopwins_operator.matching import match_videos, score_video
from kpopwins_operator.registry import ChannelEntry

from .conftest import add_win

REGISTRY = [ChannelEntry("music-bank", "@KBSKpop", ("music bank", "뮤직뱅크"))]


def add_match_data(connection, title="Alpha First Music Bank 1위"):
    add_win(connection)
    connection.execute(
        """
        INSERT INTO youtube_channels (
            show_slug, configured_handle, channel_id, channel_title,
            uploads_playlist_id, verified_at
        ) VALUES ('music-bank', '@KBSKpop', 'UC1', 'KBS Kpop', 'UU1', 'now')
        """
    )
    connection.execute(
        """
        INSERT INTO youtube_videos (
            video_id, channel_id, title, description, published_at, duration,
            privacy_status, embeddable, live_broadcast_state,
            availability_status, first_seen_at, last_seen_at
        ) VALUES ('v1', 'UC1', ?, '', '2026-01-02T01:00:00Z', 'PT3M',
                  'public', 1, 'none', 'active', 'now', 'now')
        """,
        (title,),
    )
    connection.commit()


def test_match_gates_require_artist_and_win_term():
    common = {
        "description": "",
        "artist": "Alpha",
        "song": "First",
        "show_keywords": ("music bank",),
        "win_date": date(2026, 1, 2),
        "publication_date": date(2026, 1, 2),
    }
    assert score_video(title="First Music Bank winner", **common) is None
    assert score_video(title="Alpha First Music Bank stage", **common) is None
    positive = score_video(title="Alpha First Music Bank winner", **common)
    negative = score_video(title="Alpha First Music Bank winner fancam", **common)
    assert positive and negative and positive[0] > negative[0]
    hash_one = score_video(title="Alpha First Music Bank #1", **common)
    assert hash_one and "win term: #1" in hash_one[1]
    assert (
        score_video(
            title="Winner First Music Bank",
            **{**common, "artist": "I"},
        )
        is None
    )


def test_matching_is_idempotent_preserves_review_and_dry_run_is_read_only(connection):
    add_match_data(connection)
    first = match_videos(
        connection,
        REGISTRY,
        show=None,
        min_score=75,
        limit=None,
        dry_run=False,
        timestamp="2026-08-31T12:00:00Z",
    )
    assert first.created == 1
    candidate = connection.execute("SELECT * FROM reference_candidates").fetchone()
    assert json.loads(candidate["metadata"])["youtube_match"]["score"] >= 75
    evidence = connection.execute("SELECT * FROM youtube_candidate_matches").fetchone()
    assert evidence["show_mapping"] == "music-bank"
    assert evidence["korean_publication_date"] == "2026-01-02"
    assert "artist phrase" in json.loads(evidence["reasons"])
    assert candidate["review_status"] == "pending"

    connection.execute(
        "UPDATE reference_candidates SET review_status='rejected' WHERE id=?",
        (candidate["id"],),
    )
    connection.commit()
    second = match_videos(
        connection,
        REGISTRY,
        show="music-bank",
        min_score=75,
        limit=1,
        dry_run=False,
        timestamp="2026-09-01T12:00:00Z",
    )
    assert second.updated == 1
    assert (
        connection.execute("SELECT review_status FROM reference_candidates").fetchone()[
            0
        ]
        == "rejected"
    )

    before = connection.total_changes
    dry = match_videos(
        connection,
        REGISTRY,
        show=None,
        min_score=0,
        limit=None,
        dry_run=True,
        timestamp="2026-09-02T12:00:00Z",
    )
    assert dry.accepted == 1
    assert connection.total_changes == before

    output = StringIO()
    list_candidates(
        connection,
        output,
        status="rejected",
        show="music-bank",
        provider="YouTube",
        minimum_score=75,
        limit=10,
    )
    assert "KBS Kpop" in output.getvalue()
    details = StringIO()
    show_candidate(connection, details, candidate["id"])
    assert "reasons:" in details.getvalue()
    assert "publisher_name: KBS Kpop" in details.getvalue()


def test_approve_and_reject_are_atomic_and_approval_marks_search_matched(connection):
    add_match_data(connection)
    match_videos(
        connection,
        REGISTRY,
        show=None,
        min_score=75,
        limit=None,
        dry_run=False,
        timestamp="2026-08-31T12:00:00Z",
    )
    candidate_id = connection.execute("SELECT id FROM reference_candidates").fetchone()[
        0
    ]
    with pytest.raises(ValueError, match="not found"):
        review_candidates(
            connection,
            [candidate_id, 999],
            decision="approved",
            timestamp="2026-09-01T12:00:00Z",
        )
    assert (
        connection.execute("SELECT review_status FROM reference_candidates").fetchone()[
            0
        ]
        == "pending"
    )

    review_candidates(
        connection,
        [candidate_id],
        decision="approved",
        timestamp="2026-09-01T12:00:00Z",
    )
    assert (
        connection.execute("SELECT status FROM search_state").fetchone()[0] == "matched"
    )
    document = approved_document(connection)
    assert document["references"][0]["external_id"] == "v1"
    assert document["references"][0]["metadata"] == {}

    review_candidates(
        connection,
        [candidate_id],
        decision="rejected",
        timestamp="2026-09-02T12:00:00Z",
    )
    assert (
        connection.execute("SELECT status FROM search_state").fetchone()[0] == "pending"
    )
    assert (
        len(
            due_searches(
                connection,
                "youtube",
                due_at="2026-09-02T12:00:00Z",
                limit=None,
            )
        )
        == 1
    )


def test_reject_keeps_matched_when_another_approved_youtube_candidate_exists(
    connection,
):
    add_match_data(connection)
    match_videos(
        connection,
        REGISTRY,
        show=None,
        min_score=75,
        limit=None,
        dry_run=False,
        timestamp="2026-08-31T12:00:00Z",
    )
    first_id = connection.execute("SELECT id FROM reference_candidates").fetchone()[0]
    insert_candidate(
        connection,
        {
            "show_slug": "music-bank",
            "win_date": "2026-01-02",
            "reference_type": "video",
            "provider": "youtube",
            "external_id": "v2",
            "url": "https://www.youtube.com/watch?v=v2",
            "review_status": "approved",
        },
        timestamp="2026-08-31T12:00:00Z",
    )
    connection.commit()
    review_candidates(
        connection,
        [first_id],
        decision="approved",
        timestamp="2026-09-01T12:00:00Z",
    )
    review_candidates(
        connection,
        [first_id],
        decision="rejected",
        timestamp="2026-09-02T12:00:00Z",
    )
    assert connection.execute("SELECT status FROM search_state").fetchone()[0] == (
        "matched"
    )


def test_reject_never_approved_candidate_preserves_search_state(connection):
    add_match_data(connection)
    match_videos(
        connection,
        REGISTRY,
        show=None,
        min_score=75,
        limit=None,
        dry_run=False,
        timestamp="2026-08-31T12:00:00Z",
    )
    candidate_id = connection.execute("SELECT id FROM reference_candidates").fetchone()[
        0
    ]
    connection.execute(
        """
        INSERT INTO search_state (
            show_slug, win_date, provider, status, attempt_count,
            last_error, updated_at
        ) VALUES ('music-bank', '2026-01-02', 'youtube', 'disabled', 3,
                  'manual', '2026-08-31T12:00:00Z')
        """
    )
    connection.commit()
    review_candidates(
        connection,
        [candidate_id],
        decision="rejected",
        timestamp="2026-09-02T12:00:00Z",
    )
    state = connection.execute("SELECT * FROM search_state").fetchone()
    assert (state["status"], state["attempt_count"], state["last_error"]) == (
        "disabled",
        3,
        "manual",
    )


def test_unavailable_video_updates_candidate_and_date_window_is_enforced(connection):
    add_match_data(connection)
    match_videos(
        connection,
        REGISTRY,
        show=None,
        min_score=75,
        limit=None,
        dry_run=False,
        timestamp="2026-08-31T12:00:00Z",
    )
    connection.execute(
        "UPDATE youtube_videos SET availability_status='unavailable' "
        "WHERE video_id='v1'"
    )
    connection.execute(
        """
        INSERT INTO youtube_videos (
            video_id, channel_id, title, description, published_at, duration,
            privacy_status, embeddable, live_broadcast_state,
            availability_status, first_seen_at, last_seen_at
        ) VALUES ('outside', 'UC1', 'Alpha First Music Bank winner', '',
                  '2026-01-20T00:00:00Z', '', 'public', 1, 'none',
                  'active', 'now', 'now')
        """
    )
    connection.commit()
    counts = match_videos(
        connection,
        REGISTRY,
        show=None,
        min_score=0,
        limit=None,
        dry_run=False,
        timestamp="2026-09-01T12:00:00Z",
    )
    assert counts.accepted == 0
    assert (
        connection.execute(
            "SELECT status FROM reference_candidates WHERE external_id='v1'"
        ).fetchone()[0]
        == "unavailable"
    )
    assert (
        connection.execute(
            "SELECT COUNT(*) FROM reference_candidates WHERE external_id='outside'"
        ).fetchone()[0]
        == 0
    )


def test_matching_query_excludes_videos_outside_korean_date_window(connection):
    add_match_data(connection)
    connection.execute("DELETE FROM youtube_videos")
    for video_id, published_at in (
        ("inside", "2026-01-09T14:59:59Z"),
        ("too-early", "2025-12-31T14:59:59Z"),
        ("too-late", "2026-01-09T15:00:00Z"),
    ):
        connection.execute(
            """
            INSERT INTO youtube_videos (
                video_id, channel_id, title, description, published_at,
                duration, privacy_status, embeddable, live_broadcast_state,
                availability_status, first_seen_at, last_seen_at
            ) VALUES (?, 'UC1', 'Alpha First Music Bank winner', '', ?, '',
                      'public', 1, 'none', 'active', 'now', 'now')
            """,
            (video_id, published_at),
        )
    connection.commit()
    counts = match_videos(
        connection,
        REGISTRY,
        show=None,
        min_score=0,
        limit=None,
        dry_run=False,
        timestamp="2026-09-01T12:00:00Z",
    )
    assert counts.considered == 1
    assert counts.accepted == 1
    assert (
        connection.execute("SELECT external_id FROM reference_candidates").fetchone()[0]
        == "inside"
    )


def test_local_match_cli_does_not_require_youtube_api_key(config, connection):
    output = StringIO()
    result = main(
        ["youtube", "match", "--dry-run"],
        environ={"KPOPWINS_OPERATOR_HOME": str(config.home)},
        stdout=output,
        now="2026-08-31T12:00:00Z",
    )
    assert result == 0
    assert "dry-run=yes" in output.getvalue()
