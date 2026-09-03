from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from .youtube import APICallLimit, Video, YouTubeClient

CUTOFF = "2013-12-01T00:00:00Z"


@dataclass
class IngestionCounts:
    channels: int = 0
    pages: int = 0
    discovered: int = 0
    added: int = 0
    updated: int = 0
    unavailable: int = 0
    more_remaining: bool = False


def upsert_video(connection: sqlite3.Connection, video: Video, seen_at: str) -> bool:
    existed = connection.execute(
        "SELECT 1 FROM youtube_videos WHERE video_id = ?", (video.video_id,)
    ).fetchone()
    connection.execute(
        """
        INSERT INTO youtube_videos (
            video_id, channel_id, channel_title, title, description,
            published_at, duration, privacy_status, embeddable, live_broadcast_state,
            availability_status, first_seen_at, last_seen_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?)
        ON CONFLICT (video_id) DO UPDATE SET
            channel_id = excluded.channel_id,
            channel_title = excluded.channel_title,
            title = excluded.title,
            description = excluded.description,
            published_at = excluded.published_at,
            duration = excluded.duration,
            privacy_status = excluded.privacy_status,
            embeddable = excluded.embeddable,
            live_broadcast_state = excluded.live_broadcast_state,
            availability_status = 'active',
            last_seen_at = excluded.last_seen_at
        """,
        (
            video.video_id,
            video.channel_id,
            video.channel_title,
            video.title,
            video.description,
            video.published_at,
            video.duration,
            video.privacy_status,
            int(video.embeddable),
            video.live_broadcast_state,
            seen_at,
            seen_at,
        ),
    )
    connection.execute(
        """
        UPDATE reddit_youtube_lookup_state
        SET lookup_status = 'available', checked_at = ?
        WHERE video_id = ?
        """,
        (seen_at, video.video_id),
    )
    return existed is None


def _selected_channels(
    connection: sqlite3.Connection, handle: str | None
) -> list[sqlite3.Row]:
    sql = """
        SELECT channel_id, MIN(uploads_playlist_id) AS uploads_playlist_id
        FROM youtube_channels
        WHERE is_active = 1
    """
    parameters: tuple[str, ...] = ()
    if handle:
        sql += " AND lower(configured_handle) = lower(?)"
        parameters = (handle,)
    sql += " GROUP BY channel_id ORDER BY channel_id"
    rows = list(connection.execute(sql, parameters))
    if handle and not rows:
        raise ValueError(f"No verified active channel found for {handle}.")
    if not rows:
        raise ValueError("No verified channels; run `youtube verify-channels --apply`.")
    return rows


def ingest_channels(
    connection: sqlite3.Connection,
    client: YouTubeClient,
    *,
    handle: str | None,
    max_pages: int,
    restart: bool,
    timestamp: str,
) -> IngestionCounts:
    channels = _selected_channels(connection, handle)
    counts = IngestionCounts(channels=len(channels))
    for channel in channels:
        channel_id = channel["channel_id"]
        if restart:
            with connection:
                connection.execute(
                    """
                    INSERT INTO youtube_ingestion_state (
                        channel_id, next_page_token, initial_scan_complete,
                        last_error
                    ) VALUES (?, NULL, 0, '')
                    ON CONFLICT (channel_id) DO UPDATE SET
                        next_page_token = NULL,
                        initial_scan_complete = 0,
                        last_error = ''
                    """,
                    (channel_id,),
                )
        state = connection.execute(
            "SELECT * FROM youtube_ingestion_state WHERE channel_id = ?", (channel_id,)
        ).fetchone()
        if state is None:
            with connection:
                connection.execute(
                    "INSERT INTO youtube_ingestion_state (channel_id) VALUES (?)",
                    (channel_id,),
                )
            state = connection.execute(
                "SELECT * FROM youtube_ingestion_state WHERE channel_id = ?",
                (channel_id,),
            ).fetchone()
        initial = not bool(state["initial_scan_complete"])
        token = state["next_page_token"] if initial else None
        channel_pages = 0
        while channel_pages < max_pages:
            with connection:
                connection.execute(
                    """
                    UPDATE youtube_ingestion_state
                    SET last_attempted_at = ?, last_error = '' WHERE channel_id = ?
                    """,
                    (timestamp, channel_id),
                )
            try:
                page = client.playlist_page(channel["uploads_playlist_id"], token)
                page_ids = list(page.video_ids)
                hit_cutoff = False
                if initial:
                    retained: list[str] = []
                    for video_id in page_ids:
                        if page.published_at[video_id] < CUTOFF:
                            hit_cutoff = True
                            break
                        retained.append(video_id)
                    page_ids = retained
                known_before = (
                    {
                        row["video_id"]
                        for row in connection.execute(
                            "SELECT video_id FROM youtube_videos WHERE video_id IN "
                            f"({','.join('?' for _ in page_ids)})",
                            page_ids,
                        )
                    }
                    if page_ids
                    else set()
                )
                videos = []
                for offset in range(0, len(page_ids), 50):
                    videos.extend(client.videos(page_ids[offset : offset + 50]))
            except APICallLimit:
                counts.more_remaining = True
                return counts
            except Exception as exc:
                with connection:
                    connection.execute(
                        "UPDATE youtube_ingestion_state SET last_error = ? "
                        "WHERE channel_id = ?",
                        (str(exc), channel_id),
                    )
                raise
            returned = {video.video_id for video in videos}
            omitted = set(page_ids) - returned
            next_token = page.next_page_token
            complete = False
            if initial and (hit_cutoff or not next_token):
                complete = True
                next_token = None
            incremental_done = not initial and (
                not page_ids or set(page_ids).issubset(known_before) or not next_token
            )
            with connection:
                for video in videos:
                    if video.channel_id != channel_id:
                        raise ValueError(
                            f"Video {video.video_id} belongs to an unexpected channel."
                        )
                    if upsert_video(connection, video, timestamp):
                        counts.added += 1
                    else:
                        counts.updated += 1
                if omitted:
                    placeholders = ",".join("?" for _ in omitted)
                    connection.execute(
                        f"""
                        UPDATE youtube_videos SET availability_status = 'unavailable',
                            last_seen_at = ?
                        WHERE video_id IN ({placeholders})
                        """,
                        (timestamp, *sorted(omitted)),
                    )
                    counts.unavailable += len(omitted)
                connection.execute(
                    """
                    UPDATE youtube_ingestion_state SET
                        next_page_token = ?,
                        initial_scan_complete = ?,
                        last_successful_at = ?,
                        last_error = '',
                        oldest_imported_at = COALESCE(
                            (SELECT MIN(published_at) FROM youtube_videos
                             WHERE channel_id = ?), oldest_imported_at
                        )
                    WHERE channel_id = ?
                    """,
                    (
                        next_token if initial and not complete else None,
                        int(complete or not initial),
                        timestamp,
                        channel_id,
                        channel_id,
                    ),
                )
            counts.pages += 1
            channel_pages += 1
            counts.discovered += len(page_ids)
            if complete or incremental_done:
                break
            token = next_token
        else:
            counts.more_remaining = True
    return counts
