from django.shortcuts import render

from main.apps import MainConfig
from musicshowwins.settings import BASE_URL

app_name = MainConfig.name


def index(request):
    return render(request, f"{app_name}/index.html")
