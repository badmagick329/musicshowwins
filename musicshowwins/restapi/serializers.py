from main.models import Artist, MusicShow, Song, Win
from rest_framework import serializers


class ShowSerializer(serializers.ModelSerializer):
    class Meta:
        model = MusicShow
        fields = ("id", "slug", "name", "active")


class ArtistSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Artist
        fields = ("id", "name")


class ArtistSerializer(serializers.ModelSerializer):
    total_wins = serializers.IntegerField(read_only=True)
    winning_songs = serializers.IntegerField(read_only=True)
    latest_win_date = serializers.DateField(read_only=True, allow_null=True)

    class Meta:
        model = Artist
        fields = (
            "id",
            "name",
            "total_wins",
            "winning_songs",
            "latest_win_date",
        )


class SongSerializer(serializers.ModelSerializer):
    artist = ArtistSummarySerializer(read_only=True)
    total_wins = serializers.IntegerField(read_only=True)
    latest_win_date = serializers.DateField(read_only=True, allow_null=True)
    winning_shows = serializers.IntegerField(read_only=True)

    class Meta:
        model = Song
        fields = (
            "id",
            "title",
            "artist",
            "total_wins",
            "latest_win_date",
            "winning_shows",
        )


class WinSerializer(serializers.ModelSerializer):
    show = ShowSerializer(read_only=True)
    song = SongSerializer(read_only=True)

    class Meta:
        model = Win
        fields = ("id", "date", "show", "song")


class ArtistLeaderboardSerializer(serializers.Serializer):
    rank = serializers.IntegerField()
    wins = serializers.IntegerField()
    artist = ArtistSummarySerializer(source="*")

    def to_representation(self, instance):
        return {
            "rank": instance.rank,
            "wins": instance.wins,
            "artist": ArtistSummarySerializer(instance).data,
        }


class SongLeaderboardSerializer(serializers.Serializer):
    rank = serializers.IntegerField()
    wins = serializers.IntegerField()
    song = SongSerializer(source="*")

    def to_representation(self, instance):
        wins = instance.win_count if hasattr(instance, "win_count") else instance.wins
        return {
            "rank": instance.rank,
            "wins": wins,
            "song": {
                "id": instance.pk,
                "title": instance.title,
                "artist": ArtistSummarySerializer(instance.artist).data,
            },
        }
