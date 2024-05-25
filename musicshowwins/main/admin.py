from django.contrib import admin
from main.models import (
    Artist,
    ArtistFix,
    MusicShow,
    Song,
    SongFix,
    URLApprovalStatus,
    Win,
)

admin.site.register(MusicShow)
admin.site.register(URLApprovalStatus)


class ArtistAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


class SongAdmin(admin.ModelAdmin):
    list_display = ("name", "artist")
    list_filter = ("artist",)
    search_fields = ("name", "artist__name")


class WinAdmin(admin.ModelAdmin):
    list_display = ("music_show", "song", "date")
    list_filter = ("music_show", "date")
    search_fields = ("music_show__name", "song__name", "song__artist__name")


class ArtistFixAdmin(admin.ModelAdmin):
    list_display = ("old", "new")
    search_fields = ("old", "new")


class SongFixAdmin(admin.ModelAdmin):
    list_display = ("old", "new")
    search_fields = ("old", "new")


admin.site.register(Win, WinAdmin)
admin.site.register(Song, SongAdmin)
admin.site.register(Artist, ArtistAdmin)
admin.site.register(ArtistFix, ArtistFixAdmin)
admin.site.register(SongFix, SongFixAdmin)
