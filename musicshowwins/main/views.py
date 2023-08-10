import django.db.models as models
from django.db.models import F, Q
from django.shortcuts import render

from main.apps import MainConfig
from main.models import Artist, Song, Win
from musicshowwins.settings import BASE_URL

app_name = MainConfig.name


def index(request):
    top_songs = Win.top_songs()
    context = {"songs": top_songs, "songs_by_year": list()}
    for year in range(2014, 2023):
        top_songs_by_year = Win.top_songs(year=year)
        context["songs_by_year"].append({"year": year, "songs": top_songs_by_year})
    return render(request, f"{app_name}/index.html", context)


def artists_view(request):
    artists = Win.top_artists()
    context = {
        "artists": artists,
        "artists_by_year": list(),
    }
    for year in range(2014, 2023):
        top_artists_by_year = Win.top_artists(year=year)
        context["artists_by_year"].append(
            {"year": year, "artists": top_artists_by_year}
        )
    return render(request, f"{app_name}/artists_page.html", context)


def artists_songs_view(request, artist_name: str):
    top_songs = Win.top_songs(artist=artist_name)
    context = {"songs": top_songs, "songs_by_year": list()}
    for year in range(2014, 2023):
        top_songs_by_year = Win.top_songs(artist=artist_name, year=year)
        if not top_songs_by_year:
            continue
        context["songs_by_year"].append({"year": year, "songs": top_songs_by_year})
    return render(request, f"{app_name}/index.html", context)
