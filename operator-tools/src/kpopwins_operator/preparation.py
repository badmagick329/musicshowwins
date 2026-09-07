from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import asdict
from typing import TextIO

import requests

from .catalogue import refresh_catalogue
from .config import Config
from .ingestion import ingest_channels
from .manifest import write_atomic
from .matching import match_videos
from .reddit import RedditClient, run_reddit_audit
from .reddit_hydration import hydrate_youtube_ids, load_reddit_youtube_ids
from .reddit_import import import_official_links, load_official_audit_links
from .registry import load_registry
from .review_batches import _snapshot
from .youtube import YouTubeClient


def prepare_candidates(
    connection: sqlite3.Connection,
    config: Config,
    *,
    include_reddit: bool,
    max_pages: int,
    reddit_max_pages: int,
    min_score: int,
    timestamp: str,
    stdout: TextIO,
    session: requests.Session | None = None,
    sleep=time.sleep,
) -> dict:
    """Sequence bounded discovery runs while keeping review and publication explicit."""
    # Check prerequisites before refreshing the catalogue or consuming API calls.
    client = YouTubeClient(config, connection, session=session, sleep=sleep)
    registry = load_registry(config.channel_registry_path)
    if not connection.execute(
        "SELECT 1 FROM youtube_channels WHERE is_active=1 LIMIT 1"
    ).fetchone():
        raise ValueError(
            "No verified channels; run youtube verify-channels --apply first."
        )
    if include_reddit:
        RedditClient(config, session=session, sleep=sleep)

    report_path = config.reports_dir / "prepare.json"
    previous = (
        json.loads(report_path.read_text(encoding="utf-8"))
        if report_path.exists()
        else {}
    )
    if not isinstance(previous, dict):
        raise ValueError("Preparation report must be a JSON object.")
    refresh_indexes = (
        previous.get("reddit_refresh_pending", False)
        if previous.get("reddit_pending", False)
        else True
    )
    report = {
        "version": 1,
        "started_at": timestamp,
        "complete": False,
        "reddit_pending": include_reddit or previous.get("reddit_pending", False),
        "reddit_refresh_pending": refresh_indexes,
        "stages": {},
        "stage": "refresh-wins",
    }

    def stage(name: str) -> None:
        report["stage"] = name
        write_atomic(report_path, json.dumps(report, indent=2) + "\n")
        print(f"Preparing: {name}", file=stdout, flush=True)

    def review_queue_counts() -> dict[str, int]:
        pending_rows = list(
            connection.execute(
                """SELECT candidate.id, deferred.fingerprint
                   FROM reference_candidates AS candidate
                   JOIN wins USING(show_slug, win_date)
                   LEFT JOIN candidate_deferrals AS deferred
                     ON deferred.candidate_id = candidate.id
                   WHERE candidate.review_status='pending'
                     AND candidate.withdrawn=0 AND wins.is_current=1
                     AND candidate.provider='youtube'"""
            )
        )
        ready = 0
        deferred = 0
        for row in pending_rows:
            current = _snapshot(connection, config, row["id"])
            if row["fingerprint"] == current["fingerprint"]:
                deferred += 1
            else:
                ready += 1
        return {"pending": len(pending_rows), "ready": ready, "deferred": deferred}

    existing_pending_ids = {
        row["id"]
        for row in connection.execute(
            """SELECT candidate.id
               FROM reference_candidates AS candidate
               JOIN wins USING(show_slug, win_date)
               WHERE candidate.review_status='pending'
                 AND candidate.withdrawn=0 AND wins.is_current=1
                 AND candidate.provider='youtube'"""
        )
    }

    try:
        stage("refresh-wins")
        report["stages"]["catalogue"] = asdict(
            refresh_catalogue(
                connection,
                config.api_base_url,
                session=session,
                seen_at=timestamp,
            )
        )
        stage("youtube-ingest")
        ingestion = ingest_channels(
            connection,
            client,
            handle=None,
            max_pages=max_pages,
            restart=False,
            timestamp=timestamp,
        )
        report["stages"]["youtube"] = asdict(ingestion)
        stage("youtube-match")
        matching = match_videos(
            connection,
            registry,
            show=None,
            min_score=min_score,
            limit=None,
            dry_run=False,
            timestamp=timestamp,
        )
        report["stages"]["matching"] = asdict(matching)
        report["new_candidates"] = {
            "youtube_match": matching.created,
            "reddit_import": 0,
            "total": matching.created,
        }

        reddit_complete = not include_reddit
        if include_reddit:
            stage("reddit-audit")
            audit = run_reddit_audit(
                connection,
                config,
                show=None,
                max_pages=reddit_max_pages,
                refresh_indexes=refresh_indexes,
                output_path=None,
                stdout=stdout,
                session=session,
                sleep=sleep,
                now=timestamp,
            )
            report["reddit_refresh_pending"] = False
            report["stages"]["reddit_audit"] = {
                "complete": audit.collection_complete,
                "totals": audit.totals,
            }
            if audit.collection_complete:
                stage("reddit-hydrate")
                hydration = hydrate_youtube_ids(
                    connection,
                    client,
                    load_reddit_youtube_ids(audit.report_path),
                    limit=None,
                    retry_unavailable=False,
                    timestamp=timestamp,
                )
                report["stages"]["reddit_hydration"] = asdict(hydration)
                if not hydration.more_remaining:
                    stage("reddit-reclassify")
                    # Collection is complete: reclassification uses cached pages only.
                    refreshed = run_reddit_audit(
                        connection,
                        config,
                        show=None,
                        max_pages=0,
                        refresh_indexes=False,
                        output_path=None,
                        stdout=stdout,
                        session=session,
                        sleep=sleep,
                        now=timestamp,
                    )
                    if refreshed.collection_complete:
                        stage("reddit-import")
                        reddit_import = import_official_links(
                            connection,
                            load_official_audit_links(refreshed.report_path),
                            limit=None,
                            dry_run=False,
                            timestamp=timestamp,
                        )
                        report["stages"]["reddit_import"] = asdict(reddit_import)
                        report["new_candidates"]["reddit_import"] = (
                            reddit_import.created
                        )
                        report["new_candidates"]["total"] += reddit_import.created
                        report["withheld_official_links"] = max(
                            0,
                            report["stages"]["reddit_audit"]["totals"].get(
                                "new_official", 0
                            )
                            - reddit_import.eligible,
                        )
                        reddit_complete = True
            report["reddit_pending"] = not reddit_complete

        report["complete"] = not ingestion.more_remaining and reddit_complete
        report["stage"] = "complete" if report["complete"] else "paused"
        report["youtube_api_calls"] = client.calls_used
        report["review_queue"] = review_queue_counts()
        report["pending_candidates"] = report["review_queue"]["pending"]
        report["existing_pending_candidates"] = sum(
            1
            for candidate_id in existing_pending_ids
            if connection.execute(
                """SELECT 1 FROM reference_candidates AS candidate
                   JOIN wins USING(show_slug, win_date)
                   WHERE candidate.id=? AND candidate.review_status='pending'
                     AND candidate.withdrawn=0 AND wins.is_current=1
                     AND candidate.provider='youtube'""",
                (candidate_id,),
            ).fetchone()
        )
        report.setdefault("withheld_official_links", 0)
    except Exception:
        report["failed_stage"] = report["stage"]
        report["stage"] = "failed"
        raise
    finally:
        write_atomic(report_path, json.dumps(report, indent=2) + "\n")

    new_candidates = report["new_candidates"]["total"]
    queue = report["review_queue"]
    print(f"New candidates created: {new_candidates}", file=stdout)
    print(
        f"Existing pending candidates: {report['existing_pending_candidates']}",
        file=stdout,
    )
    print(
        f"Review queue: ready={queue['ready']} deferred={queue['deferred']}",
        file=stdout,
    )
    print(f"Report: {report_path}", file=stdout)
    print(
        f"Official links withheld (no local win): {report['withheld_official_links']}",
        file=stdout,
    )
    if report["complete"]:
        if new_candidates or queue["ready"]:
            print("Discovery complete. Next: review batch", file=stdout)
        else:
            print(
                "Discovery complete. No candidates are ready for review. "
                "Next: export-approved",
                file=stdout,
            )
    else:
        suffix = " --reddit" if include_reddit else ""
        suffix += f" --max-pages {max_pages} --min-score {min_score}"
        if include_reddit:
            suffix += f" --reddit-max-pages {reddit_max_pages}"
        print(
            f"Discovery paused at a page/request limit. Resume: prepare{suffix}",
            file=stdout,
        )
        if new_candidates or queue["ready"]:
            print("Candidates are ready for review with: review batch", file=stdout)
    return report
