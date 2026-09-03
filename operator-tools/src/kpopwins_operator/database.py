from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .config import Config
from .validation import normalize_candidate

SCHEMA_VERSION = 3


class DatabaseError(RuntimeError):
    pass


SCHEMA_V1 = """
CREATE TABLE IF NOT EXISTS wins (
    show_slug TEXT NOT NULL,
    win_date TEXT NOT NULL,
    api_win_id INTEGER NOT NULL,
    artist_name TEXT NOT NULL,
    song_title TEXT NOT NULL,
    is_current INTEGER NOT NULL DEFAULT 1 CHECK (is_current IN (0, 1)),
    last_seen_at TEXT NOT NULL,
    PRIMARY KEY (show_slug, win_date)
);

CREATE TABLE IF NOT EXISTS search_state (
    show_slug TEXT NOT NULL,
    win_date TEXT NOT NULL,
    provider TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'matched', 'no_match', 'error', 'disabled')),
    attempt_count INTEGER NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
    last_attempt_at TEXT,
    next_attempt_at TEXT,
    last_error TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL,
    PRIMARY KEY (show_slug, win_date, provider),
    FOREIGN KEY (show_slug, win_date)
        REFERENCES wins(show_slug, win_date) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS search_state_due_idx
    ON search_state(provider, status, next_attempt_at);

CREATE TABLE IF NOT EXISTS reference_candidates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    show_slug TEXT NOT NULL,
    win_date TEXT NOT NULL,
    reference_type TEXT NOT NULL
        CHECK (reference_type IN ('video', 'article', 'other')),
    provider TEXT NOT NULL,
    external_id TEXT NOT NULL DEFAULT '',
    url TEXT NOT NULL,
    title TEXT NOT NULL DEFAULT '',
    publisher_name TEXT NOT NULL DEFAULT '',
    publisher_external_id TEXT NOT NULL DEFAULT '',
    is_official INTEGER NOT NULL DEFAULT 0 CHECK (is_official IN (0, 1)),
    status TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'unavailable')),
    published_at TEXT,
    last_verified_at TEXT,
    metadata TEXT NOT NULL DEFAULT '{}'
        CHECK (json_valid(metadata) AND json_type(metadata) = 'object'),
    review_status TEXT NOT NULL DEFAULT 'pending'
        CHECK (review_status IN ('pending', 'approved', 'rejected')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE (show_slug, win_date, url),
    FOREIGN KEY (show_slug, win_date)
        REFERENCES wins(show_slug, win_date) ON DELETE CASCADE
);

CREATE UNIQUE INDEX IF NOT EXISTS candidate_provider_external_id_idx
    ON reference_candidates(show_slug, win_date, provider, external_id)
    WHERE external_id <> '';

CREATE INDEX IF NOT EXISTS candidate_review_status_idx
    ON reference_candidates(review_status, show_slug, win_date);
"""

MIGRATION_1_TO_2 = """
CREATE TABLE IF NOT EXISTS youtube_channels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    show_slug TEXT NOT NULL,
    configured_handle TEXT NOT NULL,
    channel_id TEXT NOT NULL,
    channel_title TEXT NOT NULL,
    uploads_playlist_id TEXT NOT NULL,
    verified_at TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    UNIQUE (show_slug, configured_handle)
);

CREATE INDEX IF NOT EXISTS youtube_channels_channel_idx
    ON youtube_channels(channel_id, is_active);

CREATE TABLE IF NOT EXISTS youtube_videos (
    video_id TEXT PRIMARY KEY,
    channel_id TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    published_at TEXT NOT NULL,
    duration TEXT NOT NULL DEFAULT '',
    privacy_status TEXT NOT NULL DEFAULT '',
    embeddable INTEGER NOT NULL DEFAULT 1 CHECK (embeddable IN (0, 1)),
    live_broadcast_state TEXT NOT NULL DEFAULT 'none',
    availability_status TEXT NOT NULL DEFAULT 'active'
        CHECK (availability_status IN ('active', 'unavailable')),
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS youtube_videos_channel_published_idx
    ON youtube_videos(channel_id, published_at DESC);

CREATE TABLE IF NOT EXISTS youtube_ingestion_state (
    channel_id TEXT PRIMARY KEY,
    next_page_token TEXT,
    initial_scan_complete INTEGER NOT NULL DEFAULT 0
        CHECK (initial_scan_complete IN (0, 1)),
    last_attempted_at TEXT,
    last_successful_at TEXT,
    last_error TEXT NOT NULL DEFAULT '',
    oldest_imported_at TEXT
);

CREATE TABLE IF NOT EXISTS youtube_candidate_matches (
    candidate_id INTEGER PRIMARY KEY,
    video_id TEXT NOT NULL,
    score INTEGER NOT NULL,
    reasons TEXT NOT NULL CHECK (json_valid(reasons) AND json_type(reasons) = 'array'),
    show_mapping TEXT NOT NULL,
    korean_publication_date TEXT NOT NULL,
    matched_at TEXT NOT NULL,
    FOREIGN KEY (candidate_id) REFERENCES reference_candidates(id) ON DELETE CASCADE,
    FOREIGN KEY (video_id) REFERENCES youtube_videos(video_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS youtube_api_usage (
    pacific_date TEXT NOT NULL,
    api_method TEXT NOT NULL,
    call_count INTEGER NOT NULL DEFAULT 0 CHECK (call_count >= 0),
    PRIMARY KEY (pacific_date, api_method)
);
"""

MIGRATION_2_TO_3 = """
ALTER TABLE youtube_videos
ADD COLUMN channel_title TEXT NOT NULL DEFAULT '';

CREATE TABLE reddit_youtube_lookup_state (
    video_id TEXT PRIMARY KEY,
    lookup_status TEXT NOT NULL
        CHECK (lookup_status IN ('available', 'unavailable')),
    checked_at TEXT NOT NULL
);
"""

SCHEMA = SCHEMA_V1 + MIGRATION_1_TO_2 + MIGRATION_2_TO_3


def _connect(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database(config: Config) -> int:
    config.home.mkdir(parents=True, exist_ok=True)
    config.manifests_dir.mkdir(parents=True, exist_ok=True)
    with _connect(config.database_path) as connection:
        version = connection.execute("PRAGMA user_version").fetchone()[0]
        if version > SCHEMA_VERSION:
            raise DatabaseError(
                "The operator database was created by a newer tool version."
            )
        if version == 0:
            connection.executescript(SCHEMA_V1)
            connection.execute("PRAGMA user_version = 1")
            version = 1
        if version == 1:
            connection.executescript(MIGRATION_1_TO_2)
            connection.execute("PRAGMA user_version = 2")
            version = 2
        if version == 2:
            connection.executescript(MIGRATION_2_TO_3)
            connection.execute("PRAGMA user_version = 3")
    return SCHEMA_VERSION


def open_database(config: Config) -> sqlite3.Connection:
    if not config.database_path.is_file():
        raise DatabaseError("Operator state is not initialized; run `init` first.")
    connection = _connect(config.database_path)
    version = connection.execute("PRAGMA user_version").fetchone()[0]
    if version != SCHEMA_VERSION:
        connection.close()
        raise DatabaseError("Operator database schema is not current; run `init`.")
    return connection


def utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def due_searches(
    connection: sqlite3.Connection,
    provider: str,
    *,
    due_at: str,
    limit: int | None,
) -> list[sqlite3.Row]:
    sql = """
        SELECT wins.show_slug, wins.win_date, wins.artist_name, wins.song_title,
               COALESCE(state.status, 'pending') AS search_status,
               COALESCE(state.attempt_count, 0) AS attempt_count,
               state.next_attempt_at
        FROM wins
        LEFT JOIN search_state AS state
          ON state.show_slug = wins.show_slug
         AND state.win_date = wins.win_date
         AND state.provider = ?
        WHERE wins.is_current = 1
          AND (
              state.show_slug IS NULL
              OR (
                  state.status IN ('pending', 'no_match')
                  AND (state.next_attempt_at IS NULL OR state.next_attempt_at <= ?)
              )
          )
        ORDER BY state.next_attempt_at, wins.win_date, wins.show_slug
    """
    parameters: list[Any] = [provider, due_at]
    if limit is not None:
        sql += " LIMIT ?"
        parameters.append(limit)
    return list(connection.execute(sql, parameters))


def insert_candidate(
    connection: sqlite3.Connection,
    candidate: dict[str, Any],
    *,
    timestamp: str | None = None,
) -> int:
    normalized = normalize_candidate(candidate)
    encoded_metadata = json.dumps(
        normalized["metadata"],
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    now = timestamp or utc_now()
    values = {
        **normalized,
        "metadata": encoded_metadata,
        "created_at": now,
        "updated_at": now,
    }
    cursor = connection.execute(
        """
        INSERT INTO reference_candidates (
            show_slug, win_date, reference_type, provider, external_id, url,
            title, publisher_name, publisher_external_id, is_official, status,
            published_at, last_verified_at, metadata, review_status,
            created_at, updated_at
        ) VALUES (
            :show_slug, :win_date, :reference_type, :provider, :external_id, :url,
            :title, :publisher_name, :publisher_external_id, :is_official,
            :status, :published_at, :last_verified_at, :metadata, :review_status,
            :created_at, :updated_at
        )
        """,
        values,
    )
    return cursor.lastrowid
