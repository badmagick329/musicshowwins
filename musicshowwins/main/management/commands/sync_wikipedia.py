from __future__ import annotations

from datetime import date

from django.core.management.base import BaseCommand, CommandError

from main.models import MusicShow
from main.wikipedia import MIN_YEAR, WikipediaImporter


class Command(BaseCommand):
    help = "Synchronize music show wins from revisioned Wikipedia pages."

    def add_arguments(self, parser):
        parser.add_argument(
            "--year",
            dest="years",
            action="append",
            type=int,
            help=(
                "Year to synchronize; repeat for multiple years "
                "(default: current and previous)."
            ),
        )
        parser.add_argument(
            "--show",
            dest="shows",
            action="append",
            help=(
                "Active show slug to synchronize; repeat for multiple shows "
                "(default: all active shows)."
            ),
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Fetch and validate pages without writing any database records.",
        )

    def handle(self, *args, **options):
        years = options.get("years")
        if not years:
            current_year = date.today().year
            years = [current_year - 1, current_year]
        years = sorted(set(years))
        if any(year < MIN_YEAR for year in years):
            raise CommandError(f"Years before {MIN_YEAR} are not supported")

        active_slugs = set(
            MusicShow.objects.filter(active=True).values_list("slug", flat=True)
        )
        explicit_shows = options.get("shows")
        shows = explicit_shows or sorted(active_slugs)
        shows = sorted(set(shows))
        available_slugs = set(MusicShow.objects.values_list("slug", flat=True))
        unknown = sorted(set(shows) - available_slugs)
        if unknown:
            raise CommandError("Unknown show slug(s): " + ", ".join(unknown))

        summary = WikipediaImporter().sync(
            shows=shows,
            years=years,
            dry_run=options["dry_run"],
        )
        mode = "Dry run" if options["dry_run"] else "Sync"
        self.stdout.write(
            f"{mode}: {summary.pages_processed} pages, "
            f"{summary.wins_added} wins added, "
            f"{summary.conflicts_found} conflicts."
        )
        if summary.failures:
            for failure in summary.failures:
                self.stdout.write(self.style.WARNING(failure))
