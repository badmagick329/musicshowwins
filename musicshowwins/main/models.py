from django.db import models
from django.db.models import F, Q, QuerySet


class MusicShow(models.Model):
    name = models.CharField(max_length=100, unique=True, blank=False, null=False)

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"<MusicShow(id={self.id}, name={self.name})>"


class Artist(models.Model):
    name = models.CharField(max_length=100, unique=True, blank=False, null=False)

    def take_songs_from(self, other: "Artist"):
        own_songs = Song.objects.filter(artist=self)
        other_songs = Song.objects.filter(artist=other)
        own_names = own_songs.values_list("name", flat=True)
        to_remove = list()
        for other_song in other_songs:
            if other_song.name in own_names:
                other_song.give_wins_to(own_songs.get(name=other_song.name))
                to_remove.append(other_song)
                continue
            other_song.artist = self
            other_song.save()
        remove_songs = other_songs.filter(id__in=[s.id for s in to_remove])
        for song in remove_songs:
            song.delete()

    @property
    def display_name(self) -> str:
        return self.name

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"<Artist(id={self.id}, name={self.name})>"


class Song(models.Model):
    name = models.CharField(max_length=100)
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE)

    def give_wins_to(self, other: "Song"):
        own_wins = Win.objects.filter(song=self)
        to_remove = list()
        for win in own_wins:
            win_exists = Win.objects.filter(
                music_show=win.music_show, song=other, date=win.date
            ).exists()
            if win_exists:
                to_remove.append(win)
                continue
            win.song = other
            win.save()
        remove_wins = own_wins.filter(id__in=[w.id for w in to_remove])
        for win in remove_wins:
            win.delete()

    @property
    def display_name(self) -> str:
        return f"{self.artist.name} - {self.name}"

    def __str__(self):
        return f"{self.artist} - {self.name}"

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
        if not self.year:
            self.year = int(self.date.split("-")[0])
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.music_show} - {self.song} - {self.date}"

    def __repr__(self):
        return f"<Win(id={self.id}, music_show={self.music_show}, song={self.song})>"

    @classmethod
    def top_songs(
        cls,
        artist: str | None = None,
        year: int | None = None,
        song: str | None = None,
    ) -> QuerySet[Song]:
        songs = Song.objects.select_related("artist")
        filters = Q()
        if year:
            filters &= Q(win__year=year)
        if artist:
            filters &= Q(artist__name__iexact=artist)
        if song:
            filters &= Q(name__iexact=song)
        qs = songs.filter(filters).annotate(wins=models.Count("win")).order_by("-wins")
        return qs

    @classmethod
    def top_artists(cls, year: int | None = None) -> QuerySet[Artist]:
        artists = Artist.objects.all()
        filters = Q()
        if year:
            filters &= Q(song__win__year=year)
        qs = (
            artists.filter(filters)
            .annotate(wins=models.Count("song__win"))
            .order_by("-wins")
        )
        return qs

    class Meta:
        unique_together = ("music_show", "song", "date")
        indexes = [
            models.Index(fields=["year"]),
        ]


class ArtistFix(models.Model):
    old = models.CharField(max_length=100)
    new = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.old} -> {self.new}"


class SongFix(models.Model):
    old = models.CharField(max_length=100)
    new = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.old} -> {self.new}"


class URLApprovalStatus(models.Model):
    url = models.CharField(max_length=255, unique=True)
    approved = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.url} - {self.approved}"
