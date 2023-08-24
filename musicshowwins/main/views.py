from datetime import datetime

from django.template.response import TemplateResponse

from main.apps import MainConfig
from main.models import Artist, Win
from main.utils import add_ranks, song_chart, year_chart, log_access
from scripts.wikiscraper import WikiScraper

app_name = MainConfig.name


def index(request):
    top_items = Win.top_songs()
    add_ranks(top_items)
    current_year = datetime.now().year

    # TODO:
    # Get min and max year from db
    context = {
        "items": top_items,
        "item_type": "songs",
        "years": list(range(current_year, 2013, -1)),
        "table_header": "Top Songs since 2014",
    }
    return TemplateResponse(request, f"{app_name}/index.html", context)


def details(request):
    search = request.GET.get("search", "").strip()
    artist_id = request.GET.get("artist_id", "").strip()
    context = {"search": search, "artist_id": artist_id}
    return TemplateResponse(request, f"{app_name}/details.html", context)


def artist_search(request):
    search = request.GET.get("search", "").strip()
    if len(search) < 2:
        search = ""
    if search:
        artists = Artist.objects.filter(name__icontains=search)
    else:
        artists = list()
    context = {"artists": artists}
    return TemplateResponse(
        request, f"{app_name}/partials/search_results.html", context
    )


def artist_details(request):
    artist_id = request.GET.get("artist_id", "").strip()
    artist_name = None
    if artist_id and artist_id.isdigit():
        artist = Artist.objects.get(id=artist_id)
        artist_name = artist.name
    context = {
        "artist_id": artist_id,
        "artist_name": artist_name,
    }
    return TemplateResponse(
        request, f"{app_name}/partials/artist_details.html", context
    )


def song_image_view(request):
    artist_id = request.GET.get("artist_id", "").strip()
    song_wins_image = None
    context_data = {}
    if artist_id and artist_id.isdigit():
        artist = Artist.objects.get(id=artist_id)
        song_wins_image, context_data = song_chart(artist.name)
    context = {
        "song_wins_image": song_wins_image,
        **context_data,
    }
    return TemplateResponse(request, f"{app_name}/partials/song_image.html", context)


def year_image_view(request):
    artist_id = request.GET.get("artist_id", "").strip()
    year_wins_image = None
    context_data = {}
    if artist_id and artist_id.isdigit():
        artist = Artist.objects.get(id=artist_id)
        year_wins_image, context_data = year_chart(artist.name)
    context = {
        "year_wins_image": year_wins_image,
        **context_data,
    }
    return TemplateResponse(request, f"{app_name}/partials/year_image.html", context)


def wintable(request):
    list_type = request.GET.get("list", "songs").strip()
    year = request.GET.get("year", None)
    if year and not year.isdigit():
        year = None
    if list_type == "songs":
        top_items = Win.top_songs(year=year)
    else:
        top_items = Win.top_artists(year=year)
    add_ranks(top_items)
    table_header = ""
    if list_type == "songs":
        table_header = "Top Songs "
    else:
        table_header = "Top Artists "
    # TODO:
    # Get min and max year from db
    if year:
        table_header += f"in {year} "
    else:
        table_header += "since 2014"
    context = {"items": top_items, "item_type": list_type, "table_header": table_header}
    return TemplateResponse(request, f"{app_name}/partials/wintable.html", context)


def about(request):
    s = WikiScraper()
    sources = s.get_sources()
    return TemplateResponse(request, f"{app_name}/about.html", {"sources": sources})
