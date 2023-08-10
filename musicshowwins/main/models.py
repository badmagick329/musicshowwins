from django.db import models
from django.db.models import F, Q, QuerySet


class MusicShow(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"<MusicShow(id={self.id}, name={self.name})>"


class Artist(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"<Artist(id={self.id}, name={self.name})>"


class Song(models.Model):
    name = models.CharField(max_length=100)
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.artist} - {self.name} "

    def __repr__(self):
        return f"<Song(id={self.id}, name={self.name}, artist={self.artist})>"

    class Meta:
        unique_together = ("name", "artist")


class Win(models.Model):
    music_show = models.ForeignKey(MusicShow, on_delete=models.CASCADE)
    song = models.ForeignKey(Song, on_delete=models.CASCADE)
    date = models.DateField()
    year = models.IntegerField()

    def save(self, *args, **kwargs):
        self.year = int(self.date.split("-")[0])
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.music_show} - {self.song} - {self.date}"

    def __repr__(self):
        return f"<Win(id={self.id}, music_show={self.music_show}, song={self.song})>"

    @classmethod
    def top_songs(
        cls, artist: str | None = None, year: int | None = None, n: int = 20
    ) -> QuerySet[Song]:
        songs = Song.objects.select_related("artist")
        filters = Q()
        if year:
            filters &= Q(win__year=year)
        if artist:
            filters &= Q(artist__name__iexact=artist)
        qs = (
            songs.filter(filters)
            .annotate(wins=models.Count("win"))
            .order_by("-wins")[:n]
        )
        return qs

    @classmethod
    def top_artists(cls, year: int | None = None, n: int = 20) -> QuerySet[Artist]:
        artists = Artist.objects.all()
        filters = Q()
        if year:
            filters &= Q(song__win__year=year)
        qs = (
            artists.filter(filters)
            .annotate(wins=models.Count("song__win"))
            .order_by("-wins")[:n]
        )
        return qs

    class Meta:
        unique_together = ("music_show", "song", "date")
        indexes = [
            models.Index(fields=["year"]),
        ]
