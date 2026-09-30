import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from main.cache_invalidation import (
    CacheInvalidationError,
    invalidate_public_archive_cache,
)
from main.debut_io import DebutDocumentError, import_debuts


class Command(BaseCommand):
    help = "Make artist debut dates match the reviewed debuts file."

    def add_arguments(self, parser):
        parser.add_argument("path")
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--skip-cache-revalidation", action="store_true")

    def handle(self, *args, **options):
        try:
            document = json.loads(Path(options["path"]).read_text(encoding="utf-8"))
            changed = import_debuts(document, dry_run=options["dry_run"])
        except (OSError, UnicodeError, json.JSONDecodeError, DebutDocumentError) as exc:
            raise CommandError(str(exc)) from exc
        if (
            not options["dry_run"]
            and not options["skip_cache_revalidation"]
            and changed
        ):
            try:
                invalidate_public_archive_cache()
            except CacheInvalidationError as exc:
                raise CommandError(str(exc)) from exc
        prefix = "Dry run: " if options["dry_run"] else ""
        self.stdout.write(f"{prefix}changed {changed}.")
