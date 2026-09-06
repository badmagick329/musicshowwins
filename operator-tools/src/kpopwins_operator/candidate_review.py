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
    events = [
        dict(event)
        for event in connection.execute(
            "SELECT * FROM candidate_review_events WHERE candidate_id=? ORDER BY id",
            (candidate_id,),
        )
    ]
    print(
        "review_history: " + json.dumps(events, ensure_ascii=False, indent=2),
        file=stdout,
    )


def review_candidates(
    connection: sqlite3.Connection,
    candidate_ids: Sequence[int],
    *,
    decision: str,
    timestamp: str,
    reviewer: str,
    reason: str,
    revise: bool = False,
) -> int:
    """Prevent silent decision reversals and retain the evidence behind revisions."""
    if decision not in {"approved", "rejected", "withdrawn"}:
        raise ValueError("Invalid review decision.")
    if not candidate_ids or len(set(candidate_ids)) != len(candidate_ids):
        raise ValueError("Supply unique candidate IDs.")
    if not reviewer.strip() or not reason.strip():
        raise ValueError("Reviewer and reason must not be blank.")
    placeholders = ",".join("?" for _ in candidate_ids)
    with connection:
        # Acquire the writer lock before reading statuses used to authorize changes.
        connection.execute("UPDATE reference_candidates SET id=id WHERE 0")
        rows = list(
            connection.execute(
                f"""
            SELECT candidate.*, wins.artist_name, wins.song_title, wins.is_current
            FROM reference_candidates AS candidate
            JOIN wins USING (show_slug, win_date)
            WHERE candidate.id IN ({placeholders})
            """,
                candidate_ids,
            )
        )
        missing = set(candidate_ids) - {row["id"] for row in rows}
        if missing:
            raise ValueError(
                f"Candidate(s) not found: {', '.join(map(str, sorted(missing)))}."
            )
        for row in rows:
            if (
                decision != "withdrawn"
                and not revise
                and (row["review_status"] != "pending" or row["withdrawn"])
            ):
                raise ValueError(
                    f"Candidate {row['id']} was already reviewed; use --revise."
                )
            if decision == "approved" and not row["is_current"]:
                raise ValueError(f"Candidate {row['id']} has no current win.")
        for row in rows:
            previous = "withdrawn" if row["withdrawn"] else row["review_status"]
            connection.execute(
                """
                INSERT INTO candidate_review_events (
                    candidate_id, previous_status, decision, reviewer, reason,
                    reviewed_at, artist_name, song_title
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["id"],
                    previous,
                    decision,
                    reviewer.strip(),
                    reason.strip(),
                    timestamp,
                    row["artist_name"],
                    row["song_title"],
                ),
            )
            connection.execute(
                """UPDATE reference_candidates
                   SET review_status=?, withdrawn=?, updated_at=? WHERE id=?""",
                (
                    "rejected" if decision == "withdrawn" else decision,
                    int(decision == "withdrawn"),
                    timestamp,
                    row["id"],
                ),
            )
            if row["provider"] != "youtube":
                continue
            if decision == "approved":
                connection.execute(
                    """
                    INSERT INTO search_state (
                        show_slug, win_date, provider, status, attempt_count,
                        last_attempt_at, next_attempt_at, last_error, updated_at
                    ) VALUES (?, ?, 'youtube', 'matched', 0, ?, NULL, '', ?)
                    ON CONFLICT (show_slug, win_date, provider) DO UPDATE SET
                        status='matched', last_attempt_at=excluded.last_attempt_at,
                        next_attempt_at=NULL, last_error='',
                        updated_at=excluded.updated_at
                    """,
                    (row["show_slug"], row["win_date"], timestamp, timestamp),
                )
        for row in rows:
            if decision == "approved" or row["provider"] != "youtube":
                continue
            connection.execute(
                """
                UPDATE search_state SET status='pending', next_attempt_at=NULL,
                    last_error='', updated_at=?
                WHERE show_slug=? AND win_date=? AND provider='youtube'
                  AND status='matched'
                  AND NOT EXISTS (
                      SELECT 1 FROM reference_candidates
                      WHERE show_slug=? AND win_date=? AND provider='youtube'
                        AND review_status='approved' AND withdrawn=0
                  )
                """,
                (
                    timestamp,
                    row["show_slug"],
                    row["win_date"],
                    row["show_slug"],
                    row["win_date"],
                ),
            )
    return len(rows)
