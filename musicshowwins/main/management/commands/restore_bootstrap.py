from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from main.models import (
    Artist,
    ArtistAlias,
    ImportIssue,
    ImportRun,
    MusicShow,
    Song,
    SourcePage,
    Win,
    normalize_key,
    normalize_text,
)

EXPECTED_COUNTS = {"shows": 6, "artists": 296, "songs": 901, "wins": 2965}
MIN_DATE = date(2014, 1, 1)
MAX_DATE = date(2025, 8, 12)


class Command(BaseCommand):
    help = "Restore the versioned legacy domain dataset into an empty database."

    def add_arguments(self, parser):
        parser.add_argument(
            "--input",
            type=Path,
            default=Path(__file__).resolve().parents[2] / "data" / "bootstrap.json",
            help="Bootstrap JSON file (defaults to the tracked dataset).",
        )

    def handle(self, *args, **options):
        payload = self._load(options["input"])
        self._validate_payload(payload)
        self._refuse_nonempty_tables()

        with transaction.atomic():
            shows = {
                row["slug"]: MusicShow.objects.create(
                    slug=row["slug"], name=row["name"], active=row.get("active", True)
                )
                for row in payload["shows"]
            }
            artists = {
                row["name"]: Artist.objects.create(
                    name=row["name"], identity_key=normalize_key(row["name"])
                )
                for row in payload["artists"]
            }
            songs = {}
            for row in payload["songs"]:
                songs[(row["artist"], normalize_key(row["title"]))] = (
                    Song.objects.create(
                        artist=artists[row["artist"]],
                        title=row["title"],
                        normalized_title=normalize_key(row["title"]),
                    )
                )
            ArtistAlias.objects.bulk_create(
                [
                    ArtistAlias(
                        alias=row["alias"],
                        normalized_name=normalize_key(row["alias"]),
                        artist=artists[row["artist"]],
                    )
                    for row in payload["aliases"]
                ]
            )
            Win.objects.bulk_create(
                [
                    Win(
                        show=shows[row["show"]],
                        song=songs[(row["artist"], normalize_key(row["title"]))],
                        date=date.fromisoformat(row["date"]),
                        source_type=Win.SourceType.LEGACY,
                        source_revision=None,
                    )
                    for row in payload["wins"]
                ],
                batch_size=500,
            )

        self.stdout.write(
            self.style.SUCCESS(
                "Restored 6 shows, 296 artists, 901 songs and 2,965 wins."
            )
        )

    @staticmethod
    def _load(path: Path) -> dict:
        try:
            with path.open(encoding="utf-8") as file:
                payload = json.load(file)
        except (OSError, json.JSONDecodeError) as exc:
            raise CommandError(f"Unable to read bootstrap data: {path}: {exc}") from exc
        if not isinstance(payload, dict):
            raise CommandError("Bootstrap data must be a JSON object")
        return payload

    def _validate_payload(self, payload: dict) -> None:
        if payload.get("version") != 1:
            raise CommandError("Unsupported bootstrap data version")
        for key, expected in EXPECTED_COUNTS.items():
            actual = payload.get(key)
            if not isinstance(actual, list) or len(actual) != expected:
                actual_count = len(actual) if isinstance(actual, list) else "invalid"
                raise CommandError(f"Expected {expected} {key}; got {actual_count}")

        show_slugs = [row.get("slug") for row in payload["shows"]]
        if any(
            not isinstance(row.get("slug"), str)
            or not normalize_text(row.get("name", ""))
            for row in payload["shows"]
        ):
            raise CommandError("Every show must have a slug and display name")
        if len(set(show_slugs)) != len(show_slugs):
            raise CommandError("Bootstrap contains duplicate show slugs")
        show_set = set(show_slugs)

        artist_names = [row.get("name") for row in payload["artists"]]
        if any(
            not isinstance(name, str) or not normalize_text(name)
            for name in artist_names
        ):
            raise CommandError("Every artist must have a nonempty name")
        artist_keys = [normalize_key(name) for name in artist_names]
        if len(set(artist_keys)) != len(artist_keys):
            raise CommandError("Bootstrap contains duplicate artist identities")
        artist_set = set(artist_names)

        song_keys = []
        for row in payload["songs"]:
            if (
                row.get("artist") not in artist_set
                or not isinstance(row.get("title"), str)
                or not normalize_text(row["title"])
            ):
                raise CommandError(f"Invalid song row: {row!r}")
            song_keys.append((row["artist"], normalize_key(row["title"])))
        if len(set(song_keys)) != len(song_keys):
            raise CommandError("Bootstrap contains duplicate artist/song pairs")
        song_set = set(song_keys)

        aliases = payload.get("aliases", [])
        alias_keys = []
        for row in aliases:
            if (
                row.get("artist") not in artist_set
                or not isinstance(row.get("alias"), str)
                or not normalize_text(row["alias"])
            ):
                raise CommandError(f"Invalid artist alias row: {row!r}")
            alias_keys.append(normalize_key(row["alias"]))
        if set(alias_keys) != {"bigbang", "akdong musician"} or len(alias_keys) != 2:
            raise CommandError(
                "Bootstrap aliases must contain only BigBang and Akdong Musician"
            )
        if any(row.get("alias") == "Blackpink and Selena Gomez" for row in aliases):
            raise CommandError(
                "The collaboration-collapsing BLACKPINK alias is not allowed"
            )

        win_keys = []
        for row in payload["wins"]:
            key = (row.get("artist"), normalize_key(row.get("title", "")))
            if row.get("show") not in show_set or key not in song_set:
                raise CommandError(f"Invalid win reference: {row!r}")
            try:
                win_date = date.fromisoformat(row["date"])
            except (KeyError, TypeError, ValueError) as exc:
                raise CommandError(f"Invalid win date: {row!r}") from exc
            if not MIN_DATE <= win_date <= MAX_DATE:
                raise CommandError(f"Win date outside supported history: {row!r}")
            exact_key = (row["show"], win_date, *key)
            if exact_key in win_keys:
                raise CommandError(f"Duplicate win: {row!r}")
            win_keys.append(exact_key)

    @staticmethod
    def _refuse_nonempty_tables() -> None:
        domain_models = (
            MusicShow,
            Artist,
            ArtistAlias,
            Song,
            Win,
            SourcePage,
            ImportRun,
            ImportIssue,
        )
        occupied = [
            str(model._meta.verbose_name_plural)
            for model in domain_models
            if model.objects.exists()
        ]
        if occupied:
            raise CommandError(
                "Bootstrap restore requires empty domain tables; populated: "
                + ", ".join(occupied)
            )
