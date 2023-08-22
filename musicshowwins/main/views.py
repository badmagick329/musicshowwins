from datetime import datetime

from django.shortcuts import render

from main.apps import MainConfig
from main.models import Artist, Win
from main.utils import song_chart

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


def details(request):
    search = request.GET.get("search", "").strip()
    context = {"search": search}
    return render(request, f"{app_name}/details.html", context)


def artist_search(request):
    search = request.GET.get("search", "").strip()
    if len(search) < 3:
        search = ""
    if search:
        artists = Artist.objects.filter(name__icontains=search)
    else:
        artists = list()
    context = {"artists": artists}
    return render(request, f"{app_name}/partials/search_results.html", context)


def artist_details(request):
    artist_id = request.GET.get("artist_id", "").strip()
    if artist_id and artist_id.isdigit():
        artist = Artist.objects.get(id=artist_id)
        artist_name = artist.name
        artist_wins_image = str(song_chart(artist.name))
    else:
        artist_name = None
        artist_wins_image = None
    context = {"artist_name": artist_name, "artist_wins_image": artist_wins_image}
    return render(request, f"{app_name}/partials/artist_details.html", context)


def wintable(request):
    list_type = request.GET.get("list", "songs").strip()
    year = request.GET.get("year", None)
    search = request.GET.get("search", "").strip()
    if search:
        list_type = "songs"
    if year and not year.isdigit():
        year = None
    by_ = search.title() if search else ""
    if list_type == "songs":
        top_items = Win.top_songs(year=year, artist=search)
        if top_items:
            by_ = top_items[0].artist.name
    else:
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
