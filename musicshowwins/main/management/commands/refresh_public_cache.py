from django.core.management.base import BaseCommand

from main.cache_invalidation import (
    CacheInvalidationError,
    invalidate_public_archive_cache,
)


class Command(BaseCommand):
    help = "Refresh the frontend archive cache without blocking deployment."

    def handle(self, *args, **options):
        try:
            invalidate_public_archive_cache()
        except CacheInvalidationError as exc:
            self.stderr.write(self.style.WARNING(f"Cache refresh failed: {exc}"))
            return
        self.stdout.write(self.style.SUCCESS("Public cache refreshed."))
