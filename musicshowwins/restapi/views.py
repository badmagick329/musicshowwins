from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from main.models import Win
from rest_framework import generics
from rest_framework.throttling import UserRateThrottle

from .serializers import SongsListSerializer

CACHE_TTL = settings.API_CACHE_TTL


class WinListThrottle(UserRateThrottle):
    rate = "60/minute"


class SongsList(generics.ListAPIView):
    serializer_class = SongsListSerializer
    throttle_classes = [WinListThrottle]

    @method_decorator(cache_page(CACHE_TTL))
    @swagger_auto_schema(
        operation_description="Get list of songs",
        manual_parameters=[
            openapi.Parameter(
                name="year",
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
                description="Filter song wins by year",
            ),
            openapi.Parameter(
                name="name",
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                description="Filter by song name",
            ),
            openapi.Parameter(
                name="artist",
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                description="Filter by artist name",
            ),
        ],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        year = self.request.query_params.get("year", None)
        if year is not None:
            try:
                year = int(year)
            except (TypeError, ValueError):
                year = None
        artist = self.request.query_params.get("artist", None)
        song = self.request.query_params.get("name", None)
        return Win.top_songs(year=year, artist=artist, song=song)
