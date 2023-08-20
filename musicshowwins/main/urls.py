from django.urls import path

from main import views
from main.apps import MainConfig

app_name = MainConfig.name

urlpatterns = [
    path("", views.index, name="index"),
    path("wintable", views.wintable, name="wintable"),
    path("details", views.details, name="details"),
    path("artist_search", views.artist_search, name="artist_search"),
    path("artist_details", views.artist_details, name="artist_details"),
]
