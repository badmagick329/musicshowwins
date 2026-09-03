from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from .database import insert_candidate
from .reddit import canonical_watch_url, parse_video_link
from .reddit_hydration import load_reddit_audit_report
from .validation import normalize_candidate


class RedditOfficialImportError(ValueError):
    pass


@dataclass(frozen=True)
class OfficialAuditLink:
    show_slug: str
    win_date: str
    video_id: str
    canonical_url: str
    episode_url: str
    classification: str


@dataclass
class ImportCounts:
    eligible: int = 0
    selected: int = 0
    created: int = 0
    existing: int = 0


def _required_text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RedditOfficialImportError(f"Reddit audit {field} must be non-empty text.")
    return value.strip()


def load_official_audit_links(path: Path) -> list[OfficialAuditLink]:
    report = load_reddit_audit_report(path)
    found: list[OfficialAuditLink] = []
    for episode in report["episodes"]:
        if episode.get("has_local_win") is not True:
            continue
        for link in episode["links"]:
            if (
                link.get("provider") != "youtube"
                or link.get("classification") != "new_official"
            ):
                continue
            external_id = link.get("external_id")
            canonical = link.get("canonical_url")
            if not isinstance(external_id, str) or not isinstance(canonical, str):
                raise RedditOfficialImportError(
                    "Reddit audit YouTube identity fields must be text."
                )
            video_id = external_id.strip()
            canonical_url = canonical.strip()
            if not video_id or not canonical_url:
                continue
            parsed = parse_video_link(canonical_url)
            expected_url = canonical_watch_url(video_id)
            if (
                parsed is None
                or parsed.provider != "youtube"
                or parsed.external_id != video_id
                or canonical_url != expected_url
            ):
                continue
            show_slug = _required_text(episode.get("show_slug"), "show_slug")
            win_date = _required_text(episode.get("win_date"), "win_date")
            episode_url = _required_text(episode.get("episode_url"), "episode_url")
            found.append(
                OfficialAuditLink(
                    show_slug=show_slug,
                    win_date=win_date,
                    video_id=video_id,
                    canonical_url=canonical_url,
                    episode_url=episode_url,
                    classification="new_official",
                )
            )

    unique: dict[tuple[str, str, str], OfficialAuditLink] = {}
    for entry in sorted(
        found,
        key=lambda item: (
            item.show_slug,
            item.win_date,
            item.video_id,
            item.episode_url,
        ),
    ):
        unique.setdefault((entry.show_slug, entry.win_date, entry.video_id), entry)
    return list(unique.values())


def _candidate_for_entry(
    connection: sqlite3.Connection,
    entry: OfficialAuditLink,
    timestamp: str,
) -> dict:
    row = connection.execute(
        """
        SELECT wins.is_current, video.channel_id, video.channel_title,
               video.title, video.published_at, video.availability_status,
               (
                   SELECT channel.channel_title
                   FROM youtube_channels AS channel
                   WHERE channel.show_slug = wins.show_slug
                     AND channel.channel_id = video.channel_id
                     AND channel.is_active = 1
                   ORDER BY channel.id
                   LIMIT 1
               ) AS verified_channel_title,
               EXISTS (
                   SELECT 1 FROM youtube_channels AS channel
                   WHERE channel.show_slug = wins.show_slug
                     AND channel.channel_id = video.channel_id
                     AND channel.is_active = 1
               ) AS current_official_channel
        FROM wins
        LEFT JOIN youtube_videos AS video ON video.video_id = ?
        WHERE wins.show_slug = ? AND wins.win_date = ?
        """,
        (entry.video_id, entry.show_slug, entry.win_date),
    ).fetchone()
    identity = f"{entry.show_slug}/{entry.win_date}/{entry.video_id}"
    if row is None or row["is_current"] != 1:
        raise RedditOfficialImportError(
            f"Stale Reddit audit entry has no current local win: {identity}."
        )
    if row["channel_id"] is None:
        raise RedditOfficialImportError(
            f"Stale Reddit audit entry has no local YouTube video: {identity}."
        )
    if row["availability_status"] != "active":
        raise RedditOfficialImportError(
            f"Stale Reddit audit entry references an unavailable video: {identity}."
        )
    if row["current_official_channel"] != 1:
        raise RedditOfficialImportError(
            "Stale Reddit audit entry no longer matches an active official channel: "
            f"{identity}."
        )
    return normalize_candidate(
        {
            "show_slug": entry.show_slug,
            "win_date": entry.win_date,
            "reference_type": "video",
            "provider": "youtube",
            "external_id": entry.video_id,
            "url": entry.canonical_url,
            "title": row["title"],
            "publisher_name": (
                row["channel_title"].strip() or row["verified_channel_title"]
            ),
            "publisher_external_id": row["channel_id"],
            "is_official": True,
            "status": row["availability_status"],
            "published_at": row["published_at"],
            "last_verified_at": timestamp,
            "metadata": {
                "reddit_audit": {
                    "episode_url": entry.episode_url,
                    "classification": entry.classification,
                }
            },
            "review_status": "pending",
        }
    )


def import_official_links(
    connection: sqlite3.Connection,
    entries: list[OfficialAuditLink],
    *,
    limit: int | None,
    dry_run: bool,
    timestamp: str,
) -> ImportCounts:
    selected = entries if limit is None else entries[:limit]
    candidates = [
        _candidate_for_entry(connection, entry, timestamp) for entry in selected
    ]
    existing: list[bool] = []
    for candidate in candidates:
        row = connection.execute(
            """
            SELECT 1 FROM reference_candidates
            WHERE show_slug = ? AND win_date = ?
              AND (
                  (provider = 'youtube' AND external_id = ?)
                  OR url = ?
              )
            LIMIT 1
            """,
            (
                candidate["show_slug"],
                candidate["win_date"],
                candidate["external_id"],
                candidate["url"],
            ),
        ).fetchone()
        existing.append(row is not None)

    counts = ImportCounts(
        eligible=len(entries),
        selected=len(selected),
        created=existing.count(False),
        existing=existing.count(True),
    )
    if dry_run:
        return counts
    with connection:
        for candidate, already_exists in zip(candidates, existing, strict=True):
            if not already_exists:
                insert_candidate(connection, candidate, timestamp=timestamp)
    return counts
