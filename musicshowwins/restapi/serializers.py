from main.models import Artist, Song
from rest_framework import serializers


class ArtistSerializer(serializers.ModelSerializer):
    class Meta:
        model = Artist
        fields = ("name",)


class SongSerializer(serializers.ModelSerializer):
    artist = ArtistSerializer()

    class Meta:
        model = Song
        fields = (
            "artist",
            "name",
        )


class TopSongsSerializer(serializers.BaseSerializer):
    def to_representation(self, instance):
        return {
            "song": instance.name,
            "artist": instance.artist.name,
            "wins": instance.wins,
        }
