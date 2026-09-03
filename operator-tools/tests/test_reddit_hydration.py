from __future__ import annotations

import json
from copy import deepcopy
from io import StringIO

import pytest

from kpopwins_operator.cli import main
from kpopwins_operator.ingestion import upsert_video
from kpopwins_operator.reddit import REDDIT_ENTRY_POINT
from kpopwins_operator.reddit_hydration import (
    RedditHydrationError,
    hydrate_youtube_ids,
    load_reddit_youtube_ids,
)
from kpopwins_operator.youtube import APICallLimit, Video


def report_document(*, episodes=None):
    return {
        "version": 1,
        "source": {"entry_point": REDDIT_ENTRY_POINT},
        "collection_complete": True,
        "episodes": episodes or [],
    }


def eligible_link(video_id, **changes):
    link = {
        "provider": "youtube",
        "classification": "new_unverified",
        "external_id": video_id,
    }
    link.update(changes)
    return link


def write_report(path, document):
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


def video(video_id, *, title=None, channel_title="Uploader"):
    return Video(
        video_id=video_id,
        channel_id="UC-uploader",
        channel_title=channel_title,
        title=title or f"Video {video_id}",
        description="Description",
        published_at="2026-01-02T00:00:00Z",
        duration="PT3M",
        privacy_status="public",
        embeddable=True,
        live_broadcast_state="none",
    )


class Client:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []
        self.calls_used = 0

    def videos(self, video_ids):
        self.calls.append(list(video_ids))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        self.calls_used += 1
        return response


@pytest.mark.parametrize(
    "change, message",
    [
        ({"version": 2}, "version"),
        ({"source": {"entry_point": "https://example.test"}}, "source"),
        ({"collection_complete": False}, "not complete"),
        ({"collection_complete": 1}, "not complete"),
    ],
)
def test_report_validation_rejects_unsupported_or_incomplete_reports(
    tmp_path, change, message
):
    document = report_document()
    document.update(change)
    path = write_report(tmp_path / "audit.json", document)
    with pytest.raises(RedditHydrationError, match=message):
        load_reddit_youtube_ids(path)


def test_report_filtering_and_video_id_deduplication(tmp_path):
    document = report_document(
        episodes=[
            {"has_local_win": False, "links": [eligible_link("not-local")]},
            {
                "has_local_win": True,
                "links": [
                    eligible_link("v1"),
                    eligible_link("v1"),
                    eligible_link("v2", provider="naver"),
                    eligible_link("v3", classification="new_official"),
                    eligible_link(""),
                    eligible_link(" v4 "),
                ],
            },
        ]
    )
    path = write_report(tmp_path / "audit.json", document)
    original = path.read_bytes()
    assert load_reddit_youtube_ids(path) == ["v1", "v4"]
    assert path.read_bytes() == original


def test_hydration_batches_fifty_stores_metadata_and_resumes(connection):
    ids = [f"v{index}" for index in range(51)]
    client = Client([[video(video_id) for video_id in ids[:50]], [video(ids[50])]])
    counts = hydrate_youtube_ids(
        connection,
        client,
        ids,
        limit=None,
        retry_unavailable=False,
        timestamp="2026-09-03T12:00:00Z",
    )
    assert [len(batch) for batch in client.calls] == [50, 1]
    assert (counts.considered, counts.queried, counts.batches) == (51, 51, 2)
    assert (counts.added, counts.updated, counts.unavailable) == (51, 0, 0)
    stored = connection.execute(
        "SELECT * FROM youtube_videos WHERE video_id = 'v0'"
    ).fetchone()
    assert stored["channel_title"] == "Uploader"
    assert stored["description"] == "Description"
    assert (
        connection.execute(
            "SELECT COUNT(*) FROM reddit_youtube_lookup_state "
            "WHERE lookup_status = 'available'"
        ).fetchone()[0]
        == 51
    )
    assert (
        connection.execute("SELECT COUNT(*) FROM reference_candidates").fetchone()[0]
        == 0
    )

    rerun_client = Client([])
    rerun = hydrate_youtube_ids(
        connection,
        rerun_client,
        ids,
        limit=None,
        retry_unavailable=False,
        timestamp="2026-09-04T12:00:00Z",
    )
    assert rerun_client.calls == []
    assert (rerun.considered, rerun.queried, rerun.skipped) == (0, 0, 51)
    assert not rerun.more_remaining


def test_unavailable_ids_are_only_retried_explicitly(connection):
    first = Client([[video("available")]])
    counts = hydrate_youtube_ids(
        connection,
        first,
        ["available", "missing"],
        limit=None,
        retry_unavailable=False,
        timestamp="2026-09-03T12:00:00Z",
    )
    assert counts.unavailable == 1
    assert (
        connection.execute(
            "SELECT lookup_status FROM reddit_youtube_lookup_state "
            "WHERE video_id='missing'"
        ).fetchone()[0]
        == "unavailable"
    )

    skipped_client = Client([])
    skipped = hydrate_youtube_ids(
        connection,
        skipped_client,
        ["available", "missing"],
        limit=None,
        retry_unavailable=False,
        timestamp="2026-09-04T12:00:00Z",
    )
    assert skipped_client.calls == []
    assert skipped.skipped == 2

    retry_client = Client([[video("missing", channel_title="Recovered")]])
    retried = hydrate_youtube_ids(
        connection,
        retry_client,
        ["available", "missing"],
        limit=None,
        retry_unavailable=True,
        timestamp="2026-09-05T12:00:00Z",
    )
    assert retry_client.calls == [["missing"]]
    assert (retried.considered, retried.added, retried.skipped) == (1, 1, 1)
    assert (
        connection.execute(
            "SELECT channel_title FROM youtube_videos WHERE video_id='missing'"
        ).fetchone()[0]
        == "Recovered"
    )


def test_limit_and_api_limit_preserve_completed_batches(connection):
    ids = [f"v{index}" for index in range(120)]
    first = hydrate_youtube_ids(
        connection,
        Client([[video(video_id) for video_id in ids[:50]]]),
        ids,
        limit=50,
        retry_unavailable=False,
        timestamp="2026-09-03T12:00:00Z",
    )
    assert first.considered == 50
    assert first.more_remaining

    api_limited = Client(
        [[video(video_id) for video_id in ids[50:100]], APICallLimit("limit")]
    )
    second = hydrate_youtube_ids(
        connection,
        api_limited,
        ids,
        limit=None,
        retry_unavailable=False,
        timestamp="2026-09-04T12:00:00Z",
    )
    assert second.skipped == 50
    assert second.queried == 50
    assert second.batches == 1
    assert second.more_remaining
    assert (
        connection.execute(
            "SELECT COUNT(*) FROM reddit_youtube_lookup_state"
        ).fetchone()[0]
        == 100
    )

    recovery = Client([[video(video_id) for video_id in ids[100:]]])
    final = hydrate_youtube_ids(
        connection,
        recovery,
        ids,
        limit=None,
        retry_unavailable=False,
        timestamp="2026-09-05T12:00:00Z",
    )
    assert recovery.calls == [ids[100:]]
    assert not final.more_remaining


def test_existing_video_is_updated_not_added(connection):
    upsert_video(connection, video("v1", title="Old"), "2026-09-01T12:00:00Z")
    connection.commit()
    client = Client([[video("v1", title="New", channel_title="New channel")]])
    counts = hydrate_youtube_ids(
        connection,
        client,
        ["v1"],
        limit=None,
        retry_unavailable=False,
        timestamp="2026-09-03T12:00:00Z",
    )
    assert (counts.added, counts.updated) == (0, 1)
    row = connection.execute(
        "SELECT title, channel_title FROM youtube_videos WHERE video_id='v1'"
    ).fetchone()
    assert tuple(row) == ("New", "New channel")


class Response:
    status_code = 200
    headers = {}

    def __init__(self, payload):
        self.payload = payload

    def json(self):
        return deepcopy(self.payload)


class Session:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return Response(self.payload)


def test_hydrate_cli_uses_input_override_and_prints_counts(
    config, connection, tmp_path
):
    path = write_report(
        tmp_path / "custom-audit.json",
        report_document(
            episodes=[{"has_local_win": True, "links": [eligible_link("v1")]}]
        ),
    )
    session = Session(
        {
            "items": [
                {
                    "id": "v1",
                    "snippet": {
                        "channelId": "UC1",
                        "channelTitle": "Uploader",
                        "title": "Winner",
                        "description": "",
                        "publishedAt": "2026-01-02T00:00:00Z",
                        "liveBroadcastContent": "none",
                    },
                    "contentDetails": {"duration": "PT3M"},
                    "status": {"privacyStatus": "public", "embeddable": True},
                }
            ]
        }
    )
    output = StringIO()
    result = main(
        ["reddit", "hydrate-youtube", "--input", str(path)],
        environ={
            "KPOPWINS_OPERATOR_HOME": str(config.home),
            "YOUTUBE_API_KEY": "test-key",
            "YOUTUBE_API_BASE_URL": "https://youtube.example/v3",
        },
        stdout=output,
        session=session,
        now="2026-09-03T12:00:00Z",
    )
    assert result == 0
    assert len(session.calls) == 1
    assert "considered=1 queried=1 batches=1 added=1" in output.getvalue()
    assert "more-remaining=no" in output.getvalue()
