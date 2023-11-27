from main.models import Win
from rest_framework import filters, generics
from rest_framework.decorators import throttle_classes
from rest_framework.throttling import UserRateThrottle

from .serializers import TopSongsSerializer


class WinListThrottle(UserRateThrottle):
    rate = "30/minute"


class TopSongsList(generics.ListAPIView):
    serializer_class = TopSongsSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ["name", "artist__name"]

    @throttle_classes([WinListThrottle])
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        year = self.request.query_params.get("year", None)
        if year is not None:
            try:
                year = int(year)
            except (TypeError, ValueError):
                year = None
        artist = self.request.query_params.get("artist", None)
        return Win.top_songs(year=year, artist=artist)
