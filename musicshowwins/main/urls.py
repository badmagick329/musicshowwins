from django.urls import path

from main import views
from main.apps import MainConfig

app_name = MainConfig.name

urlpatterns = [
    path("", views.index, name="index"),
    # TODO:
    # Change these route names
    path("list_view", views.list_view, name="list_view"),
    path("artists_view", views.artists_view, name="artists_view"),
    path("artists_songs_view/<str:artist_name>", views.artists_songs_view, name="artists_songs_view"),
]
