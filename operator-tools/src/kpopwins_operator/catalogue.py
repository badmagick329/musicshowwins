from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date
from typing import Any
from urllib.parse import urljoin, urlsplit

import requests

from .database import utc_now


class CatalogueError(RuntimeError):
    pass


@dataclass(frozen=True)
class CatalogueWin:
    show_slug: str
    win_date: str
    api_win_id: int
    artist_name: str
    song_title: str

    @property
    def key(self) -> tuple[str, str]:
        return self.show_slug, self.win_date


@dataclass(frozen=True)
class RefreshCounts:
    fetched: int
    added: int
    updated: int
    unchanged: int
    no_longer_current: int


def _origin(url: str) -> tuple[str, str, int | None]:
    parsed = urlsplit(url)
    scheme = parsed.scheme.lower()
    default_port = 443 if scheme == "https" else 80 if scheme == "http" else None
    return scheme, (parsed.hostname or "").lower(), parsed.port or default_port


def _required_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CatalogueError(f"API win field {field} is invalid.")
    return value.strip()


def _validate_win(value: Any) -> CatalogueWin:
    if not isinstance(value, dict):
        raise CatalogueError("API win records must be objects.")
    api_win_id = value.get("id")
    if type(api_win_id) is not int or api_win_id < 1:
        raise CatalogueError("API win field id is invalid.")
    win_date = _required_text(value.get("date"), "date")
    try:
        parsed_date = date.fromisoformat(win_date)
    except ValueError as exc:
        raise CatalogueError("API win field date is invalid.") from exc
    if parsed_date.isoformat() != win_date:
        raise CatalogueError("API win field date is invalid.")
    show = value.get("show")
    song = value.get("song")
    if not isinstance(show, dict):
        raise CatalogueError("API win field show is invalid.")
    if not isinstance(song, dict):
        raise CatalogueError("API win field song is invalid.")
    artist = song.get("artist")
    if not isinstance(artist, dict):
        raise CatalogueError("API win field song.artist is invalid.")
    return CatalogueWin(
        show_slug=_required_text(show.get("slug"), "show.slug"),
        win_date=win_date,
        api_win_id=api_win_id,
        artist_name=_required_text(artist.get("name"), "song.artist.name"),
        song_title=_required_text(song.get("title"), "song.title"),
    )


def fetch_catalogue(
    api_base_url: str,
    *,
    session: requests.Session | None = None,
) -> list[CatalogueWin]:
    client = session or requests.Session()
    configured_origin = _origin(api_base_url)
    next_url: str | None = f"{api_base_url.rstrip('/')}/wins"
    visited: set[str] = set()
    records: list[CatalogueWin] = []
    keys: set[tuple[str, str]] = set()
    expected_count: int | None = None

    while next_url is not None:
        if _origin(next_url) != configured_origin:
            raise CatalogueError("API pagination left the configured origin.")
        if next_url in visited:
            raise CatalogueError("API pagination loop detected.")
        visited.add(next_url)
        try:
            response = client.get(next_url, timeout=30)
            response.raise_for_status()
            page = response.json()
        except (requests.RequestException, ValueError) as exc:
            raise CatalogueError("Could not fetch a complete win catalogue.") from exc
        if not isinstance(page, dict):
            raise CatalogueError("API page must be a JSON object.")
        count = page.get("count")
        if type(count) is not int or count < 0:
            raise CatalogueError("API page count is invalid.")
        if expected_count is None:
            expected_count = count
        elif count != expected_count:
            raise CatalogueError("API page count changed during pagination.")
        results = page.get("results")
        if not isinstance(results, list):
            raise CatalogueError("API page results must be an array.")
        for raw_record in results:
            record = _validate_win(raw_record)
            if record.key in keys:
                raise CatalogueError("API catalogue contains a duplicate win.")
            keys.add(record.key)
            records.append(record)
        next_value = page.get("next")
        if next_value is None:
            next_url = None
        elif isinstance(next_value, str) and next_value.strip():
            next_url = urljoin(next_url, next_value.strip())
        else:
            raise CatalogueError("API page next link is invalid.")

    if expected_count != len(records):
        raise CatalogueError("API catalogue count does not match returned wins.")
    return records


def refresh_catalogue(
    connection: sqlite3.Connection,
    api_base_url: str,
    *,
    session: requests.Session | None = None,
    seen_at: str | None = None,
) -> RefreshCounts:
    existing = {
        (row["show_slug"], row["win_date"]): row
        for row in connection.execute("SELECT * FROM wins")
    }
    previously_current = {
        key for key, row in existing.items() if row["is_current"] == 1
    }
    with connection:
        connection.execute("UPDATE wins SET is_current = 0 WHERE is_current = 1")
        records = fetch_catalogue(api_base_url, session=session)
        fetched_keys = {record.key for record in records}
        added = updated = unchanged = 0
        timestamp = seen_at or utc_now()
        for record in records:
            previous = existing.get(record.key)
            current_values = (
                record.api_win_id,
                record.artist_name,
                record.song_title,
            )
            if previous is None:
                added += 1
            elif previous["is_current"] != 1 or current_values != (
                previous["api_win_id"],
                previous["artist_name"],
                previous["song_title"],
            ):
                updated += 1
            else:
                unchanged += 1
            connection.execute(
                """
                INSERT INTO wins (
                    show_slug, win_date, api_win_id, artist_name, song_title,
                    is_current, last_seen_at
                ) VALUES (?, ?, ?, ?, ?, 1, ?)
                ON CONFLICT(show_slug, win_date) DO UPDATE SET
                    api_win_id = excluded.api_win_id,
                    artist_name = excluded.artist_name,
                    song_title = excluded.song_title,
                    is_current = 1,
                    last_seen_at = excluded.last_seen_at
                """,
                (
                    record.show_slug,
                    record.win_date,
                    record.api_win_id,
                    record.artist_name,
                    record.song_title,
                    timestamp,
                ),
            )
        no_longer_current = len(previously_current - fetched_keys)
    return RefreshCounts(
        fetched=len(records),
        added=added,
        updated=updated,
        unchanged=unchanged,
        no_longer_current=no_longer_current,
    )
