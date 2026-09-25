from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from main.cache_invalidation import (
    CacheInvalidationError,
    invalidate_public_archive_cache,
)
from main.youtube_availability import (
    YouTubeAvailabilityError,
    check_youtube_references,
)


class Command(BaseCommand):
    help = "Hide unwatchable YouTube references and restore ones that return."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        if not settings.YOUTUBE_API_KEY:
            raise CommandError("YOUTUBE_API_KEY is not configured.")
        try:
            summary = check_youtube_references(
                settings.YOUTUBE_API_KEY, dry_run=options["dry_run"]
            )
        except YouTubeAvailabilityError as exc:
            raise CommandError(str(exc)) from exc
        if summary.changed and not options["dry_run"]:
            try:
                invalidate_public_archive_cache()
            except CacheInvalidationError as exc:
                raise CommandError(str(exc)) from exc
        mode = "Dry run" if options["dry_run"] else "Check"
        self.stdout.write(
            f"{mode}: {summary.checked} references checked, "
            f"{summary.became_unavailable} became unavailable, "
            f"{summary.restored} restored."
        )
