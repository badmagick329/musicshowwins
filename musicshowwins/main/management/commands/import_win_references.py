from __future__ import annotations

import json
import sys
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError

from main.win_reference_io import ReferenceDocumentError, import_document


class Command(BaseCommand):
    help = "Import versioned external references for existing wins."

    def add_arguments(self, parser):
        parser.add_argument("path", help="JSON file path, or - to read stdin")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        path = options["path"]
        try:
            source = (
                sys.stdin.read()
                if path == "-"
                else Path(path).read_text(encoding="utf-8")
            )
        except (OSError, UnicodeError) as exc:
            raise CommandError("Could not read the input document.") from exc
        try:
            document = json.loads(source)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise CommandError("Invalid JSON input.") from exc

        try:
            created, updated, unchanged = import_document(
                document, dry_run=options["dry_run"]
            )
        except ReferenceDocumentError as exc:
            raise CommandError(str(exc)) from exc
        except DatabaseError as exc:
            raise CommandError("The reference import could not be saved.") from exc

        prefix = "Dry run: " if options["dry_run"] else ""
        self.stdout.write(
            f"{prefix}created {created}, updated {updated}, unchanged {unchanged}."
        )
