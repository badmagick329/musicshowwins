from datetime import date, timedelta

import pytest
from main.models import Artist, ArtistAlias, MusicShow, Song, Win
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_rbb_exact_alias_cutoff_and_production_http(settings):
    """Private proxy metadata must preserve public redirects and exact filtering."""
    settings.ALLOWED_HOSTS = ["kpopwins-api"]
    settings.SECURE_SSL_REDIRECT = True
    settings.SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    artist = Artist.objects.create(name="Alpha Artist")
    ArtistAlias.objects.create(artist=artist, alias="Alternate")
    song = Song.objects.create(artist=artist, title="First")
    show = MusicShow.objects.create(slug="music-bank", name="Music Bank")
    cutoff = date(2026, 10, 18)
    boundary = Win.objects.create(show=show, song=song, date=cutoff)
    Win.objects.create(show=show, song=song, date=cutoff + timedelta(days=1))
    client = APIClient(HTTP_HOST="kpopwins-api")
    assert client.get("/api/v1/wins").status_code == 301
    for value in (" alpha ARTIST ", " ALTERNATE ", str(artist.pk)):
        response = client.get(
            "/api/v1/wins",
            {
                "artist": value,
                "ordering": "-date",
                "date_to": cutoff.isoformat(),
                "page": 1,
            },
            HTTP_X_FORWARDED_PROTO="https",
        )
        assert response.status_code == 200
        assert set(response.data) == {"count", "next", "previous", "results"}
        assert [row["id"] for row in response.data["results"]] == [boundary.pk]
        assert response.data["results"][0]["song"]["artist"] == {
            "id": artist.pk,
            "slug": artist.slug,
            "name": artist.name,
        }
    for value in ("Alpha", artist.slug, "missing"):
        response = client.get(
            "/api/v1/wins", {"artist": value}, HTTP_X_FORWARDED_PROTO="https"
        )
        assert response.status_code == 200
        assert response.data["results"] == []
    assert (
        client.get(
            "/api/v1/wins", HTTP_HOST="untrusted", HTTP_X_FORWARDED_PROTO="https"
        ).status_code
        == 400
    )


@pytest.mark.django_db
def test_rbb_page_size_is_fixed_and_ties_are_stable():
    artist = Artist.objects.create(name="Artist")
    song = Song.objects.create(artist=artist, title="Song")
    show = MusicShow.objects.create(slug="show", name="Show")
    wins = Win.objects.bulk_create(
        [
            Win(show=show, song=song, date=date(2026, 10, 18) - timedelta(days=n))
            for n in range(101)
        ]
    )
    response = APIClient().get(
        "/api/v1/wins", {"ordering": "-date", "page": 1, "page_size": 5}
    )
    assert response.data["count"] == 101
    assert len(response.data["results"]) == 100
    assert response.data["next"] is not None
    assert [row["id"] for row in response.data["results"]] == [
        win.pk for win in wins[:100]
    ]
