from __future__ import annotations

import json
import sys
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError

from main.cache_invalidation import (
    CacheInvalidationError,
    CacheInvalidationUnavailable,
    invalidate_public_archive_cache,
)
from main.win_presence_io import PresenceDocumentError, import_presence


class Command(BaseCommand):
    help = "Record whether each winner performed on the winning broadcast."

    def add_arguments(self, parser):
        parser.add_argument("path", help="JSON file path, or - to read stdin")
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument(
            "--require-cache-refresh",
            action="store_true",
            help="Fail if the frontend cache cannot be refreshed.",
        )

    def handle(self, *args, **options):
        path = options["path"]
        try:
            source = (
                sys.stdin.read()
                if path == "-"
                else Path(path).read_text(encoding="utf-8")
            )
            document = json.loads(source)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise CommandError("Could not read a JSON presence document.") from exc
        try:
            summary = import_presence(document, dry_run=options["dry_run"])
        except PresenceDocumentError as exc:
            raise CommandError(str(exc)) from exc
        except DatabaseError as exc:
            raise CommandError("The presence import could not be saved.") from exc

        if summary.updated and not options["dry_run"]:
            try:
                invalidate_public_archive_cache()
            except CacheInvalidationError as exc:
                if options["require_cache_refresh"]:
                    raise CommandError(str(exc)) from exc
                reason = (
                    "the frontend is unavailable"
                    if isinstance(exc, CacheInvalidationUnavailable)
                    else str(exc)
                )
                self.stderr.write(
                    self.style.WARNING(
                        f"Presence imported; cache not refreshed: {reason}"
                    )
                )

        prefix = "Dry run: " if options["dry_run"] else ""
        self.stdout.write(
            f"{prefix}updated {summary.updated}, unchanged {summary.unchanged}, "
            f"missing wins {summary.missing}."
        )
