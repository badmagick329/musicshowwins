import json

from django.core.management.base import BaseCommand

from main.win_reference_io import export_document


class Command(BaseCommand):
    help = "Export all win references as version-1 JSON."

    def handle(self, *args, **options):
        self.stdout.write(
            json.dumps(
                export_document(),
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )
