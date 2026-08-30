from __future__ import annotations

from datetime import date

from django.db.models import Q
from main.services import (
    all_artists_queryset,
    all_songs_queryset,
    leaderboard_queryset,
    show_queryset,
    wins_queryset,
)
from rest_framework import generics
from rest_framework.exceptions import ValidationError

from .serializers import (
    ArtistLeaderboardSerializer,
    ArtistSerializer,
    ShowSerializer,
    SongLeaderboardSerializer,
    SongSerializer,
    WinSerializer,
)


def _integer(value: str | None, name: str, *, minimum: int | None = None) -> int | None:
    if value in (None, ""):
        return None
    try:
        result = int(value)
    except (TypeError, ValueError):
        raise ValidationError({name: "Must be an integer."})
    if minimum is not None and result < minimum:
        raise ValidationError({name: f"Must be at least {minimum}."})
    return result


def _date(value: str | None, name: str) -> date | None:
    if value in (None, ""):
        return None
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        raise ValidationError({name: "Use YYYY-MM-DD."})


def filters(request):
    params = request.query_params
    year = _integer(params.get("year"), "year", minimum=1900)
    date_from = _date(params.get("date_from"), "date_from")
    date_to = _date(params.get("date_to"), "date_to")
    if date_from and date_to and date_from > date_to:
        raise ValidationError({"date_range": "date_from cannot be after date_to."})
    return {
        "search": params.get("search", "").strip(),
        "artist": params.get("artist", "").strip(),
        "song": params.get("song", "").strip(),
        "show": params.get("show", "").strip(),
        "year": year,
        "date_from": date_from,
        "date_to": date_to,
    }


def ordered(queryset, request, allowed: set[str], default: str):
    value = request.query_params.get("ordering", default)
    parts = [part.strip() for part in value.split(",") if part.strip()]
    if not parts or any(part.lstrip("-") not in allowed for part in parts):
        raise ValidationError(
            {"ordering": f"Allowed fields: {', '.join(sorted(allowed))}."}
        )
    return queryset.order_by(*parts)


class ShowList(generics.ListAPIView):
    serializer_class = ShowSerializer

    def get_queryset(self):
        return ordered(
            show_queryset(self.request.query_params.get("search", "").strip()),
            self.request,
            {"name", "slug", "id"},
            "name",
        )


class ArtistList(generics.ListAPIView):
    serializer_class = ArtistSerializer

    def get_queryset(self):
        params = filters(self.request)
        query = all_artists_queryset(**params)
        if any(
            params[key] not in (None, "")
            for key in ("artist", "song", "show", "year", "date_from", "date_to")
        ):
            query = query.filter(
                pk__in=wins_queryset(**params).values("song__artist_id")
            )
        if params["search"]:
            query = query.filter(
                Q(name__icontains=params["search"])
                | Q(aliases__alias__icontains=params["search"])
            ).distinct()
        return ordered(
            query,
            self.request,
            {"name", "id", "total_wins"},
            "-total_wins,name",
        )


class ArtistDetail(generics.RetrieveAPIView):
    serializer_class = ArtistSerializer

    def get_queryset(self):
        return all_artists_queryset()


class SongList(generics.ListAPIView):
    serializer_class = SongSerializer

    def get_queryset(self):
        params = filters(self.request)
        query = all_songs_queryset(**params)
        if any(
            params[key] not in (None, "")
            for key in ("artist", "song", "show", "year", "date_from", "date_to")
        ):
            query = query.filter(pk__in=wins_queryset(**params).values("song_id"))
        if params["search"]:
            query = query.filter(
                Q(title__icontains=params["search"])
                | Q(artist__name__icontains=params["search"])
            )
        return ordered(
            query,
            self.request,
            {"title", "id", "total_wins", "artist__name"},
            "-total_wins,title,artist__name",
        )


class SongDetail(generics.RetrieveAPIView):
    serializer_class = SongSerializer

    def get_queryset(self):
        return all_songs_queryset()


class WinList(generics.ListAPIView):
    serializer_class = WinSerializer

    def get_queryset(self):
        return ordered(
            wins_queryset(with_song_totals=True, **filters(self.request)),
            self.request,
            {"date", "id", "show__name", "song__title", "song__artist__name"},
            "-date",
        )


class LeaderboardList(generics.ListAPIView):
    leaderboard_kind = "artists"

    def get_queryset(self):
        params = self.request.query_params
        year = _integer(params.get("year"), "year", minimum=1900)
        limit = _integer(params.get("limit"), "limit", minimum=1) or 100
        if limit > 1000:
            raise ValidationError({"limit": "Must be no greater than 1000."})
        return leaderboard_queryset(
            self.leaderboard_kind,
            year=year,
            show=params.get("show", "").strip(),
        )[:limit]


class ArtistLeaderboard(LeaderboardList):
    serializer_class = ArtistLeaderboardSerializer
    leaderboard_kind = "artists"


class SongLeaderboard(LeaderboardList):
    serializer_class = SongLeaderboardSerializer
    leaderboard_kind = "songs"
