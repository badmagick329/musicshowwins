from __future__ import annotations

from datetime import UTC, date, datetime
from io import StringIO

from kpopwins_operator.cli import main
from kpopwins_operator.database import due_searches, insert_candidate
from kpopwins_operator.scheduling import no_match_retry_at


def test_retry_delays_and_deterministic_staggering():
    confirmed_at = datetime(2026, 1, 1, tzinfo=UTC)
    expected_delays = (90, 180, 365, 730, 730)

    results = [
        no_match_retry_at(
            "music-bank",
            date(2025, 1, 3),
            "youtube",
            attempt,
            confirmed_at,
        )
        for attempt in range(1, 6)
    ]

    for result, base_delay in zip(results, expected_delays, strict=True):
        actual_days = (result - confirmed_at).days
        assert base_delay <= actual_days <= base_delay + 29
    assert results == [
        no_match_retry_at(
            "music-bank",
            date(2025, 1, 3),
            "youtube",
            attempt,
            confirmed_at,
        )
        for attempt in range(1, 6)
    ]


def test_due_queue_filters_orders_and_does_not_update(wins):
    states = [
        ("show-1", "2026-01-02", "pending", "2027-01-01T00:00:00Z"),
        ("show-0", "2026-01-03", "matched", None),
        ("show-1", "2026-01-04", "disabled", None),
        ("show-0", "2026-01-05", "error", None),
        ("show-1", "2026-01-06", "no_match", "2026-08-01T00:00:00Z"),
    ]
    for attempt, (show, win_date, status, next_attempt) in enumerate(states, start=1):
        wins.execute(
            """
            INSERT INTO search_state (
                show_slug, win_date, provider, status, attempt_count,
                last_attempt_at, next_attempt_at, last_error, updated_at
            ) VALUES (?, ?, 'youtube', ?, ?, NULL, ?, '', ?)
            """,
            (
                show,
                win_date,
                status,
                attempt,
                next_attempt,
                "2026-08-01T00:00:00Z",
            ),
        )
    wins.commit()
    before = [tuple(row) for row in wins.execute("SELECT * FROM search_state")]

    rows = due_searches(
        wins,
        "youtube",
        due_at="2026-08-31T00:00:00Z",
        limit=100,
    )

    assert [(row["show_slug"], row["win_date"]) for row in rows] == [
        ("show-0", "2026-01-01"),
        ("show-1", "2026-01-06"),
    ]
    assert [row["search_status"] for row in rows] == ["pending", "no_match"]
    assert [tuple(row) for row in wins.execute("SELECT * FROM search_state")] == before


def test_due_cli_limit_and_status_counts(config, wins):
    wins.execute(
        """
        INSERT INTO search_state (
            show_slug, win_date, provider, status, attempt_count,
            next_attempt_at, last_error, updated_at
        ) VALUES (
            'show-0', '2026-01-01', 'youtube', 'no_match', 1,
            '2026-08-01T00:00:00Z', '', '2026-08-01T00:00:00Z'
        )
        """
    )
    insert_candidate(
        wins,
        {
            "show_slug": "show-0",
            "win_date": "2026-01-01",
            "reference_type": "article",
            "provider": "publisher",
            "url": "https://example.com/reference",
            "review_status": "approved",
        },
    )
    wins.commit()
    environment = {"KPOPWINS_OPERATOR_HOME": str(config.home)}

    status_output = StringIO()
    due_output = StringIO()
    assert (
        main(
            ["status"],
            environ=environment,
            stdout=status_output,
            now="2026-08-31T00:00:00Z",
        )
        == 0
    )
    assert (
        main(
            ["due", "--provider", "YouTube", "--limit", "1"],
            environ=environment,
            stdout=due_output,
            now="2026-08-31T00:00:00Z",
        )
        == 0
    )

    assert "wins: current=6 non-current=1" in status_output.getvalue()
    assert "search youtube/no_match: 1" in status_output.getvalue()
    assert "candidates: pending=0 approved=1 rejected=0" in status_output.getvalue()
    assert "due searches: 6" in status_output.getvalue()
    assert len(due_output.getvalue().splitlines()) == 2
