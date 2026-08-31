from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime

import pytest

from kpopwins_operator.config import Config
from kpopwins_operator.youtube import (
    APICallLimit,
    APIKeyMissing,
    QuotaExceeded,
    YouTubeClient,
    YouTubeError,
)


class Response:
    def __init__(self, payload, status=200, headers=None):
        self.payload = payload
        self.status_code = status
        self.headers = headers or {}

    def json(self):
        if isinstance(self.payload, Exception):
            raise self.payload
        return deepcopy(self.payload)


class Session:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.responses.pop(0)


def youtube_config(config, **changes):
    values = {
        "home": config.home,
        "api_base_url": config.api_base_url,
        "youtube_api_key": "top-secret",
        "youtube_api_base_url": "https://youtube.example/v3",
        "youtube_max_api_calls_per_run": 500,
    }
    values.update(changes)
    return Config(**values)


def test_client_requires_key_and_sends_bounded_channels_request(connection, config):
    with pytest.raises(APIKeyMissing):
        YouTubeClient(config, connection)
    session = Session(
        [
            Response(
                {
                    "items": [
                        {
                            "id": "UC1",
                            "snippet": {"title": "KBS Kpop"},
                            "contentDetails": {"relatedPlaylists": {"uploads": "UU1"}},
                        }
                    ]
                }
            )
        ]
    )
    client = YouTubeClient(
        youtube_config(config),
        connection,
        session=session,
        clock=lambda: datetime(2026, 1, 1, 7, tzinfo=UTC),
    )

    resolved = client.resolve_handle("@KBSKpop")

    assert resolved.channel_id == "UC1"
    url, options = session.calls[0]
    assert url == "https://youtube.example/v3/channels"
    assert options["params"]["forHandle"] == "@KBSKpop"
    assert options["params"]["key"] == "top-secret"
    assert options["timeout"] == (5, 30)
    assert options["headers"]["User-Agent"] == (
        "KpopWinsOperator/0.1 (+https://github.com/badmagick329/musicshowwins)"
    )
    usage = connection.execute("SELECT * FROM youtube_api_usage").fetchone()
    assert (usage["pacific_date"], usage["api_method"], usage["call_count"]) == (
        "2025-12-31",
        "channels.list",
        1,
    )


def test_transient_retry_quota_stop_limit_and_key_safe_errors(connection, config):
    sleeps = []
    session = Session(
        [
            Response({}, 503, {"Retry-After": "2"}),
            Response({"items": []}),
        ]
    )
    client = YouTubeClient(
        youtube_config(config), connection, session=session, sleep=sleeps.append
    )
    with pytest.raises(YouTubeError, match="did not resolve") as error:
        client.resolve_handle("@missing")
    assert sleeps == [2]
    assert client.calls_used == 2
    assert "top-secret" not in str(error.value)

    quota = YouTubeClient(
        youtube_config(config),
        connection,
        session=Session(
            [Response({"error": {"errors": [{"reason": "quotaExceeded"}]}}, 403)]
        ),
    )
    with pytest.raises(QuotaExceeded):
        quota.resolve_handle("@KBSKpop")
    assert quota.calls_used == 1

    limited = YouTubeClient(
        youtube_config(config, youtube_max_api_calls_per_run=1),
        connection,
        session=Session([Response({"items": []})]),
    )
    with pytest.raises(YouTubeError):
        limited.resolve_handle("@one")
    with pytest.raises(APICallLimit):
        limited.resolve_handle("@two")


def test_playlist_and_video_requests_are_paginated_and_shape_checked(
    connection, config
):
    session = Session(
        [
            Response(
                {
                    "nextPageToken": "NEXT",
                    "items": [
                        {
                            "contentDetails": {"videoId": "v1"},
                            "snippet": {"publishedAt": "2026-01-01T00:00:00Z"},
                        }
                    ],
                }
            ),
            Response(
                {
                    "items": [
                        {
                            "id": "v1",
                            "snippet": {
                                "channelId": "UC1",
                                "title": "Winner",
                                "description": "Description",
                                "publishedAt": "2026-01-01T00:00:00Z",
                                "liveBroadcastContent": "none",
                            },
                            "contentDetails": {"duration": "PT3M"},
                            "status": {"privacyStatus": "public", "embeddable": True},
                        }
                    ]
                }
            ),
        ]
    )
    client = YouTubeClient(youtube_config(config), connection, session=session)
    page = client.playlist_page("UU1", "TOKEN")
    videos = client.videos(list(page.video_ids))

    assert page.next_page_token == "NEXT"
    assert videos[0].video_id == "v1"
    assert session.calls[0][1]["params"]["maxResults"] == 50
    assert session.calls[0][1]["params"]["pageToken"] == "TOKEN"
    assert session.calls[1][1]["params"]["id"] == "v1"
    with pytest.raises(ValueError, match="at most 50"):
        client.videos([str(index) for index in range(51)])


def test_malformed_video_response_is_rejected(connection, config):
    client = YouTubeClient(
        youtube_config(config),
        connection,
        session=Session([Response({"items": {"not": "a list"}})]),
    )
    with pytest.raises(YouTubeError, match="incomplete"):
        client.videos(["v1"])
