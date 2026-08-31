from __future__ import annotations

import argparse
import sqlite3
import sys
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import TextIO

import requests

from .catalogue import CatalogueError, refresh_catalogue
from .config import ConfigurationError, load_config
from .database import (
    DatabaseError,
    due_searches,
    initialize_database,
    open_database,
)
from .manifest import ManifestError, approved_document, serialize_document, write_atomic


def _positive_integer(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer") from exc
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="kpopwins-operator")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("init", help="Initialize local operator state")
    subparsers.add_parser("refresh-wins", help="Refresh the public win catalogue")
    subparsers.add_parser("status", help="Show compact local state counts")
    due_parser = subparsers.add_parser("due", help="List searches currently due")
    due_parser.add_argument("--provider", required=True)
    due_parser.add_argument("--limit", type=_positive_integer, default=100)
    export_parser = subparsers.add_parser(
        "export-approved", help="Export approved reference candidates"
    )
    export_parser.add_argument("--output")
    return parser


def _status(connection: sqlite3.Connection, stdout: TextIO, now: str) -> None:
    win_counts = {
        bool(row["is_current"]): row["total"]
        for row in connection.execute(
            "SELECT is_current, COUNT(*) AS total FROM wins GROUP BY is_current"
        )
    }
    print(
        f"wins: current={win_counts.get(True, 0)} "
        f"non-current={win_counts.get(False, 0)}",
        file=stdout,
    )
    state_rows = list(
        connection.execute(
            """
            SELECT provider, status, COUNT(*) AS total
            FROM search_state
            GROUP BY provider, status
            ORDER BY provider, status
            """
        )
    )
    if state_rows:
        for row in state_rows:
            print(
                f"search {row['provider']}/{row['status']}: {row['total']}",
                file=stdout,
            )
    else:
        print("search states: none", file=stdout)
    candidate_rows = {
        row["review_status"]: row["total"]
        for row in connection.execute(
            """
            SELECT review_status, COUNT(*) AS total
            FROM reference_candidates
            GROUP BY review_status
            """
        )
    }
    print(
        "candidates: "
        f"pending={candidate_rows.get('pending', 0)} "
        f"approved={candidate_rows.get('approved', 0)} "
        f"rejected={candidate_rows.get('rejected', 0)}",
        file=stdout,
    )
    providers = [
        row["provider"]
        for row in connection.execute(
            "SELECT DISTINCT provider FROM search_state ORDER BY provider"
        )
    ]
    due_total = sum(
        len(due_searches(connection, provider, due_at=now, limit=None))
        for provider in providers
    )
    print(f"due searches: {due_total}", file=stdout)


def _due(
    connection: sqlite3.Connection,
    stdout: TextIO,
    provider: str,
    limit: int,
    now: str,
) -> None:
    normalized_provider = provider.strip().lower()
    if not normalized_provider:
        raise ValueError("Provider must not be empty.")
    rows = due_searches(connection, normalized_provider, due_at=now, limit=limit)
    print(
        "show_slug\twin_date\tartist_name\tsong_title\tstatus\t"
        "attempt_count\tnext_attempt_at",
        file=stdout,
    )
    for row in rows:
        print(
            "\t".join(
                (
                    row["show_slug"],
                    row["win_date"],
                    row["artist_name"],
                    row["song_title"],
                    row["search_status"],
                    str(row["attempt_count"]),
                    row["next_attempt_at"] or "-",
                )
            ),
            file=stdout,
        )


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def main(
    argv: Sequence[str] | None = None,
    *,
    environ: Mapping[str, str] | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
    session: requests.Session | None = None,
    now: str | None = None,
) -> int:
    output = stdout or sys.stdout
    errors = stderr or sys.stderr
    args = build_parser().parse_args(argv)
    try:
        config = load_config(environ)
        if args.command == "init":
            version = initialize_database(config)
            print(f"Operator home: {config.home}", file=output)
            print(f"Schema version: {version}", file=output)
            return 0

        connection = open_database(config)
        try:
            if args.command == "refresh-wins":
                counts = refresh_catalogue(
                    connection,
                    config.api_base_url,
                    session=session,
                    seen_at=now,
                )
                print(
                    f"fetched={counts.fetched} added={counts.added} "
                    f"updated={counts.updated} unchanged={counts.unchanged} "
                    f"no-longer-current={counts.no_longer_current}",
                    file=output,
                )
            elif args.command == "status":
                _status(connection, output, now or _now())
            elif args.command == "due":
                _due(connection, output, args.provider, args.limit, now or _now())
            elif args.command == "export-approved":
                content = serialize_document(approved_document(connection))
                if args.output == "-":
                    output.write(content)
                else:
                    destination = (
                        Path(args.output).expanduser().resolve()
                        if args.output
                        else config.default_manifest_path
                    )
                    write_atomic(destination, content)
                    print(f"Wrote approved manifest: {destination}", file=output)
        finally:
            connection.close()
        return 0
    except (
        CatalogueError,
        ConfigurationError,
        DatabaseError,
        ManifestError,
        OSError,
        sqlite3.Error,
        ValueError,
    ) as exc:
        print(f"error: {exc}", file=errors)
        return 1
