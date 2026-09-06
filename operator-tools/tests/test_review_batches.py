import json
from io import StringIO

import pytest

from kpopwins_operator import review_batches
from kpopwins_operator.cli import main
from kpopwins_operator.database import insert_candidate
from kpopwins_operator.review_batches import (
    apply_batch,
    batch_directory,
    cancel_batch,
    create_batch,
)

from .test_matching_review import add_match_data
from .test_review_safeguards import match

NOW = "2026-09-06T12:00:00Z"


def batch(connection, config, **options):
    return create_batch(
        connection,
        config,
        **{
            "show": None,
            "source": None,
            "limit": 25,
            "include_deferred": False,
            "timestamp": NOW,
            **options,
        },
    )


def decision_file(config, packet, actions):
    path = batch_directory(config, packet["batch_id"]) / "decisions.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    document["reviewer"] = "review-agent"
    for entry, action in zip(document["decisions"], actions, strict=True):
        entry.update(
            decision=action,
            reason=f"Reason for {action}",
            evidence="Compared exact winner and episode against linked video.",
        )
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


def add_candidates(connection):
    add_match_data(connection)
    match(connection)
    for i in (2, 3):
        insert_candidate(
            connection,
            {
                "show_slug": "music-bank",
                "win_date": "2026-01-02",
                "reference_type": "video",
                "provider": "youtube",
                "external_id": f"v{i}",
                "url": f"https://www.youtube.com/watch?v=v{i}",
            },
        )
    connection.commit()


def test_batch_includes_local_evidence_and_resumes_without_overwriting_work(
    connection, config
):
    add_match_data(connection)
    match(connection)
    metadata = {
        "reddit_audit": {
            "episode_url": "https://www.reddit.com/r/kpop/wiki/music-shows/music-bank/20260102"
        }
    }
    connection.execute(
        "UPDATE reference_candidates SET metadata=?", (json.dumps(metadata),)
    )
    connection.commit()
    cache = config.reddit_dir / "pages/music-shows/music-bank/20260102.md"
    cache.parent.mkdir(parents=True)
    cache.write_text(
        "# WINNER\nAlpha - First [Encore](https://youtube.com/watch?v=v1)\n# Other\nNo",
        encoding="utf-8",
    )
    packet = batch(connection, config, source="reddit_audit")
    candidate = packet["candidates"][0]
    assert candidate["video"]["description"] == ""
    assert candidate["candidate"]["artist_name"] == "Alpha"
    assert candidate["official_channels"][0]["channel_id"] == "UC1"
    assert "Alpha - First" in candidate["reddit_winner_context"]
    assert "# Other" not in candidate["reddit_winner_context"]
    path = decision_file(config, packet, ["approve"])
    before = path.read_bytes()
    assert batch(connection, config, source="reddit_audit") == packet
    assert path.read_bytes() == before
    assert batch(connection, config) is None  # Reserved by the other scope.


def test_apply_is_atomic_dry_runnable_logged_and_idempotent(connection, config):
    add_candidates(connection)
    packet = batch(connection, config)
    path = decision_file(config, packet, ["approve", "reject", "defer"])
    result = apply_batch(connection, config, path, dry_run=True, timestamp=NOW)
    assert result["counts"] == {"approve": 1, "reject": 1, "defer": 1}
    assert (
        connection.execute("SELECT COUNT(*) FROM candidate_review_events").fetchone()[0]
        == 0
    )
    assert (
        connection.execute("SELECT status FROM review_batches").fetchone()[0] == "open"
    )
    assert not (path.parent / "applied.json").exists()
    result = apply_batch(connection, config, path, dry_run=False, timestamp=NOW)
    assert not result["already_applied"]
    assert [
        r[0]
        for r in connection.execute(
            "SELECT review_status FROM reference_candidates ORDER BY id"
        )
    ] == ["approved", "rejected", "pending"]
    assert (
        connection.execute("SELECT COUNT(*) FROM candidate_review_events").fetchone()[0]
        == 3
    )
    assert (
        connection.execute("SELECT status FROM search_state").fetchone()[0] == "matched"
    )
    assert (
        json.loads((path.parent / "applied.json").read_text())["reviewer"]
        == "review-agent"
    )
    assert apply_batch(connection, config, path, dry_run=False, timestamp=NOW)[
        "already_applied"
    ]
    assert (
        connection.execute("SELECT COUNT(*) FROM candidate_review_events").fetchone()[0]
        == 3
    )
    assert batch(connection, config) is None
    reconsidered = batch(connection, config, include_deferred=True)["candidates"]
    assert len(reconsidered) == 1
    assert reconsidered[0]["previous_reviews"][0]["decision"] == "deferred"


def test_failure_during_second_decision_rolls_back_the_first(
    connection, config, monkeypatch
):
    add_candidates(connection)
    packet = batch(connection, config)
    path = decision_file(config, packet, ["approve", "reject", "defer"])
    original = review_batches.review_candidates
    calls = 0

    def fail_second(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise ValueError("Injected write failure")
        return original(*args, **kwargs)

    monkeypatch.setattr(review_batches, "review_candidates", fail_second)
    with pytest.raises(ValueError, match="Injected"):
        apply_batch(connection, config, path, dry_run=False, timestamp=NOW)
    assert (
        connection.execute(
            "SELECT COUNT(*) FROM reference_candidates WHERE review_status='pending'"
        ).fetchone()[0]
        == 3
    )
    assert (
        connection.execute("SELECT COUNT(*) FROM candidate_review_events").fetchone()[0]
        == 0
    )
    assert connection.execute("SELECT COUNT(*) FROM search_state").fetchone()[0] == 0
    assert (
        connection.execute("SELECT status FROM review_batches").fetchone()[0] == "open"
    )


@pytest.mark.parametrize(
    "sql",
    [
        "UPDATE wins SET song_title='Changed'",
        "UPDATE youtube_videos SET description='Changed'",
        "UPDATE youtube_channels SET is_active=0",
        "UPDATE reference_candidates SET title='Changed'",
        "UPDATE reference_candidates SET review_status='rejected'",
    ],
)
def test_stale_evidence_prevents_all_decisions(connection, config, sql):
    add_match_data(connection)
    match(connection)
    packet = batch(connection, config)
    path = decision_file(config, packet, ["approve"])
    connection.execute(sql)
    connection.commit()
    with pytest.raises(ValueError, match="changed since export"):
        apply_batch(connection, config, path, dry_run=False, timestamp=NOW)
    assert (
        connection.execute("SELECT COUNT(*) FROM candidate_review_events").fetchone()[0]
        == 0
    )


def test_identical_rematch_is_not_stale_and_changed_evidence_requeues_deferred(
    connection, config
):
    add_match_data(connection)
    match(connection)
    packet = batch(connection, config)
    path = decision_file(config, packet, ["defer"])
    match(connection)
    apply_batch(connection, config, path, dry_run=False, timestamp=NOW)
    match(connection)
    assert batch(connection, config) is None
    connection.execute(
        "UPDATE youtube_videos SET description='Now includes the episode date'"
    )
    connection.commit()
    assert batch(connection, config)["batch_id"] != packet["batch_id"]


@pytest.mark.parametrize(
    "change", ["blank", "missing", "duplicate", "foreign", "bad-action", "extra-field"]
)
def test_invalid_decision_files_leave_state_untouched(connection, config, change):
    add_candidates(connection)
    packet = batch(connection, config)
    path = decision_file(config, packet, ["approve", "reject", "defer"])
    document = json.loads(path.read_text())
    if change == "blank":
        document["decisions"][0]["evidence"] = ""
    elif change == "missing":
        document["decisions"].pop()
    elif change == "duplicate":
        document["decisions"][1] = document["decisions"][0]
    elif change == "foreign":
        document["decisions"][0]["candidate_id"] = 999
    elif change == "bad-action":
        document["decisions"][0]["decision"] = "withdraw"
    else:
        document["decisions"][0]["unexpected"] = True
    path.write_text(json.dumps(document))
    with pytest.raises(ValueError):
        apply_batch(connection, config, path, dry_run=False, timestamp=NOW)
    assert (
        connection.execute("SELECT COUNT(*) FROM candidate_review_events").fetchone()[0]
        == 0
    )


def test_cancel_releases_candidates_and_blocks_old_decisions(connection, config):
    add_match_data(connection)
    match(connection)
    packet = batch(connection, config)
    path = decision_file(config, packet, ["approve"])
    cancel_batch(connection, packet["batch_id"])
    fresh = batch(connection, config)
    assert fresh["batch_id"] != packet["batch_id"]
    with pytest.raises(ValueError, match="cancelled"):
        apply_batch(connection, config, path, dry_run=False, timestamp=NOW)


def test_cli_batch_template_cannot_be_applied_unreviewed(connection, config):
    add_match_data(connection)
    match(connection)
    output, errors = StringIO(), StringIO()
    options = {
        "environ": {"KPOPWINS_OPERATOR_HOME": str(config.home)},
        "stdout": output,
        "stderr": errors,
    }
    assert main(["review", "batch"], **options) == 0
    identifier = connection.execute("SELECT batch_id FROM review_batches").fetchone()[0]
    path = batch_directory(config, identifier) / "decisions.json"
    assert main(["review", "apply", str(path)], **options) == 1
    assert "reviewer must not be blank" in errors.getvalue()
    assert "Agent evidence:" in output.getvalue()
