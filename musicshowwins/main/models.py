from django.db import models


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
        return f"{self.name} - {self.artist}"

    def __repr__(self):
        return f"<Song(id={self.id}, name={self.name}, artist={self.artist})>"

    class Meta:
        unique_together = ("name", "artist")


class Win(models.Model):
    music_show = models.ForeignKey(MusicShow, on_delete=models.CASCADE)
    song = models.ForeignKey(Song, on_delete=models.CASCADE)
    date = models.DateField()

    def __str__(self):
        return f"{self.music_show} - {self.song} - {self.date}"

    def __repr__(self):
        return f"<Win(id={self.id}, music_show={self.music_show}, song={self.song})>"

    class Meta:
        unique_together = ("music_show", "song", "date")
