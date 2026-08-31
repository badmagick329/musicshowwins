from __future__ import annotations

from copy import deepcopy
from io import StringIO

import pytest
import requests

from kpopwins_operator.catalogue import CatalogueError, refresh_catalogue
from kpopwins_operator.cli import main


def api_win(
    identifier: int,
    win_date: str,
    *,
    show="music-bank",
    artist="Alpha",
    song="First",
):
    return {
        "id": identifier,
        "date": win_date,
        "show": {"id": 5, "slug": show, "name": "Music Bank", "active": True},
        "song": {
            "id": 9,
            "title": song,
            "artist": {"id": 3, "name": artist},
            "total_wins": 1,
            "latest_win_date": win_date,
            "winning_shows": 1,
        },
        "references": [],
    }


class FakeResponse:
    def __init__(self, payload, *, status=200):
        self.payload = payload
        self.status = status

    def raise_for_status(self):
        if self.status >= 400:
            raise requests.HTTPError(f"HTTP {self.status}")

    def json(self):
        if isinstance(self.payload, Exception):
            raise self.payload
        return deepcopy(self.payload)


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.urls = []

    def get(self, url, *, timeout):
        self.urls.append(url)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        assert timeout == 30
        return response


def page(results, next_url=None, *, count=None):
    return FakeResponse(
        {
            "count": len(results) if count is None else count,
            "next": next_url,
            "previous": None,
            "results": results,
        }
    )


def test_multi_page_refresh_and_catalogue_upserts(connection):
    session = FakeSession(
        [
            page(
                [api_win(1, "2026-01-01")],
                "?page=2&ordering=-date",
                count=2,
            ),
            page(
                [api_win(2, "2026-01-02", artist="Beta", song="Second")],
                count=2,
            ),
        ]
    )

    first = refresh_catalogue(
        connection,
        "https://api.example.test/api/v1",
        session=session,
        seen_at="2026-08-31T12:00:00Z",
    )

    assert first.fetched == first.added == 2
    assert session.urls == [
        "https://api.example.test/api/v1/wins",
        "https://api.example.test/api/v1/wins?page=2&ordering=-date",
    ]

    changed = FakeSession(
        [
            page(
                [
                    api_win(10, "2026-01-01", artist="Updated"),
                    api_win(3, "2026-01-03", artist="Gamma", song="Third"),
                ]
            )
        ]
    )
    second = refresh_catalogue(
        connection,
        "https://api.example.test/api/v1",
        session=changed,
        seen_at="2026-09-01T12:00:00Z",
    )

    assert second.fetched == 2
    assert second.added == 1
    assert second.updated == 1
    assert second.unchanged == 0
    assert second.no_longer_current == 1
    rows = list(connection.execute("SELECT * FROM wins ORDER BY win_date"))
    assert [row["is_current"] for row in rows] == [1, 0, 1]
    assert rows[0]["api_win_id"] == 10
    assert rows[0]["artist_name"] == "Updated"

    identical = refresh_catalogue(
        connection,
        "https://api.example.test/api/v1",
        session=FakeSession(
            [
                page(
                    [
                        api_win(10, "2026-01-01", artist="Updated"),
                        api_win(3, "2026-01-03", artist="Gamma", song="Third"),
                    ]
                )
            ]
        ),
    )
    assert identical.added == identical.updated == 0
    assert identical.unchanged == 2


@pytest.mark.parametrize(
    "failure_session",
    [
        FakeSession([requests.ConnectionError("offline")]),
        FakeSession([page([], "https://api.example.test/api/v1/wins", count=1)]),
        FakeSession([page([{"id": 2}], count=1)]),
        FakeSession([page([], "https://evil.example/wins", count=1)]),
        FakeSession([FakeResponse(ValueError("bad json"))]),
    ],
    ids=["http", "pagination-loop", "invalid-record", "foreign-origin", "json"],
)
def test_failed_refresh_rolls_back_complete_catalogue(connection, failure_session):
    refresh_catalogue(
        connection,
        "https://api.example.test/api/v1",
        session=FakeSession([page([api_win(1, "2026-01-01")])]),
        seen_at="2026-08-31T12:00:00Z",
    )
    before = [tuple(row) for row in connection.execute("SELECT * FROM wins")]

    with pytest.raises(CatalogueError):
        refresh_catalogue(
            connection,
            "https://api.example.test/api/v1",
            session=failure_session,
        )

    after = [tuple(row) for row in connection.execute("SELECT * FROM wins")]
    assert after == before


def test_rejects_pagination_outside_configured_origin(connection):
    session = FakeSession(
        [page([], "https://other.example/api/v1/wins?page=2", count=1)]
    )

    with pytest.raises(CatalogueError, match="configured origin"):
        refresh_catalogue(
            connection,
            "https://api.example.test/api/v1",
            session=session,
        )


def test_refresh_cli_reports_counts_and_returns_nonzero_on_failure(config, connection):
    environment = {
        "KPOPWINS_OPERATOR_HOME": str(config.home),
        "KPOPWINS_API_BASE_URL": config.api_base_url,
    }
    output = StringIO()
    errors = StringIO()

    assert (
        main(
            ["refresh-wins"],
            environ=environment,
            stdout=output,
            stderr=errors,
            session=FakeSession([page([api_win(1, "2026-01-01")])]),
            now="2026-08-31T12:00:00Z",
        )
        == 0
    )
    assert (
        output.getvalue()
        == "fetched=1 added=1 updated=0 unchanged=0 no-longer-current=0\n"
    )

    before = [tuple(row) for row in connection.execute("SELECT * FROM wins")]
    assert (
        main(
            ["refresh-wins"],
            environ=environment,
            stdout=output,
            stderr=errors,
            session=FakeSession([requests.ConnectionError("offline")]),
        )
        == 1
    )
    assert "complete win catalogue" in errors.getvalue()
    assert [tuple(row) for row in connection.execute("SELECT * FROM wins")] == before
