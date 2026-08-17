from __future__ import annotations

from datetime import date

from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse

from .services import all_artists_queryset, leaderboard_queryset, wins_queryset


def _year(value: str | None) -> int | None:
    try:
        return int(value) if value else None
    except (TypeError, ValueError):
        return None


def index(request):
    kind = request.GET.get("list", "artists")
    if kind not in {"artists", "songs"}:
        kind = "artists"
    year = _year(request.GET.get("year"))
    items = leaderboard_queryset(kind, year=year)[:100]
    context = {
        "kind": kind,
        "year": year,
        "items": items,
        "years": range(date.today().year, 2013, -1),
    }
    return TemplateResponse(request, "main/index.html", context)


def artist_search(request):
    search = request.GET.get("search", "").strip()
    artists = all_artists_queryset()
    if search:
        artists = artists.filter(
            Q(name__icontains=search) | Q(aliases__alias__icontains=search)
        ).distinct()
    else:
        artists = artists.none()
    return TemplateResponse(
        request,
        "main/artists.html",
        {"artists": artists[:100], "search": search},
    )


def artist_detail(request, pk: int):
    artist = get_object_or_404(all_artists_queryset(), pk=pk)
    wins = wins_queryset(artist=str(pk))[:100]
    return TemplateResponse(
        request,
        "main/artist_detail.html",
        {"artist": artist, "wins": wins},
    )


def wins(request):
    year = _year(request.GET.get("year"))
    query = wins_queryset(year=year)
    return TemplateResponse(
        request,
        "main/wins.html",
        {"wins": query[:100], "year": year},
    )


def about(request):
    return TemplateResponse(request, "main/about.html", {})
