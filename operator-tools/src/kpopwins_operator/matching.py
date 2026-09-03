from __future__ import annotations

import json
import re
import sqlite3
import unicodedata
from dataclasses import dataclass
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from .registry import ChannelEntry

WIN_TERMS = (
    "winner",
    "win",
    "1위",
    "1st place",
    "#1",
    "trophy",
    "encore",
    "앵콜",
    "수상",
)
NEGATIVE_TERMS = (
    "teaser",
    "preview",
    "fancam",
    "직캠",
    "lyrics",
    "full episode",
    "music video",
    "official mv",
    "performance video",
)


@dataclass
class MatchCounts:
    considered: int = 0
    accepted: int = 0
    created: int = 0
    updated: int = 0


def normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return " ".join(re.sub(r"[\W_]+", " ", normalized, flags=re.UNICODE).split())


def _has_phrase(text: str, phrase: str) -> bool:
    normalized_phrase = normalize_text(phrase)
    return bool(normalized_phrase) and f" {normalized_phrase} " in f" {text} "


def _publication_date(value: str) -> date:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(ZoneInfo("Asia/Seoul")).date()


def score_video(
    *,
    title: str,
    description: str,
    artist: str,
    song: str,
    show_keywords: tuple[str, ...],
    win_date: date,
    publication_date: date,
) -> tuple[int, list[str]] | None:
    text = normalize_text(f"{title} {description}")
    title_text = normalize_text(title)
    reasons: list[str] = []
    if not _has_phrase(text, artist):
        return None
    score = 35
    reasons.append("artist phrase")
    if _has_phrase(text, song):
        score += 25
        reasons.append("song phrase")
    matched_keyword = next(
        (keyword for keyword in show_keywords if _has_phrase(text, keyword)), None
    )
    if matched_keyword:
        score += 15
        reasons.append(f"show keyword: {matched_keyword}")
    matched_win_term = next(
        (term for term in WIN_TERMS if term != "#1" and _has_phrase(text, term)),
        None,
    )
    if matched_win_term is None and re.search(
        r"(?<!\w)#\s*1(?!\w)", f"{title} {description}"
    ):
        matched_win_term = "#1"
    if not matched_win_term:
        return None
    score += 25
    reasons.append(f"win term: {matched_win_term}")
    distance = abs((publication_date - win_date).days)
    date_points = max(0, 15 - distance * 2)
    score += date_points
    reasons.append(f"publication date: {distance} day(s) from win")
    compact_date = win_date.strftime("%Y%m%d")
    if compact_date in re.sub(r"\D", "", title):
        score += 10
        reasons.append("title date")
    negatives = [term for term in NEGATIVE_TERMS if _has_phrase(title_text, term)]
    if negatives:
        score -= 50 * len(negatives)
        reasons.extend(f"negative: {term}" for term in negatives)
    return score, reasons


def _candidate_values(row: sqlite3.Row, metadata: dict, timestamp: str) -> dict:
    return {
        "show_slug": row["show_slug"],
        "win_date": row["win_date"],
        "reference_type": "video",
        "provider": "youtube",
        "external_id": row["video_id"],
        "url": f"https://www.youtube.com/watch?v={row['video_id']}",
        "title": row["title"],
        "publisher_name": row["channel_title"] or row["resolved_channel_title"],
        "publisher_external_id": row["channel_id"],
        "is_official": 1,
        "status": row["availability_status"],
        "published_at": row["published_at"],
        "last_verified_at": timestamp,
        "metadata": json.dumps(metadata, ensure_ascii=False, sort_keys=True),
        "timestamp": timestamp,
    }


def match_videos(
    connection: sqlite3.Connection,
    registry: list[ChannelEntry],
    *,
    show: str | None,
    min_score: int,
    limit: int | None,
    dry_run: bool,
    timestamp: str,
) -> MatchCounts:
    by_show: dict[str, tuple[str, ...]] = {}
    for entry in registry:
        by_show[entry.show_slug] = tuple(
            dict.fromkeys((*by_show.get(entry.show_slug, ()), *entry.keywords))
        )
    if show and show not in by_show:
        raise ValueError(f"Unknown show slug: {show}.")
    if not dry_run:
        with connection:
            connection.execute(
                """
                UPDATE reference_candidates SET
                    status = (SELECT availability_status FROM youtube_videos
                              WHERE video_id = reference_candidates.external_id),
                    updated_at = ?
                WHERE provider = 'youtube'
                  AND EXISTS (SELECT 1 FROM youtube_videos
                              WHERE video_id = reference_candidates.external_id)
                  AND status <> (SELECT availability_status FROM youtube_videos
                                 WHERE video_id = reference_candidates.external_id)
                """,
                (timestamp,),
            )
    sql = """
        SELECT DISTINCT wins.show_slug, wins.win_date,
               wins.artist_name, wins.song_title,
               video.*, channel.channel_title AS resolved_channel_title
        FROM wins
        JOIN youtube_channels AS channel
          ON channel.show_slug = wins.show_slug AND channel.is_active = 1
        JOIN youtube_videos AS video ON video.channel_id = channel.channel_id
        WHERE wins.is_current = 1 AND video.availability_status = 'active'
          AND video.published_at >= strftime(
              '%Y-%m-%dT%H:%M:%S', wins.win_date, '-1 day', '-9 hours'
          )
          AND video.published_at < strftime(
              '%Y-%m-%dT%H:%M:%S', wins.win_date, '+8 days', '-9 hours'
          )
    """
    parameters: list[str] = []
    if show:
        sql += " AND wins.show_slug = ?"
        parameters.append(show)
    sql += " ORDER BY wins.win_date, wins.show_slug, video.published_at, video.video_id"
    counts = MatchCounts()
    for row in connection.execute(sql, parameters):
        win_date = date.fromisoformat(row["win_date"])
        publication_date = _publication_date(row["published_at"])
        counts.considered += 1
        result = score_video(
            title=row["title"],
            description=row["description"],
            artist=row["artist_name"],
            song=row["song_title"],
            show_keywords=by_show[row["show_slug"]],
            win_date=win_date,
            publication_date=publication_date,
        )
        if result is None or result[0] < min_score:
            continue
        if limit is not None and counts.accepted >= limit:
            break
        score, reasons = result
        counts.accepted += 1
        existing = connection.execute(
            """
            SELECT id FROM reference_candidates
            WHERE show_slug = ? AND win_date = ? AND provider = 'youtube'
              AND external_id = ?
            """,
            (row["show_slug"], row["win_date"], row["video_id"]),
        ).fetchone()
        if dry_run:
            if existing:
                counts.updated += 1
            else:
                counts.created += 1
            continue
        metadata = {
            "youtube_match": {
                "score": score,
                "reasons": reasons,
                "show_mapping": row["show_slug"],
                "korean_publication_date": publication_date.isoformat(),
            }
        }
        values = _candidate_values(row, metadata, timestamp)
        with connection:
            if existing:
                candidate_id = existing["id"]
                connection.execute(
                    """
                    UPDATE reference_candidates SET
                        url = :url, title = :title,
                        publisher_name = :publisher_name,
                        publisher_external_id = :publisher_external_id,
                        is_official = :is_official, status = :status,
                        published_at = :published_at,
                        last_verified_at = :last_verified_at,
                        metadata = :metadata, updated_at = :timestamp
                    WHERE id = :candidate_id
                    """,
                    {**values, "candidate_id": candidate_id},
                )
                counts.updated += 1
            else:
                cursor = connection.execute(
                    """
                    INSERT INTO reference_candidates (
                        show_slug, win_date, reference_type, provider, external_id,
                        url, title, publisher_name, publisher_external_id,
                        is_official, status, published_at, last_verified_at,
                        metadata, review_status, created_at, updated_at
                    ) VALUES (
                        :show_slug, :win_date, :reference_type, :provider,
                        :external_id, :url, :title, :publisher_name,
                        :publisher_external_id, :is_official, :status,
                        :published_at, :last_verified_at, :metadata, 'pending',
                        :timestamp, :timestamp
                    )
                    """,
                    values,
                )
                candidate_id = cursor.lastrowid
                counts.created += 1
            connection.execute(
                """
                INSERT INTO youtube_candidate_matches (
                    candidate_id, video_id, score, reasons, show_mapping,
                    korean_publication_date, matched_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (candidate_id) DO UPDATE SET
                    video_id = excluded.video_id, score = excluded.score,
                    reasons = excluded.reasons,
                    show_mapping = excluded.show_mapping,
                    korean_publication_date = excluded.korean_publication_date,
                    matched_at = excluded.matched_at
                """,
                (
                    candidate_id,
                    row["video_id"],
                    score,
                    json.dumps(reasons, ensure_ascii=False),
                    row["show_slug"],
                    publication_date.isoformat(),
                    timestamp,
                ),
            )
    return counts
