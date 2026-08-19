from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from main.models import MusicShow, SourceApproval


class Command(BaseCommand):
    help = "Approve a Wikipedia show/year source for real sync writes."

    def add_arguments(self, parser):
        parser.add_argument("--show", required=True, help="Music show slug.")
        parser.add_argument(
            "--year", required=True, type=int, help="Calendar year to approve."
        )
        parser.add_argument(
            "--by", default="local-admin", help="Optional approval label."
        )
        parser.add_argument("--notes", default="", help="Optional approval notes.")
        parser.add_argument(
            "--revoke",
            action="store_true",
            help="Revoke approval without deleting the approval record.",
        )

    def handle(self, *args, **options):
        year = options["year"]
        if year < 2014:
            raise CommandError("Years before 2014 are not supported")
        try:
            show = MusicShow.objects.get(slug=options["show"])
        except MusicShow.DoesNotExist as exc:
            raise CommandError(f"Unknown show slug: {options['show']}") from exc

        approval, _ = SourceApproval.objects.get_or_create(show=show, year=year)
        approval.approved = not options["revoke"]
        approval.approved_at = timezone.now() if approval.approved else None
        approval.approved_by = options["by"] if approval.approved else ""
        approval.notes = options["notes"]
        approval.save(update_fields=("approved", "approved_at", "approved_by", "notes"))
        status = "Approved" if approval.approved else "Revoked"
        self.stdout.write(f"{status} Wikipedia source: {show.slug}/{year}")
