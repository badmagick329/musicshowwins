import json
from io import StringIO

import pytest

from kpopwins_operator.candidate_review import review_candidates, show_candidate
from kpopwins_operator.catalogue import refresh_catalogue
from kpopwins_operator.cli import main
from kpopwins_operator.database import insert_candidate
from kpopwins_operator.manifest import approved_document
from kpopwins_operator.matching import match_videos

from .test_catalogue import FakeSession, api_win, page
from .test_matching_review import REGISTRY, add_match_data


def match(connection):
    return match_videos(
        connection,
        REGISTRY,
        show=None,
        min_score=75,
        limit=None,
        dry_run=False,
        timestamp="2026-09-06T00:00:00Z",
    )


def review(connection, ids, decision="approved", **kwargs):
    return review_candidates(
        connection,
        ids,
        decision=decision,
        reviewer="agent-1",
        reason="Checked exact episode and winner",
        timestamp="2026-09-06T00:00:00Z",
        **kwargs,
    )


def test_rematching_preserves_reddit_evidence_and_review_history(connection):
    add_match_data(connection)
    match(connection)
    candidate_id = connection.execute("SELECT id FROM reference_candidates").fetchone()[
        0
    ]
    evidence = {
        "reddit_audit": {"episode_url": "https://reddit.com/r/kpop/wiki/episode"}
    }
    connection.execute(
        "UPDATE reference_candidates SET metadata=?", (json.dumps(evidence),)
    )
    connection.commit()
    review(connection, [candidate_id])
    match(connection)
    row = connection.execute("SELECT * FROM reference_candidates").fetchone()
    assert json.loads(row["metadata"])["reddit_audit"] == evidence["reddit_audit"]
    assert "youtube_match" in json.loads(row["metadata"])
    assert row["review_status"] == "approved"
    details = StringIO()
    show_candidate(connection, details, candidate_id)
    assert "agent-1" in details.getvalue()
    assert "Checked exact episode" in details.getvalue()


def test_review_batch_cannot_reverse_decisions_and_rolls_back(connection):
    add_match_data(connection)
    match(connection)
    first = connection.execute("SELECT id FROM reference_candidates").fetchone()[0]
    second = insert_candidate(
        connection,
        {
            "show_slug": "music-bank",
            "win_date": "2026-01-02",
            "reference_type": "video",
            "provider": "youtube",
            "url": "https://youtube.com/watch?v=v2",
            "external_id": "v2",
        },
    )
    connection.commit()
    review(connection, [first])
    with pytest.raises(ValueError, match="already reviewed"):
        review(connection, [second, first], "rejected")
    assert [
        row[0]
        for row in connection.execute(
            "SELECT review_status FROM reference_candidates ORDER BY id"
        )
    ] == ["approved", "pending"]
    assert (
        connection.execute("SELECT COUNT(*) FROM candidate_review_events").fetchone()[0]
        == 1
    )
    review(connection, [first], "rejected", revise=True)
    assert (
        connection.execute("SELECT COUNT(*) FROM candidate_review_events").fetchone()[0]
        == 2
    )


def test_review_rejects_blank_reason_without_mutating_candidate(connection):
    add_match_data(connection)
    match(connection)
    candidate_id = connection.execute("SELECT id FROM reference_candidates").fetchone()[
        0
    ]
    with pytest.raises(ValueError, match="must not be blank"):
        review_candidates(
            connection,
            [candidate_id],
            decision="approved",
            reviewer="agent-1",
            reason="  ",
            timestamp="now",
        )
    assert (
        connection.execute("SELECT review_status FROM reference_candidates").fetchone()[
            0
        ]
        == "pending"
    )


@pytest.mark.parametrize(
    "changes,invalidated",
    [
        ({"artist": "Beta"}, True),
        ({"song": "Second"}, True),
        ({}, False),
    ],
)
def test_catalogue_correction_requires_another_review(connection, changes, invalidated):
    add_match_data(connection)
    match(connection)
    candidate_id = connection.execute("SELECT id FROM reference_candidates").fetchone()[
        0
    ]
    review(connection, [candidate_id])
    refresh_catalogue(
        connection,
        "https://api.example.test/api/v1",
        session=FakeSession([page([api_win(99, "2026-01-02", **changes)])]),
    )
    row = connection.execute(
        "SELECT review_status FROM reference_candidates"
    ).fetchone()
    assert row[0] == ("pending" if invalidated else "approved")
    assert len(approved_document(connection)["references"]) == (0 if invalidated else 1)
    assert connection.execute("SELECT status FROM search_state").fetchone()[0] == (
        "pending" if invalidated else "matched"
    )


def test_withdrawal_survives_matching_and_exports_even_for_noncurrent_win(
    config, connection
):
    add_match_data(connection)
    match(connection)
    candidate_id = connection.execute("SELECT id FROM reference_candidates").fetchone()[
        0
    ]
    review(connection, [candidate_id])
    assert (
        main(
            [
                "candidates",
                "withdraw",
                str(candidate_id),
                "--reviewer",
                "agent-1",
                "--reason",
                "Wrong episode confirmed",
            ],
            environ={"KPOPWINS_OPERATOR_HOME": str(config.home)},
            stdout=StringIO(),
        )
        == 0
    )
    match(connection)
    connection.execute("UPDATE wins SET is_current=0")
    connection.commit()
    assert approved_document(connection)["references"][0]["status"] == "withdrawn"
    with pytest.raises(ValueError, match="already reviewed"):
        review(connection, [candidate_id])
    connection.execute("UPDATE wins SET is_current=1")
    connection.commit()
    review(connection, [candidate_id], revise=True)
    assert approved_document(connection)["references"][0]["status"] == "active"
