"""Shared read-only queries used by the API and the temporary HTML UI."""

from __future__ import annotations

from datetime import date

from django.db.models import Count, F, Prefetch, Q, Window
from django.db.models.functions import DenseRank

from .models import Artist, MusicShow, Song, Win


def _show_query(value: str, prefix: str = "") -> Q:
    field = f"{prefix}show"
    if value.isdigit():
        return Q(**{f"{field}__id": int(value)})
    return Q(**{f"{field}__slug__iexact": value}) | Q(
        **{f"{field}__name__iexact": value}
    )


def _artist_query(value: str, prefix: str = "") -> Q:
    field = f"{prefix}song__artist"
    if value.isdigit():
        return Q(**{f"{field}__id": int(value)})
    return Q(**{f"{field}__name__iexact": value}) | Q(
        **{f"{field}__aliases__alias__iexact": value}
    )


def _song_query(value: str, prefix: str = "") -> Q:
    field = f"{prefix}song"
    if value.isdigit():
        return Q(**{f"{field}__id": int(value)})
    return Q(**{f"{field}__title__iexact": value})


def win_filters(
    *,
    search: str = "",
    artist: str = "",
    song: str = "",
    show: str = "",
    year: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    prefix: str = "",
) -> Q:
    """Build a reusable Q object for win-related filters."""
    query = Q()
    if search:
        query &= (
            Q(**{f"{prefix}song__title__icontains": search})
            | Q(**{f"{prefix}song__artist__name__icontains": search})
            | Q(**{f"{prefix}song__artist__aliases__alias__icontains": search})
            | Q(**{f"{prefix}show__name__icontains": search})
        )
    if artist:
        query &= _artist_query(artist, prefix)
    if song:
        query &= _song_query(song, prefix)
    if show:
        query &= _show_query(show, prefix)
    if year is not None:
        query &= Q(**{f"{prefix}date__year": year})
    if date_from is not None:
        query &= Q(**{f"{prefix}date__gte": date_from})
    if date_to is not None:
        query &= Q(**{f"{prefix}date__lte": date_to})
    return query


def wins_queryset(*, with_song_totals: bool = False, **filters):
    queryset = Win.objects.select_related("show")
    if with_song_totals:
        songs = Song.objects.select_related("artist").annotate(
            total_wins=Count("wins", distinct=True)
        )
        queryset = queryset.prefetch_related(Prefetch("song", queryset=songs))
    else:
        queryset = queryset.select_related("song__artist")
    return queryset.filter(win_filters(**filters))


def all_artists_queryset(**filters):
    query = win_filters(**filters, prefix="songs__wins__")
    return Artist.objects.annotate(
        total_wins=Count("songs__wins", filter=query, distinct=True)
    ).order_by("name")


def all_songs_queryset(**filters):
    query = win_filters(**filters, prefix="wins__")
    return (
        Song.objects.select_related("artist")
        .annotate(total_wins=Count("wins", filter=query, distinct=True))
        .order_by("title", "artist__name")
    )


def show_queryset(search: str = ""):
    query = MusicShow.objects.all()
    if search:
        query = query.filter(Q(name__icontains=search) | Q(slug__icontains=search))
    return query.order_by("name")


def leaderboard_queryset(kind: str, *, year: int | None = None, show: str = ""):
    filters = {"year": year, "show": show}
    filters = {key: value for key, value in filters.items() if value not in (None, "")}
    if kind == "artists":
        query = win_filters(**filters, prefix="songs__wins__")
        base = Artist.objects.annotate(
            wins=Count("songs__wins", filter=query, distinct=True)
        ).filter(wins__gt=0)
    else:
        query = win_filters(**filters, prefix="wins__")
        base = (
            Song.objects.select_related("artist")
            .annotate(win_count=Count("wins", filter=query, distinct=True))
            .filter(win_count__gt=0)
        )
    return base.annotate(
        rank=Window(
            expression=DenseRank(),
            order_by=F("wins" if kind == "artists" else "win_count").desc(),
        )
    ).order_by(
        "-wins" if kind == "artists" else "-win_count",
        "name" if kind == "artists" else "title",
        "pk",
    )
