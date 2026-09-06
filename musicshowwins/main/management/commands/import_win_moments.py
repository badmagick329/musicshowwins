import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from main.cache_invalidation import (
    CacheInvalidationError,
    invalidate_public_archive_cache,
)
from main.models import normalize_key
from main.moment_io import MomentDocumentError, import_moments


class Command(BaseCommand):
    help = "Validate and import win moments by portable event identity."

    def add_arguments(self, parser):
        parser.add_argument("path")
        parser.add_argument("--artist", action="append", dest="artists")
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--publish", action="store_true")

    def handle(self, *args, **options):
        try:
            document = json.loads(Path(options["path"]).read_text(encoding="utf-8"))
            artists = (
                {normalize_key(value) for value in options["artists"]}
                if options["artists"]
                else None
            )
            created, updated = import_moments(
                document,
                artists=artists,
                dry_run=options["dry_run"],
                publish=options["publish"],
            )
        except (
            OSError,
            UnicodeError,
            json.JSONDecodeError,
            MomentDocumentError,
        ) as exc:
            raise CommandError(str(exc)) from exc
        if not options["dry_run"] and (created or updated):
            try:
                invalidate_public_archive_cache()
            except CacheInvalidationError as exc:
                raise CommandError(str(exc)) from exc
        prefix = "Dry run: " if options["dry_run"] else ""
        self.stdout.write(f"{prefix}created {created}, updated {updated}.")
