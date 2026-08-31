from pathlib import Path

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from main.bootstrap import CleanupError, apply_cleanup
from main.management.commands.restore_bootstrap import Command as RestoreCommand
from main.models import Artist, ArtistAlias, MusicShow, Song, Win, normalize_key

BOOTSTRAP_PATH = Path(__file__).resolve().parents[2] / "data" / "bootstrap.json"
ARCHIVE_MODELS = (MusicShow, Artist, ArtistAlias, Song, Win)


class Command(BaseCommand):
    help = "Restore an empty archive or verify that it contains the known baseline."

    def handle(self, *args, **options):
        if self._archive_is_empty():
            call_command("restore_bootstrap", stdout=self.stdout, stderr=self.stderr)
            return

        payload = self._baseline_payload()
        problems = self._baseline_problems(payload)
        if problems:
            raise CommandError(
                "Archive data exists but the complete bootstrap baseline is missing: "
                + "; ".join(problems)
            )
        self.stdout.write(self.style.SUCCESS("Bootstrap baseline is already present."))

    @staticmethod
    def _archive_is_empty() -> bool:
        return not any(model.objects.exists() for model in ARCHIVE_MODELS)

    @staticmethod
    def _baseline_payload() -> dict:
        restore = RestoreCommand()
        payload = restore._load(BOOTSTRAP_PATH)
        try:
            payload, _issues = apply_cleanup(payload)
        except CleanupError as exc:
            raise CommandError(str(exc)) from exc
        restore._validate_payload(payload)
        return payload

    @staticmethod
    def _baseline_problems(payload: dict) -> list[str]:
        problems = []
        required_shows = {row["slug"] for row in payload["shows"]}
        present_shows = set(MusicShow.objects.values_list("slug", flat=True))
        if missing := sorted(required_shows - present_shows):
            problems.append("required shows: " + ", ".join(missing))

        required_artists = {normalize_key(row["name"]) for row in payload["artists"]}
        present_artists = set(Artist.objects.values_list("identity_key", flat=True))
        missing_artists = required_artists - present_artists
        if missing_artists:
            problems.append(f"{len(missing_artists)} required artists")

        required_songs = {
            (normalize_key(row["artist"]), normalize_key(row["title"]))
            for row in payload["songs"]
        }
        present_songs = set(
            Song.objects.values_list("artist__identity_key", "normalized_title")
        )
        missing_songs = required_songs - present_songs
        if missing_songs:
            problems.append(f"{len(missing_songs)} required songs")

        required_wins = {
            (
                row["show"],
                row["date"],
                normalize_key(row["artist"]),
                normalize_key(row["title"]),
            )
            for row in payload["wins"]
        }
        present_wins = {
            (show, win_date.isoformat(), artist, title)
            for show, win_date, artist, title in Win.objects.values_list(
                "show__slug",
                "date",
                "song__artist__identity_key",
                "song__normalized_title",
            )
        }
        missing_wins = required_wins - present_wins
        if missing_wins:
            problems.append(f"{len(missing_wins)} required dated wins")

        required_aliases = {
            (normalize_key(row["alias"]), normalize_key(row["artist"]))
            for row in payload["aliases"]
        }
        present_aliases = set(
            ArtistAlias.objects.values_list("normalized_name", "artist__identity_key")
        )
        missing_aliases = required_aliases - present_aliases
        if missing_aliases:
            problems.append(f"{len(missing_aliases)} configured aliases")
        return problems
