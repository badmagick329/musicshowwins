from django.urls import path

from . import views

app_name = "main"

urlpatterns = [
    path("", views.index, name="index"),
    path("artists", views.artist_search, name="artists"),
    path("artists/<int:pk>", views.artist_detail, name="artist-detail"),
    path("wins", views.wins, name="wins"),
    path("about", views.about, name="about"),
]
