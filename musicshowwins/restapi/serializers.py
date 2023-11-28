from collections import OrderedDict

from drf_yasg import openapi
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


class SongsListSerializer(serializers.BaseSerializer):
    class Meta:
        swagger_schema_fields = {
            "type": openapi.TYPE_OBJECT,
            "properties": {
                "song": openapi.Schema(
                    description="The name of the song",
                    type=openapi.TYPE_STRING,
                ),
                "artist": openapi.Schema(
                    description="The name of the artist",
                    type=openapi.TYPE_STRING,
                ),
                "wins": openapi.Schema(
                    description="The number of wins for this song",
                    type=openapi.TYPE_INTEGER,
                ),
            },
            "description": "A list of songs, optionally filtered by year and/or artist.",
            "example": [
                {
                    "song": "Dynamite",
                    "artist": "BTS",
                    "wins": 32,
                },
            ],
        }

    def to_representation(self, instance):
        return {
            "song": instance.name,
            "artist": instance.artist.name,
            "wins": instance.wins,
        }
