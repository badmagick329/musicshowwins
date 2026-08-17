from django.urls import path, re_path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from . import views

app_name = "restapi"

urlpatterns = [
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "docs/",
        SpectacularSwaggerView.as_view(url_name="restapi:schema"),
        name="docs",
    ),
    re_path(r"^v1/shows/?$", views.ShowList.as_view(), name="shows"),
    re_path(r"^v1/artists/?$", views.ArtistList.as_view(), name="artists"),
    path("v1/artists/<int:pk>", views.ArtistDetail.as_view(), name="artist-detail"),
    re_path(r"^v1/songs/?$", views.SongList.as_view(), name="songs"),
    path("v1/songs/<int:pk>", views.SongDetail.as_view(), name="song-detail"),
    re_path(r"^v1/wins/?$", views.WinList.as_view(), name="wins"),
    re_path(
        r"^v1/leaderboards/artists/?$",
        views.ArtistLeaderboard.as_view(),
        name="leaderboard-artists",
    ),
    re_path(
        r"^v1/leaderboards/songs/?$",
        views.SongLeaderboard.as_view(),
        name="leaderboard-songs",
    ),
]
