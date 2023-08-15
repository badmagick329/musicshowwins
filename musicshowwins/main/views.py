from datetime import datetime

import django.db.models as models
from django.db.models import F, Q
from django.shortcuts import render

from main.apps import MainConfig
from main.models import Artist, Song, Win
from musicshowwins.settings import BASE_URL

app_name = MainConfig.name


def index(request):
    top_items = Win.top_songs()
    for i, item in enumerate(top_items):
        item.rank = i + 1
    current_year = datetime.now().year

    context = {
        "items": top_items,
        "item_type": "songs",
        "years": list(range(current_year, 2013, -1)),
        "table_header": "Top Songs since 2014",
    }
    return render(request, f"{app_name}/index.html", context)


def list_view(request):
    list_type = request.GET.get("list", "songs").strip()
    year = request.GET.get("year", None)
    search = request.GET.get("search", "").strip()
    if search:
        list_type = "songs"
    if year and not year.isdigit():
        year = None
    by_ = search.title() if search else ""
    if list_type == "songs":
        print("Getting top songs")
        top_items = Win.top_songs(year=year, artist=search)
        if top_items:
            by_ = top_items[0].artist.name
    else:
        print("Getting top artists")
        top_items = Win.top_artists(year=year)
        if top_items:
            by_ = top_items[0].name
    for i, item in enumerate(top_items):
        item.rank = i + 1
    table_header = ""
    if list_type == "songs":
        table_header = "Top Songs "
    else:
        table_header = "Top Artists "
    if search:
        table_header += f"by {by_} "
    if year:
        table_header += f"in {year} "
    else:
        table_header += "since 2014"
    context = {"items": top_items, "item_type": list_type, "table_header": table_header}
    return render(request, f"{app_name}/partials/wintable.html", context)


def _index(request):
    top_songs = Win.top_songs()
    context = {"songs": top_songs, "songs_by_year": list()}
    current_year = datetime.now().year
    for year in range(current_year, 2013, -1):
        top_songs_by_year = Win.top_songs(year=year)
        context["songs_by_year"].append({"year": year, "songs": top_songs_by_year})
    return render(request, f"{app_name}/_index.html", context)


def artists_view(request):
    artists = Win.top_artists()
    context = {
        "artists": artists,
        "artists_by_year": list(),
    }
    current_year = datetime.now().year
    for year in range(2014, current_year + 1):
        top_artists_by_year = Win.top_artists(year=year)
        context["artists_by_year"].append(
            {"year": year, "artists": top_artists_by_year}
        )
    return render(request, f"{app_name}/artists_page.html", context)


def artists_songs_view(request, artist_name: str):
    top_songs = Win.top_songs(artist=artist_name)
    context = {"songs": top_songs, "songs_by_year": list()}
    current_year = datetime.now().year
    for year in range(2014, current_year + 1):
        top_songs_by_year = Win.top_songs(artist=artist_name, year=year)
        if not top_songs_by_year:
            continue
        context["songs_by_year"].append({"year": year, "songs": top_songs_by_year})
    return render(request, f"{app_name}/index.html", context)
