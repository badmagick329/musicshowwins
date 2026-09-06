import json
from io import StringIO
from types import SimpleNamespace

import pytest

from kpopwins_operator import preparation
from kpopwins_operator.ingestion import IngestionCounts
from kpopwins_operator.reddit_hydration import HydrationCounts
from kpopwins_operator.reddit_import import ImportCounts

from .test_catalogue import FakeSession, api_win, page
from .test_matching_review import add_match_data


@pytest.fixture
def setup(connection, config, monkeypatch):
    add_match_data(connection)
    client = SimpleNamespace(calls_used=2)
    monkeypatch.setattr(preparation, "YouTubeClient", lambda *a, **k: client)
    monkeypatch.setattr(preparation, "RedditClient", lambda *a, **k: None)
    monkeypatch.setattr(
        preparation, "ingest_channels", lambda *a, **k: IngestionCounts()
    )
    options = dict(
        include_reddit=False,
        max_pages=10,
        reddit_max_pages=100,
        min_score=75,
        timestamp="2026-09-06T12:00:00Z",
        stdout=StringIO(),
        session=FakeSession([page([api_win(1, "2026-01-02")])]),
    )
    return client, options


def test_prepare_matches_available_data_even_when_ingestion_pauses(
    connection, config, monkeypatch, setup
):
    _, options = setup
    monkeypatch.setattr(
        preparation,
        "ingest_channels",
        lambda *a, **k: IngestionCounts(more_remaining=True),
    )
    report = preparation.prepare_candidates(connection, config, **options)
    assert not report["complete"]
    assert report["pending_candidates"] == 1
    assert report["stage"] == "paused"
    assert "Resume: prepare" in options["stdout"].getvalue()
    assert (
        connection.execute("SELECT review_status FROM reference_candidates").fetchone()[
            0
        ]
        == "pending"
    )


def test_incomplete_reddit_collection_stops_before_hydration(
    connection, config, monkeypatch, setup
):
    _, options = setup
    options["include_reddit"] = True
    monkeypatch.setattr(
        preparation,
        "run_reddit_audit",
        lambda *a, **k: SimpleNamespace(collection_complete=False, totals={}),
    )

    def forbidden(*args, **kwargs):
        pytest.fail("Hydration must wait for a completed audit")

    monkeypatch.setattr(preparation, "hydrate_youtube_ids", forbidden)
    report = preparation.prepare_candidates(connection, config, **options)
    assert report["reddit_pending"]
    assert not report["complete"]


def test_reddit_resumes_and_shares_youtube_budget(
    connection, config, monkeypatch, setup
):
    client, options = setup
    options["include_reddit"] = True
    config.reports_dir.mkdir(parents=True)
    (config.reports_dir / "prepare.json").write_text(
        json.dumps({"reddit_pending": True})
    )
    calls = []

    def audit(*args, **kwargs):
        calls.append((kwargs["refresh_indexes"], kwargs["max_pages"]))
        return SimpleNamespace(
            collection_complete=True,
            totals={},
            report_path=config.default_reddit_audit_path,
        )

    monkeypatch.setattr(preparation, "run_reddit_audit", audit)
    monkeypatch.setattr(preparation, "load_reddit_youtube_ids", lambda p: ["v2"])

    def hydrate(conn, actual_client, ids, **kwargs):
        assert actual_client is client
        return HydrationCounts()

    monkeypatch.setattr(preparation, "hydrate_youtube_ids", hydrate)
    monkeypatch.setattr(preparation, "load_official_audit_links", lambda p: [])
    monkeypatch.setattr(
        preparation, "import_official_links", lambda *a, **k: ImportCounts()
    )
    report = preparation.prepare_candidates(connection, config, **options)
    assert report["complete"]
    assert not report["reddit_pending"]
    assert calls == [(False, 100), (False, 0)]
    assert "reddit_import" in report["stages"]


def test_hydration_budget_stop_does_not_import_incomplete_results(
    connection, config, monkeypatch, setup
):
    _, options = setup
    options["include_reddit"] = True
    monkeypatch.setattr(
        preparation,
        "run_reddit_audit",
        lambda *a, **k: SimpleNamespace(
            collection_complete=True,
            totals={},
            report_path=config.default_reddit_audit_path,
        ),
    )
    monkeypatch.setattr(preparation, "load_reddit_youtube_ids", lambda p: ["v2"])
    monkeypatch.setattr(
        preparation,
        "hydrate_youtube_ids",
        lambda *a, **k: HydrationCounts(more_remaining=True),
    )
    report = preparation.prepare_candidates(connection, config, **options)
    assert not report["complete"]
    assert "reddit_import" not in report["stages"]


def test_failure_records_stage_and_preserves_completed_work(
    connection, config, monkeypatch, setup
):
    _, options = setup

    def fail(*args, **kwargs):
        raise ValueError("Network failure")

    monkeypatch.setattr(preparation, "ingest_channels", fail)
    with pytest.raises(ValueError, match="Network"):
        preparation.prepare_candidates(connection, config, **options)
    report = json.loads((config.reports_dir / "prepare.json").read_text())
    assert report["failed_stage"] == "youtube-ingest"
    assert "catalogue" in report["stages"]


def test_failure_before_reddit_keeps_index_refresh_due(
    connection, config, monkeypatch, setup
):
    _, options = setup
    options["include_reddit"] = True

    def fail(*args, **kwargs):
        raise ValueError("Upload request failed")

    monkeypatch.setattr(preparation, "ingest_channels", fail)
    with pytest.raises(ValueError):
        preparation.prepare_candidates(connection, config, **options)
    saved = json.loads((config.reports_dir / "prepare.json").read_text())
    assert saved["reddit_refresh_pending"]
    monkeypatch.setattr(
        preparation, "ingest_channels", lambda *a, **k: IngestionCounts()
    )

    def audit(*args, **kwargs):
        assert kwargs["refresh_indexes"] is True
        return SimpleNamespace(collection_complete=False, totals={})

    monkeypatch.setattr(preparation, "run_reddit_audit", audit)
    options["session"] = FakeSession([page([api_win(1, "2026-01-02")])])
    resumed = preparation.prepare_candidates(connection, config, **options)
    assert resumed["reddit_pending"]
    assert not resumed["reddit_refresh_pending"]
