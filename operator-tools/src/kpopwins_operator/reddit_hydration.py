from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from .ingestion import upsert_video
from .reddit import REDDIT_ENTRY_POINT
from .youtube import APICallLimit, YouTubeClient

REPORT_VERSION = 1


class RedditHydrationError(ValueError):
    pass


@dataclass
class HydrationCounts:
    considered: int = 0
    queried: int = 0
    batches: int = 0
    added: int = 0
    updated: int = 0
    unavailable: int = 0
    skipped: int = 0
    more_remaining: bool = False


def load_reddit_youtube_ids(path: Path) -> list[str]:
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise RedditHydrationError(
            f"Could not read Reddit audit report: {exc}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise RedditHydrationError("Reddit audit report is not valid JSON.") from exc
    if not isinstance(report, dict):
        raise RedditHydrationError("Reddit audit report must be a JSON object.")
    if type(report.get("version")) is not int or report["version"] != REPORT_VERSION:
        raise RedditHydrationError("Unsupported Reddit audit report version.")
    source = report.get("source")
    if not isinstance(source, dict) or source.get("entry_point") != REDDIT_ENTRY_POINT:
        raise RedditHydrationError("Unsupported Reddit audit report source.")
    if report.get("collection_complete") is not True:
        raise RedditHydrationError("Reddit audit collection is not complete.")
    episodes = report.get("episodes")
    if not isinstance(episodes, list):
        raise RedditHydrationError("Reddit audit report episodes must be an array.")

    video_ids: list[str] = []
    seen: set[str] = set()
    for episode in episodes:
        if not isinstance(episode, dict):
            raise RedditHydrationError("Reddit audit episode entries must be objects.")
        links = episode.get("links")
        if not isinstance(links, list):
            raise RedditHydrationError("Reddit audit episode links must be an array.")
        if episode.get("has_local_win") is not True:
            continue
        for link in links:
            if not isinstance(link, dict):
                raise RedditHydrationError("Reddit audit links must be objects.")
            external_id = link.get("external_id")
            if (
                link.get("provider") != "youtube"
                or link.get("classification") != "new_unverified"
                or not isinstance(external_id, str)
                or not external_id.strip()
            ):
                continue
            video_id = external_id.strip()
            if video_id not in seen:
                seen.add(video_id)
                video_ids.append(video_id)
    return video_ids


def _lookup_statuses(connection: sqlite3.Connection) -> dict[str, str]:
    return {
        row["video_id"]: row["lookup_status"]
        for row in connection.execute(
            "SELECT video_id, lookup_status FROM reddit_youtube_lookup_state"
        )
    }


def hydrate_youtube_ids(
    connection: sqlite3.Connection,
    client: YouTubeClient,
    video_ids: list[str],
    *,
    limit: int | None,
    retry_unavailable: bool,
    timestamp: str,
) -> HydrationCounts:
    statuses = _lookup_statuses(connection)
    pending = [
        video_id
        for video_id in video_ids
        if video_id not in statuses
        or retry_unavailable
        and statuses[video_id] == "unavailable"
    ]
    counts = HydrationCounts(skipped=len(video_ids) - len(pending))
    selected = pending if limit is None else pending[:limit]
    counts.considered = len(selected)
    counts.more_remaining = len(selected) < len(pending)

    for offset in range(0, len(selected), 50):
        batch = selected[offset : offset + 50]
        try:
            videos = client.videos(batch)
        except APICallLimit:
            counts.more_remaining = True
            break
        returned_ids = [video.video_id for video in videos]
        if len(returned_ids) != len(set(returned_ids)) or not set(
            returned_ids
        ).issubset(batch):
            raise RedditHydrationError(
                "YouTube returned unexpected video IDs for a hydration batch."
            )
        returned = set(returned_ids)
        omitted = set(batch) - returned
        existing = (
            {
                row["video_id"]
                for row in connection.execute(
                    "SELECT video_id FROM youtube_videos WHERE video_id IN "
                    f"({','.join('?' for _ in returned)})",
                    sorted(returned),
                )
            }
            if returned
            else set()
        )
        with connection:
            for video in videos:
                upsert_video(connection, video, timestamp)
                connection.execute(
                    """
                    INSERT INTO reddit_youtube_lookup_state (
                        video_id, lookup_status, checked_at
                    ) VALUES (?, 'available', ?)
                    ON CONFLICT (video_id) DO UPDATE SET
                        lookup_status = 'available', checked_at = excluded.checked_at
                    """,
                    (video.video_id, timestamp),
                )
            for video_id in omitted:
                connection.execute(
                    """
                    INSERT INTO reddit_youtube_lookup_state (
                        video_id, lookup_status, checked_at
                    ) VALUES (?, 'unavailable', ?)
                    ON CONFLICT (video_id) DO UPDATE SET
                        lookup_status = 'unavailable', checked_at = excluded.checked_at
                    """,
                    (video_id, timestamp),
                )
            if omitted:
                unavailable_sql = (
                    "UPDATE youtube_videos SET availability_status = 'unavailable', "
                    "last_seen_at = ? WHERE video_id IN "
                    f"({','.join('?' for _ in omitted)})"
                )
                connection.execute(
                    unavailable_sql,
                    (timestamp, *sorted(omitted)),
                )
        counts.queried += len(batch)
        counts.batches += 1
        counts.added += len(returned - existing)
        counts.updated += len(returned & existing)
        counts.unavailable += len(omitted)
    return counts
