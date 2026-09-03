from __future__ import annotations

import argparse
import sqlite3
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import TextIO

import requests

from .candidate_review import list_candidates, review_candidates, show_candidate
from .catalogue import CatalogueError, refresh_catalogue
from .channel_verification import apply_verified_channels, verify_channels
from .config import ConfigurationError, load_config
from .database import (
    DatabaseError,
    due_searches,
    initialize_database,
    open_database,
)
from .ingestion import ingest_channels
from .manifest import ManifestError, approved_document, serialize_document, write_atomic
from .matching import match_videos
from .reddit import RedditError, run_reddit_audit
from .reddit_hydration import (
    RedditHydrationError,
    hydrate_youtube_ids,
    load_reddit_youtube_ids,
)
from .registry import SUPPORTED_SHOWS, RegistryError, load_registry
from .youtube import YouTubeClient, YouTubeError


def _configure_utf8(stream: TextIO) -> None:
    reconfigure = getattr(stream, "reconfigure", None)
    if not callable(reconfigure):
        return
    try:
        reconfigure(encoding="utf-8", errors="strict")
    except (AttributeError, OSError, TypeError, ValueError):
        # In-memory and custom injected streams may not be reconfigurable.
        return


def _positive_integer(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer") from exc
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return parsed


def _nonnegative_integer(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer") from exc
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be at least 0")
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

    youtube_parser = subparsers.add_parser(
        "youtube", help="Use official YouTube channels"
    )
    youtube_commands = youtube_parser.add_subparsers(
        dest="youtube_command", required=True
    )
    verify_parser = youtube_commands.add_parser(
        "verify-channels", help="Resolve configured official channel handles"
    )
    verify_parser.add_argument("--apply", action="store_true")
    verify_parser.add_argument("--handle")
    ingest_parser = youtube_commands.add_parser(
        "ingest", help="Ingest official channel upload playlists"
    )
    ingest_parser.add_argument("--handle")
    ingest_parser.add_argument("--max-pages", type=_positive_integer, default=10)
    ingest_parser.add_argument("--restart", action="store_true")
    match_parser = youtube_commands.add_parser(
        "match", help="Match local official videos to wins"
    )
    match_parser.add_argument("--show")
    match_parser.add_argument("--min-score", type=_nonnegative_integer, default=75)
    match_parser.add_argument("--limit", type=_positive_integer)
    match_parser.add_argument("--dry-run", action="store_true")

    candidates_parser = subparsers.add_parser(
        "candidates", help="Review local reference candidates"
    )
    candidate_commands = candidates_parser.add_subparsers(
        dest="candidate_command", required=True
    )
    reddit_parser = subparsers.add_parser("reddit", help="Read-only r/kpop wiki audit")
    reddit_commands = reddit_parser.add_subparsers(dest="reddit_command", required=True)
    audit_parser = reddit_commands.add_parser(
        "audit", help="Audit r/kpop wiki episode winners without changing state"
    )
    audit_parser.add_argument("--show", choices=sorted(SUPPORTED_SHOWS))
    audit_parser.add_argument("--max-pages", type=_positive_integer, default=100)
    audit_parser.add_argument("--refresh-indexes", action="store_true")
    audit_parser.add_argument("--output")
    hydrate_parser = reddit_commands.add_parser(
        "hydrate-youtube", help="Fetch metadata for unverified YouTube audit links"
    )
    hydrate_parser.add_argument("--input")
    hydrate_parser.add_argument("--limit", type=_positive_integer)
    hydrate_parser.add_argument("--retry-unavailable", action="store_true")
    list_parser = candidate_commands.add_parser("list")
    list_parser.add_argument(
        "--status", choices=("pending", "approved", "rejected"), default="pending"
    )
    list_parser.add_argument("--show")
    list_parser.add_argument("--provider")
    list_parser.add_argument("--min-score", type=_nonnegative_integer)
    list_parser.add_argument("--limit", type=_positive_integer, default=100)
    show_parser = candidate_commands.add_parser("show")
    show_parser.add_argument("id", type=_positive_integer)
    approve_parser = candidate_commands.add_parser("approve")
    approve_parser.add_argument("ids", nargs="+", type=_positive_integer)
    reject_parser = candidate_commands.add_parser("reject")
    reject_parser.add_argument("ids", nargs="+", type=_positive_integer)
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


def _fixed_clock(instant: datetime) -> Callable[[], datetime]:
    def clock() -> datetime:
        return instant

    return clock


def main(
    argv: Sequence[str] | None = None,
    *,
    environ: Mapping[str, str] | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
    session: requests.Session | None = None,
    now: str | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> int:
    output = stdout if stdout is not None else sys.stdout
    errors = stderr if stderr is not None else sys.stderr
    _configure_utf8(output)
    _configure_utf8(errors)
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
            elif args.command == "youtube":
                registry = load_registry(config.channel_registry_path)
                timestamp = now or _now()
                if args.youtube_command in {"verify-channels", "ingest"}:
                    client_clock = None
                    if now:
                        instant = datetime.fromisoformat(now.replace("Z", "+00:00"))
                        client_clock = _fixed_clock(instant)
                    client = YouTubeClient(
                        config,
                        connection,
                        session=session,
                        clock=client_clock,
                        sleep=sleep,
                    )
                if args.youtube_command == "verify-channels":
                    verified = verify_channels(registry, client, handle=args.handle)
                    for result in verified:
                        print(
                            f"{result.entry.show_slug}\t{result.entry.handle}\t"
                            f"{result.resolved.title}\t{result.resolved.channel_id}\t"
                            f"{result.resolved.uploads_playlist_id}",
                            file=output,
                        )
                    if args.apply:
                        apply_verified_channels(
                            connection,
                            verified,
                            verified_at=timestamp,
                            full_registry=args.handle is None,
                        )
                        print(
                            f"Applied {len(verified)} channel mapping(s).", file=output
                        )
                    else:
                        print(
                            "No channel mappings changed; use --apply to save.",
                            file=output,
                        )
                elif args.youtube_command == "ingest":
                    counts = ingest_channels(
                        connection,
                        client,
                        handle=args.handle,
                        max_pages=args.max_pages,
                        restart=args.restart,
                        timestamp=timestamp,
                    )
                    print(
                        f"channels={counts.channels} pages={counts.pages} "
                        f"discovered={counts.discovered} added={counts.added} "
                        f"updated={counts.updated} unavailable={counts.unavailable} "
                        f"api-calls={client.calls_used} "
                        f"more-remaining={'yes' if counts.more_remaining else 'no'}",
                        file=output,
                    )
                elif args.youtube_command == "match":
                    counts = match_videos(
                        connection,
                        registry,
                        show=args.show,
                        min_score=args.min_score,
                        limit=args.limit,
                        dry_run=args.dry_run,
                        timestamp=timestamp,
                    )
                    print(
                        f"considered={counts.considered} accepted={counts.accepted} "
                        f"created={counts.created} updated={counts.updated} "
                        f"dry-run={'yes' if args.dry_run else 'no'}",
                        file=output,
                    )
            elif args.command == "reddit":
                if args.reddit_command == "audit":
                    run_reddit_audit(
                        connection,
                        config,
                        show=args.show,
                        max_pages=args.max_pages,
                        refresh_indexes=args.refresh_indexes,
                        output_path=(
                            Path(args.output).expanduser().resolve()
                            if args.output
                            else None
                        ),
                        stdout=output,
                        session=session,
                        sleep=sleep,
                        now=now,
                    )
                elif args.reddit_command == "hydrate-youtube":
                    input_path = (
                        Path(args.input).expanduser().resolve()
                        if args.input
                        else config.default_reddit_audit_path
                    )
                    video_ids = load_reddit_youtube_ids(input_path)
                    client_clock = None
                    if now:
                        instant = datetime.fromisoformat(now.replace("Z", "+00:00"))
                        client_clock = _fixed_clock(instant)
                    client = YouTubeClient(
                        config,
                        connection,
                        session=session,
                        clock=client_clock,
                        sleep=sleep,
                    )
                    counts = hydrate_youtube_ids(
                        connection,
                        client,
                        video_ids,
                        limit=args.limit,
                        retry_unavailable=args.retry_unavailable,
                        timestamp=now or _now(),
                    )
                    print(
                        f"considered={counts.considered} queried={counts.queried} "
                        f"batches={counts.batches} added={counts.added} "
                        f"updated={counts.updated} "
                        f"unavailable={counts.unavailable} skipped={counts.skipped} "
                        f"api-calls={client.calls_used} "
                        f"more-remaining={'yes' if counts.more_remaining else 'no'}",
                        file=output,
                    )
            elif args.command == "candidates":
                timestamp = now or _now()
                if args.candidate_command == "list":
                    list_candidates(
                        connection,
                        output,
                        status=args.status,
                        show=args.show,
                        provider=args.provider,
                        minimum_score=args.min_score,
                        limit=args.limit,
                    )
                elif args.candidate_command == "show":
                    show_candidate(connection, output, args.id)
                else:
                    decision = (
                        "approved"
                        if args.candidate_command == "approve"
                        else "rejected"
                    )
                    total = review_candidates(
                        connection, args.ids, decision=decision, timestamp=timestamp
                    )
                    print(f"{decision}: {total} candidate(s)", file=output)
        finally:
            connection.close()
        return 0
    except (
        CatalogueError,
        ConfigurationError,
        DatabaseError,
        ManifestError,
        RegistryError,
        RedditError,
        RedditHydrationError,
        YouTubeError,
        OSError,
        sqlite3.Error,
        ValueError,
    ) as exc:
        print(f"error: {exc}", file=errors)
        return 1
