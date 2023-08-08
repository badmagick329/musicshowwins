import django.db.models as models
from django.db.models import F, Q
from django.shortcuts import render

from main.apps import MainConfig
from main.models import Artist, Song, Win
from musicshowwins.settings import BASE_URL

app_name = MainConfig.name


def index(request):
    top_songs = (
        Song.objects.select_related("artist")
        .all()
        .annotate(wins=models.Count("win"))
        .order_by("-wins")[:20]
    )
    context = {
        "top_songs": top_songs,
    }
    return render(request, f"{app_name}/index.html", context)
