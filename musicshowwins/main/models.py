from __future__ import annotations

import re
import unicodedata

from django.db import models


def normalize_text(value: str) -> str:
    """Normalize display text without changing the credited name itself."""
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", value or "")).strip()


def normalize_key(value: str) -> str:
    return normalize_text(value).casefold()


class MusicShow(models.Model):
    slug = models.SlugField(max_length=80, unique=True)
    name = models.CharField(max_length=100)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ("name",)

    def save(self, *args, **kwargs):
        self.slug = normalize_key(self.slug).replace(" ", "-")
        self.name = normalize_text(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Artist(models.Model):
    name = models.CharField(max_length=200)
    identity_key = models.CharField(max_length=200, unique=True, editable=False)

    class Meta:
        ordering = ("name",)

    def save(self, *args, **kwargs):
        self.name = normalize_text(self.name)
        self.identity_key = normalize_key(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class ArtistAlias(models.Model):
    alias = models.CharField(max_length=200)
    normalized_name = models.CharField(max_length=200, editable=False)
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE, related_name="aliases")

    class Meta:
        ordering = ("alias",)
        constraints = [
            models.UniqueConstraint(
                fields=("normalized_name",), name="unique_artist_alias_normalized_name"
            ),
        ]

    def save(self, *args, **kwargs):
        self.alias = normalize_text(self.alias)
        self.normalized_name = normalize_key(self.alias)
        super().save(*args, **kwargs)

    @property
    def name(self) -> str:
        return self.alias

    def __str__(self):
        return f"{self.alias} → {self.artist.name}"


class Song(models.Model):
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE, related_name="songs")
    title = models.CharField(max_length=300)
    normalized_title = models.CharField(max_length=300, editable=False)

    class Meta:
        ordering = ("title", "artist__name")
        constraints = [
            models.UniqueConstraint(
                fields=("artist", "normalized_title"),
                name="unique_song_artist_normalized_title",
            ),
        ]

    def save(self, *args, **kwargs):
        self.title = normalize_text(self.title)
        self.normalized_title = normalize_key(self.title)
        super().save(*args, **kwargs)

    @property
    def name(self) -> str:
        return self.title

    def __str__(self):
        return f"{self.artist.name} - {self.title}"


class Win(models.Model):
    class SourceType(models.TextChoices):
        LEGACY = "legacy", "Legacy bootstrap"
        WIKIPEDIA = "wikipedia", "Wikipedia"

    show = models.ForeignKey(MusicShow, on_delete=models.CASCADE, related_name="wins")
    song = models.ForeignKey(Song, on_delete=models.CASCADE, related_name="wins")
    date = models.DateField()
    source_type = models.CharField(
        max_length=20, choices=SourceType.choices, default=SourceType.LEGACY
    )
    source_page = models.ForeignKey(
        "SourcePage",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="wins",
    )
    source_revision = models.CharField(max_length=80, blank=True, null=True)

    class Meta:
        ordering = ("-date", "show__name", "song__title")
        constraints = [
            models.UniqueConstraint(
                fields=("show", "song", "date"), name="unique_win_show_song_date"
            )
        ]
        indexes = [
            models.Index(fields=("date",), name="main_win_date_045318_idx"),
            models.Index(fields=("show", "date"), name="main_win_show_id_8a27fa_idx"),
        ]

    def __str__(self):
        return f"{self.show.name} - {self.song} - {self.date}"


class SourcePage(models.Model):
    show = models.ForeignKey(
        MusicShow, on_delete=models.CASCADE, related_name="source_pages"
    )
    year = models.PositiveSmallIntegerField()
    page_title = models.CharField(max_length=255)
    latest_revision = models.CharField(max_length=80, blank=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-year", "show__name")
        constraints = [
            models.UniqueConstraint(
                fields=("show", "year"), name="unique_source_page_show_year"
            )
        ]

    def __str__(self):
        return f"{self.show.name} ({self.year})"


class ImportRun(models.Model):
    class Status(models.TextChoices):
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.RUNNING
    )
    requested_shows = models.JSONField(default=list)
    requested_years = models.JSONField(default=list)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    wins_added = models.PositiveIntegerField(default=0)
    conflicts_found = models.PositiveIntegerField(default=0)
    pages_processed = models.PositiveIntegerField(default=0)
    failure_summary = models.TextField(blank=True)

    class Meta:
        ordering = ("-started_at",)

    def __str__(self):
        return f"Import {self.pk} ({self.status})"


class ImportIssue(models.Model):
    class IssueType(models.TextChoices):
        CONFLICT = "conflict", "Winner conflict"
        INVALID_SOURCE = "invalid_source", "Invalid source"
        MISSING_WIN = "missing_win", "Missing historical win"
        FETCH_ERROR = "fetch_error", "Fetch error"

    class Resolution(models.TextChoices):
        OPEN = "open", "Open"
        ACCEPTED = "accepted", "Accepted"
        REJECTED = "rejected", "Rejected"

    import_run = models.ForeignKey(
        ImportRun,
        on_delete=models.CASCADE,
        related_name="issues",
        null=True,
        blank=True,
    )
    source_page = models.ForeignKey(
        SourcePage,
        on_delete=models.CASCADE,
        related_name="issues",
        null=True,
        blank=True,
    )
    issue_type = models.CharField(max_length=30, choices=IssueType.choices)
    candidate = models.JSONField(default=dict)
    resolution = models.CharField(
        max_length=20, choices=Resolution.choices, default=Resolution.OPEN
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.get_issue_type_display()} ({self.resolution})"
