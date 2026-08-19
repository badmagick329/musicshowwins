from django.contrib import admin

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
        "issue_type",
        "resolution",
        "source_page",
        "created_at",
        "resolved_at",
    )
    list_filter = ("issue_type", "resolution")
    search_fields = ("notes",)
    readonly_fields = ("created_at", "import_run", "source_page", "candidate", "notes")
