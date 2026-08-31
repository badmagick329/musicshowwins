from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html, format_html_join

from main.models import (
    Artist,
    ArtistAlias,
    ImportIssue,
    ImportRun,
    MusicShow,
    Song,
    SourceApproval,
    SourcePage,
    Win,
    WinReference,
)


@admin.register(MusicShow)
class MusicShowAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "active")
    list_filter = ("active",)
    search_fields = ("name", "slug")


@admin.register(Artist)
class ArtistAdmin(admin.ModelAdmin):
    list_display = ("name", "identity_key")
    search_fields = ("name", "identity_key")


@admin.register(ArtistAlias)
class ArtistAliasAdmin(admin.ModelAdmin):
    list_display = ("alias", "artist", "normalized_name")
    search_fields = ("alias", "normalized_name", "artist__name")


@admin.register(Song)
class SongAdmin(admin.ModelAdmin):
    list_display = ("title", "artist", "normalized_title")
    list_filter = ("artist",)
    search_fields = ("title", "normalized_title", "artist__name")


class WinReferenceInline(admin.TabularInline):
    model = WinReference
    extra = 0
    fields = (
        "reference_type",
        "provider",
        "external_id",
        "url",
        "title",
        "is_official",
        "status",
        "published_at",
        "last_verified_at",
    )


@admin.register(Win)
class WinAdmin(admin.ModelAdmin):
    list_display = (
        "date",
        "show",
        "song",
        "source_type",
        "source_page",
        "source_revision",
    )
    list_filter = ("show", "source_type", "date")
    search_fields = ("show__name", "song__title", "song__artist__name")
    date_hierarchy = "date"
    inlines = (WinReferenceInline,)


@admin.register(WinReference)
class WinReferenceAdmin(admin.ModelAdmin):
    list_display = (
        "win_date",
        "music_show",
        "artist",
        "song",
        "reference_type",
        "provider",
        "title_or_url",
        "publisher_name",
        "is_official",
        "status",
        "last_verified_at",
    )
    list_filter = (
        "reference_type",
        "provider",
        "is_official",
        "status",
        "win__show",
        "win__date",
    )
    search_fields = (
        "win__song__artist__name",
        "win__song__title",
        "title",
        "url",
        "external_id",
        "publisher_name",
        "publisher_external_id",
    )
    autocomplete_fields = ("win",)
    readonly_fields = ("discovered_at", "created_at", "updated_at")

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("win__show", "win__song__artist")
        )

    @admin.display(description="Win date", ordering="win__date")
    def win_date(self, obj):
        return obj.win.date

    @admin.display(description="Music show", ordering="win__show__name")
    def music_show(self, obj):
        return obj.win.show.name

    @admin.display(ordering="win__song__artist__name")
    def artist(self, obj):
        return obj.win.song.artist.name

    @admin.display(ordering="win__song__title")
    def song(self, obj):
        return obj.win.song.title

    @admin.display(description="Title or URL", ordering="title")
    def title_or_url(self, obj):
        return obj.title or obj.url


@admin.register(SourcePage)
class SourcePageAdmin(admin.ModelAdmin):
    list_display = ("show", "year", "page_title", "latest_revision", "last_synced_at")
    list_filter = ("show", "year")
    search_fields = ("page_title",)
    readonly_fields = ("latest_revision", "last_synced_at")


@admin.register(SourceApproval)
class SourceApprovalAdmin(admin.ModelAdmin):
    list_display = ("show", "year", "approved", "approved_at", "approved_by")
    list_filter = ("approved", "show", "year")
    search_fields = ("show__name", "show__slug", "approved_by", "notes")


@admin.register(ImportRun)
class ImportRunAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "status",
        "started_at",
        "finished_at",
        "pages_processed",
        "wins_added",
        "conflicts_found",
    )
    list_filter = ("status",)
    readonly_fields = (
        "started_at",
        "finished_at",
        "requested_shows",
        "requested_years",
        "wins_added",
        "conflicts_found",
        "pages_processed",
        "failure_summary",
    )


@admin.register(ImportIssue)
class ImportIssueAdmin(admin.ModelAdmin):
    list_display = (
        "issue_type_summary",
        "date_or_year",
        "show_name",
        "quarantined_record",
        "retained_record",
        "explanation",
        "decision_status",
        "source_page",
        "created_at",
    )
    list_filter = ("issue_type", "resolution")
    search_fields = (
        "notes",
        "candidate",
        "source_page__page_title",
        "source_page__show__name",
    )
    readonly_fields = (
        "issue_type",
        "issue_type_summary_detail",
        "created_at",
        "import_run",
        "source_page",
        "candidate",
        "notes",
        "resolved_at",
        "issue_date_or_year",
        "issue_show",
        "quarantined_candidate_detail",
        "retained_record_detail",
        "expected_wins",
        "issue_explanation",
        "decision_status_detail",
        "decision_help",
    )
    fieldsets = (
        (
            "Decision",
            {
                "fields": (
                    "issue_type_summary_detail",
                    "resolution",
                    "decision_status_detail",
                    "decision_help",
                    "resolved_at",
                )
            },
        ),
        (
            "Issue details",
            {
                "fields": (
                    "issue_date_or_year",
                    "issue_show",
                    "quarantined_candidate_detail",
                    "retained_record_detail",
                    "expected_wins",
                    "issue_explanation",
                )
            },
        ),
        (
            "Evidence",
            {
                "fields": (
                    "source_page",
                    "import_run",
                    "notes",
                    "created_at",
                )
            },
        ),
    )

    decision_labels = {
        ImportIssue.Resolution.OPEN: "Needs review",
        ImportIssue.Resolution.ACCEPTED: "Candidate accepted",
        ImportIssue.Resolution.REJECTED: "Keep current public record",
    }

    def has_add_permission(self, request):
        """Issues are created by imports, so they are not hand-created in admin."""

        return False

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("source_page__show", "import_run")
        )

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if "resolution" in form.base_fields:
            form.base_fields["resolution"].choices = tuple(
                (value, self.decision_labels.get(value, label))
                for value, label in ImportIssue.Resolution.choices
            )
        return form

    def save_model(self, request, obj, form, change):
        if obj.resolution == ImportIssue.Resolution.OPEN:
            obj.resolved_at = None
        elif obj.resolved_at is None:
            obj.resolved_at = timezone.now()
        super().save_model(request, obj, form, change)

    @staticmethod
    def _candidate(issue: ImportIssue) -> dict[str, Any]:
        return issue.candidate if isinstance(issue.candidate, dict) else {}

    @staticmethod
    def _display_show(value: Any, issue: ImportIssue | None = None) -> str:
        if issue is not None and issue.source_page_id and issue.source_page:
            return issue.source_page.show.name
        if value in (None, ""):
            return "—"
        return str(value).replace("-", " ").title()

    @staticmethod
    def _display_value(value: Any) -> str:
        if value in (None, ""):
            return "—"
        if isinstance(value, bool):
            return "Yes" if value else "No"
        if isinstance(value, (list, tuple)):
            return ", ".join(ImportIssueAdmin._display_value(item) for item in value)
        if isinstance(value, dict):
            return "; ".join(
                f"{ImportIssueAdmin._humanize_key(key)}: "
                f"{ImportIssueAdmin._display_value(item)}"
                for key, item in value.items()
            )
        return str(value)

    @staticmethod
    def _humanize_key(key: Any) -> str:
        return str(key).replace("_", " ").capitalize()

    @staticmethod
    def _record_text(record: Any) -> str:
        if not isinstance(record, dict):
            return ImportIssueAdmin._display_value(record)
        artist = record.get("artist")
        song = record.get("song", record.get("title"))
        if artist not in (None, "") and song not in (None, ""):
            return f"{artist} — {song}"
        return ImportIssueAdmin._display_value(record)

    @staticmethod
    def _truncate(value: str, limit: int = 90) -> str:
        return value if len(value) <= limit else f"{value[: limit - 1]}…"

    @classmethod
    def _list_value(cls, value: Any, limit: int = 90):
        text = cls._display_value(value)
        return format_html(
            '<span title="{}">{}</span>', text, cls._truncate(text, limit)
        )

    @classmethod
    def _record_fields(cls, record: Any, keys: Iterable[str] | None = None) -> str:
        if not isinstance(record, dict):
            return cls._display_value(record)
        selected_keys = tuple(keys) if keys is not None else tuple(record)
        rows = (
            (
                cls._humanize_key(key),
                cls._display_value(record.get(key)),
            )
            for key in selected_keys
            if key in record
        )
        return (
            format_html_join(
                "",
                '<div class="import-issue-detail-row">'
                "<strong>{}</strong><span>{}</span></div>",
                rows,
            )
            or "—"
        )

    @admin.display(description="Issue")
    def issue_type_summary(self, obj: ImportIssue) -> str:
        descriptions = {
            ImportIssue.IssueType.LEGACY_DISCREPANCY: (
                "Legacy discrepancy — candidate vs retained"
            ),
            ImportIssue.IssueType.LEGACY_UNDATED: (
                "Legacy undated — aggregate without dates"
            ),
        }
        return descriptions.get(obj.issue_type, obj.get_issue_type_display())

    @admin.display(description="Date / year")
    def date_or_year(self, obj: ImportIssue) -> str:
        candidate = self._candidate(obj)
        return str(candidate.get("date") or candidate.get("year") or "—")

    @admin.display(description="Show")
    def show_name(self, obj: ImportIssue) -> str:
        return self._display_show(self._candidate(obj).get("show"), obj)

    @admin.display(description="Quarantined candidate")
    def quarantined_record(self, obj: ImportIssue):
        candidate = self._candidate(obj)
        record = candidate
        if obj.issue_type == ImportIssue.IssueType.CONFLICT:
            record = candidate.get("incoming", candidate)
        text = self._record_text(record)
        if obj.issue_type == ImportIssue.IssueType.LEGACY_UNDATED:
            expected_wins = candidate.get("expected_wins")
            if expected_wins is not None:
                text = f"{text} ({expected_wins} expected wins)"
        return self._list_value(text)

    @admin.display(description="Current public record")
    def retained_record(self, obj: ImportIssue):
        retained = self._retained_records(obj)
        if isinstance(retained, list):
            return self._list_value(
                "; ".join(self._record_text(item) for item in retained)
            )
        return self._list_value(self._record_text(retained))

    @admin.display(description="Explanation")
    def explanation(self, obj: ImportIssue):
        text = obj.notes or self._default_explanation(obj)
        return self._list_value(text, limit=110)

    @admin.display(description="Decision")
    def decision_status(self, obj: ImportIssue) -> str:
        return self.decision_labels.get(obj.resolution, obj.get_resolution_display())

    @admin.display(description="Date / year")
    def issue_date_or_year(self, obj: ImportIssue) -> str:
        return self.date_or_year(obj)

    @admin.display(description="Issue type")
    def issue_type_summary_detail(self, obj: ImportIssue) -> str:
        return self.issue_type_summary(obj)

    @admin.display(description="Show")
    def issue_show(self, obj: ImportIssue) -> str:
        return self.show_name(obj)

    @admin.display(description="Quarantined candidate")
    def quarantined_candidate_detail(self, obj: ImportIssue):
        candidate = self._candidate(obj)
        if obj.issue_type == ImportIssue.IssueType.LEGACY_DISCREPANCY:
            return self._record_fields(candidate, ("artist", "song"))
        if obj.issue_type == ImportIssue.IssueType.LEGACY_UNDATED:
            return self._record_fields(candidate, ("artist", "song"))
        if obj.issue_type == ImportIssue.IssueType.CONFLICT:
            return self._record_fields(candidate.get("incoming", candidate))
        return self._record_fields(candidate)

    @admin.display(description="Current public record")
    def retained_record_detail(self, obj: ImportIssue):
        retained = self._retained_records(obj)
        if retained is None:
            return "—"
        if isinstance(retained, list):
            return format_html_join(
                "",
                '<div class="import-issue-detail-row"><strong>{}</strong>'
                "<span>{}</span></div>",
                (("Existing record", self._record_text(record)) for record in retained),
            )
        return self._record_fields(retained, ("artist", "song"))

    @admin.display(description="Expected wins")
    def expected_wins(self, obj: ImportIssue) -> str:
        if obj.issue_type != ImportIssue.IssueType.LEGACY_UNDATED:
            return "—"
        return self._display_value(self._candidate(obj).get("expected_wins"))

    @admin.display(description="Explanation")
    def issue_explanation(self, obj: ImportIssue) -> str:
        explanation = obj.notes or self._default_explanation(obj)
        if obj.issue_type == ImportIssue.IssueType.LEGACY_UNDATED:
            explanation = (
                f"{explanation} Exact dates are unknown; this aggregate is not "
                "a public dated win."
            )
        return explanation

    @admin.display(description="Decision")
    def decision_status_detail(self, obj: ImportIssue) -> str:
        return self.decision_status(obj)

    @admin.display(description="What this decision does")
    def decision_help(self, obj: ImportIssue) -> str:
        messages = {
            ImportIssue.Resolution.OPEN: (
                "Needs review. No win data is changed by this status."
            ),
            ImportIssue.Resolution.ACCEPTED: (
                "The quarantined candidate is accepted as correct. This status "
                "records the review decision; it does not itself rewrite Win data. "
                "Data corrections are applied separately."
            ),
            ImportIssue.Resolution.REJECTED: (
                "The quarantined candidate is rejected and the current public record "
                "is kept. No win data is changed by this status."
            ),
        }
        return messages.get(obj.resolution, "No win data is changed by this status.")

    @staticmethod
    def _default_explanation(obj: ImportIssue) -> str:
        defaults = {
            ImportIssue.IssueType.LEGACY_DISCREPANCY: (
                "The legacy candidate differs from the current public record."
            ),
            ImportIssue.IssueType.LEGACY_UNDATED: (
                "This legacy record contains an aggregate count without exact dates."
            ),
        }
        return defaults.get(obj.issue_type, "Review the source evidence and candidate.")

    @classmethod
    def _retained_records(cls, obj: ImportIssue) -> Any:
        candidate = cls._candidate(obj)
        retained = candidate.get("retained")
        if retained is not None:
            return retained
        if obj.issue_type == ImportIssue.IssueType.CONFLICT:
            return candidate.get("existing")
        return None
