from django.contrib import admin

# Register your models here.
from main.models import Artist, MusicShow, Song, Win

admin.site.register(MusicShow)


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


admin.site.register(Win, WinAdmin)
admin.site.register(Song, SongAdmin)
admin.site.register(Artist, ArtistAdmin)
