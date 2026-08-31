from __future__ import annotations

import json
import sqlite3
from collections.abc import Sequence
from typing import TextIO


def list_candidates(
    connection: sqlite3.Connection,
    stdout: TextIO,
    *,
    status: str,
    show: str | None,
    provider: str | None,
    minimum_score: int | None,
    limit: int,
) -> None:
    sql = """
        SELECT candidate.id, candidate.review_status, candidate.show_slug,
               candidate.win_date, wins.artist_name, wins.song_title,
               candidate.title, candidate.publisher_name,
               candidate.published_at, candidate.url, match.score
        FROM reference_candidates AS candidate
        JOIN wins ON wins.show_slug = candidate.show_slug
                 AND wins.win_date = candidate.win_date
        LEFT JOIN youtube_candidate_matches AS match
               ON match.candidate_id = candidate.id
        WHERE candidate.review_status = ?
    """
    parameters: list[object] = [status]
    if show:
        sql += " AND candidate.show_slug = ?"
        parameters.append(show)
    if provider is not None:
        if not provider.strip():
            raise ValueError("Provider must not be empty.")
        sql += " AND candidate.provider = ?"
        parameters.append(provider.strip().lower())
    if minimum_score is not None:
        sql += " AND match.score >= ?"
        parameters.append(minimum_score)
    sql += " ORDER BY candidate.win_date, candidate.show_slug, candidate.id LIMIT ?"
    parameters.append(limit)
    print(
        "id\tstatus\tshow\twin_date\tartist\tsong\tscore\tvideo_title\t"
        "channel\tpublished_at\turl",
        file=stdout,
    )
    for row in connection.execute(sql, parameters):
        print(
            "\t".join(
                str(value if value is not None else "-")
                for value in (
                    row["id"],
                    row["review_status"],
                    row["show_slug"],
                    row["win_date"],
                    row["artist_name"],
                    row["song_title"],
                    row["score"],
                    row["title"],
                    row["publisher_name"],
                    row["published_at"],
                    row["url"],
                )
            ),
            file=stdout,
        )


def show_candidate(
    connection: sqlite3.Connection, stdout: TextIO, candidate_id: int
) -> None:
    row = connection.execute(
        """
        SELECT candidate.*, wins.artist_name, wins.song_title, match.score,
               match.reasons, match.show_mapping, match.korean_publication_date
        FROM reference_candidates AS candidate
        JOIN wins ON wins.show_slug = candidate.show_slug
                 AND wins.win_date = candidate.win_date
        LEFT JOIN youtube_candidate_matches AS match
               ON match.candidate_id = candidate.id
        WHERE candidate.id = ?
        """,
        (candidate_id,),
    ).fetchone()
    if row is None:
        raise ValueError(f"Candidate {candidate_id} does not exist.")
    for key in row.keys():
        value = row[key]
        if key in {"metadata", "reasons"} and value:
            value = json.dumps(json.loads(value), ensure_ascii=False, indent=2)
        print(f"{key}: {value if value is not None else '-'}", file=stdout)


def review_candidates(
    connection: sqlite3.Connection,
    candidate_ids: Sequence[int],
    *,
    decision: str,
    timestamp: str,
) -> int:
    placeholders = ",".join("?" for _ in candidate_ids)
    select_sql = (
        "SELECT id, show_slug, win_date, provider, review_status "
        "FROM reference_candidates "
        f"WHERE id IN ({placeholders})"
    )
    rows = list(
        connection.execute(
            select_sql,
            candidate_ids,
        )
    )
    found = {row["id"] for row in rows}
    missing = [
        candidate_id for candidate_id in candidate_ids if candidate_id not in found
    ]
    if missing:
        raise ValueError(f"Candidate(s) not found: {', '.join(map(str, missing))}.")
    with connection:
        update_sql = (
            "UPDATE reference_candidates SET review_status = ?, updated_at = ? "
            f"WHERE id IN ({placeholders})"
        )
        connection.execute(
            update_sql,
            (decision, timestamp, *candidate_ids),
        )
        if decision == "approved":
            for row in rows:
                if row["provider"] != "youtube":
                    continue
                connection.execute(
                    """
                    INSERT INTO search_state (
                        show_slug, win_date, provider, status, attempt_count,
                        last_attempt_at, next_attempt_at, last_error, updated_at
                    ) VALUES (?, ?, 'youtube', 'matched', 0, ?, NULL, '', ?)
                    ON CONFLICT (show_slug, win_date, provider) DO UPDATE SET
                        status = 'matched', last_attempt_at = excluded.last_attempt_at,
                        next_attempt_at = NULL, last_error = '',
                        updated_at = excluded.updated_at
                    """,
                    (row["show_slug"], row["win_date"], timestamp, timestamp),
                )
        elif decision == "rejected":
            affected_wins = {
                (row["show_slug"], row["win_date"])
                for row in rows
                if row["provider"] == "youtube" and row["review_status"] == "approved"
            }
            for show_slug, win_date in affected_wins:
                remaining = connection.execute(
                    """
                    SELECT 1 FROM reference_candidates
                    WHERE show_slug = ? AND win_date = ?
                      AND provider = 'youtube' AND review_status = 'approved'
                    LIMIT 1
                    """,
                    (show_slug, win_date),
                ).fetchone()
                if remaining is None:
                    connection.execute(
                        """
                        UPDATE search_state
                        SET status = 'pending', next_attempt_at = NULL,
                            last_error = '', updated_at = ?
                        WHERE show_slug = ? AND win_date = ?
                          AND provider = 'youtube'
                        """,
                        (timestamp, show_slug, win_date),
                    )
    return len(rows)
