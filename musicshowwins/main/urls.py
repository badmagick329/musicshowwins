from django.urls import path

from main import views
from main.apps import MainConfig

app_name = MainConfig.name

urlpatterns = [
    path("", views.index, name="index"),
    path("artists_view", views.artists_view, name="artists_view"),
    path("artists_songs_view/<str:artist_name>", views.artists_songs_view, name="artists_songs_view"),
]
