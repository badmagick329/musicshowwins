from main.models import Artist, MusicShow, Song, Win, WinReference
from rest_framework import serializers


class ShowSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = MusicShow
        fields = ("id", "slug", "name", "active")


class ShowSerializer(ShowSummarySerializer):
    total_wins = serializers.IntegerField(read_only=True)
    first_win_date = serializers.DateField(read_only=True, allow_null=True)
    latest_win_date = serializers.DateField(read_only=True, allow_null=True)
    latest_win = serializers.SerializerMethodField()

    class Meta:
        model = MusicShow
        fields = (
            "id",
            "slug",
            "name",
            "active",
            "total_wins",
            "first_win_date",
            "latest_win_date",
            "latest_win",
        )

    def get_latest_win(self, instance) -> dict | None:
        if instance.latest_win_id is None:
            return None
        return {
            "id": instance.latest_win_id,
            "date": instance.latest_win_date.isoformat(),
            "song": {
                "id": instance.latest_win_song_id,
                "title": instance.latest_win_song_title,
                "artist": {
                    "id": instance.latest_win_artist_id,
                    "slug": instance.latest_win_artist_slug,
                    "name": instance.latest_win_artist_name,
                },
            },
        }


class CorrectionSerializer(serializers.Serializer):
    page_or_record = serializers.CharField(
        max_length=300, required=False, allow_blank=True
    )
    correction = serializers.CharField(max_length=1000)
    supporting_source = serializers.URLField(
        max_length=500, required=False, allow_blank=True
    )
    contact = serializers.CharField(max_length=200, required=False, allow_blank=True)
    website = serializers.CharField(max_length=300, required=False, allow_blank=True)

    def validate_supporting_source(self, value):
        if value and not value.lower().startswith(("http://", "https://")):
            raise serializers.ValidationError("Use an HTTP or HTTPS URL.")
        return value


class SitemapEntrySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    latest_win_date = serializers.DateField(allow_null=True)


class ArtistSitemapEntrySerializer(SitemapEntrySerializer):
    slug = serializers.SlugField()


class SitemapSerializer(serializers.Serializer):
    artists = ArtistSitemapEntrySerializer(many=True)
    songs = SitemapEntrySerializer(many=True)


class ArtistSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Artist
        fields = ("id", "slug", "name")


class ArtistSerializer(serializers.ModelSerializer):
    total_wins = serializers.IntegerField(read_only=True)
    winning_songs = serializers.IntegerField(read_only=True)
    latest_win_date = serializers.DateField(read_only=True, allow_null=True)

    class Meta:
        model = Artist
        fields = (
            "id",
            "slug",
            "name",
            "total_wins",
            "winning_songs",
            "latest_win_date",
        )


class ArtistDetailSerializer(ArtistSerializer):
    indexable = serializers.BooleanField(read_only=True)

    class Meta(ArtistSerializer.Meta):
        fields = (*ArtistSerializer.Meta.fields, "indexable", "debut", "debut_solo")


class SongSummarySerializer(serializers.ModelSerializer):
    artist = ArtistSummarySerializer(read_only=True)

    class Meta:
        model = Song
        fields = ("id", "title", "artist")


class SongSerializer(SongSummarySerializer):
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


class SongDetailSerializer(SongSerializer):
    indexable = serializers.BooleanField(read_only=True)

    class Meta(SongSerializer.Meta):
        fields = (*SongSerializer.Meta.fields, "indexable")


class WinReferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = WinReference
        fields = (
            "id",
            "reference_type",
            "provider",
            "external_id",
            "url",
            "title",
            "publisher_name",
            "is_official",
            "published_at",
            "last_verified_at",
        )


class WinSerializer(serializers.ModelSerializer):
    show = ShowSummarySerializer(read_only=True)
    song = SongSerializer(read_only=True)
    references = WinReferenceSerializer(
        source="active_references", many=True, read_only=True
    )
    moment = serializers.SerializerMethodField()
    milestones = serializers.SerializerMethodField()

    def get_milestones(self, instance):
        return {
            "song_win": instance.song_win_number,
            "song_show_win": instance.song_show_win_number,
            "artist_win": instance.artist_win_number,
        }

    def get_moment(self, instance):
        moment = getattr(instance, "public_moment", None)
        if moment is None:
            return None
        return {
            "heading": moment.heading,
            "body": moment.body,
            "citations": WinReferenceSerializer(
                moment.active_citations, many=True
            ).data,
        }

    class Meta:
        model = Win
        fields = (
            "id",
            "date",
            "show",
            "song",
            "performed",
            "references",
            "moment",
            "milestones",
        )


class ArtistLeaderboardSerializer(serializers.Serializer):
    rank = serializers.IntegerField()
    wins = serializers.IntegerField()
    artist = ArtistSummarySerializer(source="*")


class SongLeaderboardSerializer(serializers.Serializer):
    rank = serializers.IntegerField()
    wins = serializers.IntegerField(source="win_count")
    song = SongSummarySerializer(source="*")
