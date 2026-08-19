from __future__ import annotations

import json
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
        parser.add_argument(
            "--format",
            choices=("text", "json"),
            default="text",
            help="Report format (default: text). JSON is written to stdout only.",
        )
        parser.add_argument(
            "--strict",
            action="store_true",
            help=(
                "Exit unsuccessfully when reconciliation work remains, including "
                "additions, conflicts, missing legacy wins or unapproved pages."
            ),
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
        if options["format"] == "json":
            self.stdout.write(json.dumps(summary.as_dict(), ensure_ascii=False))
        else:
            mode = "Dry run" if options["dry_run"] else "Sync"
            self.stdout.write(
                f"{mode}: {summary.pages_processed} pages, "
                f"{summary.wins_added} wins added, "
                f"{summary.conflicts_found} conflicts, "
                f"{summary.missing_legacy} missing legacy wins, "
                f"{summary.unapproved_pages} unapproved pages."
            )
            for report in summary.page_reports:
                details = (
                    f"{report.show}/{report.year}: {report.status}; "
                    f"page={report.page_title!r}; revision={report.revision or '-'}; "
                    f"source_rows={report.source_rows}; "
                    f"exact_matches={report.exact_matches}; "
                    f"additions={report.additions}; "
                    f"conflicts={report.conflicts}; "
                    f"missing_legacy={report.missing_legacy}"
                )
                if report.failure:
                    details += f"; failure={report.failure}"
                self.stdout.write(details)
                for candidate in report.addition_candidates:
                    self.stdout.write(
                        "  addition: "
                        f"{candidate['date']} | {candidate['artist']} | "
                        f"{candidate['song']}"
                    )
                for candidate in report.conflict_candidates:
                    existing = "; ".join(
                        f"{item['artist']} | {item['song']}"
                        for item in candidate["existing"]
                    )
                    self.stdout.write(
                        "  conflict: "
                        f"{candidate['date']} | incoming "
                        f"{candidate['incoming']['artist']} | "
                        f"{candidate['incoming']['song']} | existing {existing}"
                    )
                for candidate in report.missing_legacy_candidates:
                    self.stdout.write(
                        "  missing legacy: "
                        f"{candidate['date']} | {candidate['artist']} | "
                        f"{candidate['song']}"
                    )

        if summary.failures:
            raise CommandError(
                "Wikipedia source failures: " + " | ".join(summary.failures)
            )
        if options["strict"] and (
            summary.wins_added
            or summary.conflicts_found
            or summary.missing_legacy
            or summary.unapproved_pages
        ):
            raise CommandError(
                "Strict reconciliation failed: additions, conflicts or missing "
                "legacy wins remain."
            )
