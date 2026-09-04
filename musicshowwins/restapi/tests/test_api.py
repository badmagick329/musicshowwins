import json
from datetime import date, timedelta
from unittest.mock import Mock, patch

import pytest
import requests
from django.apps import apps
from django.conf import settings
from django.core.cache import cache
from main.models import Artist, MusicShow, Song, Win, WinReference
from rest_framework.test import APIClient


@pytest.fixture
def archive(db):
    show = MusicShow.objects.create(slug="music-bank", name="Music Bank")
    artist_a = Artist.objects.create(name="Alpha")
    artist_b = Artist.objects.create(name="Beta")
    song_a = Song.objects.create(artist=artist_a, title="First")
    song_b = Song.objects.create(artist=artist_b, title="Second")
    Win.objects.create(show=show, song=song_a, date=date(2025, 1, 1))
    Win.objects.create(show=show, song=song_b, date=date(2025, 1, 2))
    Win.objects.create(show=show, song=song_a, date=date(2024, 1, 1))
    return show, artist_a, artist_b, song_a, song_b


@pytest.mark.django_db
def test_sitemap_source_returns_every_entity_without_pagination(archive):
    response = APIClient().get("/api/v1/sitemap")

    assert response.status_code == 200
    assert response.data == {
        "artists": [
            {"id": archive[1].pk, "latest_win_date": date(2025, 1, 1)},
            {"id": archive[2].pk, "latest_win_date": date(2025, 1, 2)},
        ],
        "songs": [
            {"id": archive[3].pk, "latest_win_date": date(2025, 1, 1)},
            {"id": archive[4].pk, "latest_win_date": date(2025, 1, 2)},
        ],
    }


@pytest.mark.django_db
def test_read_only_collections_and_contracts(archive):
    client = APIClient()

    shows = client.get("/api/v1/shows")
    artists = client.get("/api/v1/artists")
    songs = client.get("/api/v1/songs")
    wins = client.get("/api/v1/wins")

    assert (
        shows.status_code
        == artists.status_code
        == songs.status_code
        == wins.status_code
        == 200
    )
    assert set(shows.data["results"][0]) == {
        "id",
        "slug",
        "name",
        "active",
        "total_wins",
        "first_win_date",
        "latest_win_date",
        "latest_win",
    }
    assert shows.data["results"][0]["total_wins"] == 3
    assert shows.data["results"][0]["first_win_date"] == "2024-01-01"
    assert shows.data["results"][0]["latest_win"] == {
        "id": Win.objects.get(date=date(2025, 1, 2)).pk,
        "date": "2025-01-02",
        "song": {
            "id": archive[4].pk,
            "title": "Second",
            "artist": {"id": archive[2].pk, "name": "Beta"},
        },
    }
    assert set(artists.data["results"][0]) == {
        "id",
        "name",
        "total_wins",
        "winning_songs",
        "latest_win_date",
    }
    assert set(songs.data["results"][0]) == {
        "id",
        "title",
        "artist",
        "total_wins",
        "latest_win_date",
        "winning_shows",
    }
    assert set(wins.data["results"][0]) == {
        "id",
        "date",
        "show",
        "song",
        "references",
    }
    assert wins.data["results"][0]["references"] == []


@pytest.mark.django_db
def test_filters_ordering_and_invalid_parameters(archive):
    client = APIClient()
    assert client.get("/api/v1/wins?year=2025").data["count"] == 2
    assert client.get("/api/v1/wins?artist=Alpha").data["count"] == 2
    assert client.get("/api/v1/songs?search=Second").data["count"] == 1
    assert client.get("/api/v1/wins?date_from=2025-01-02").data["count"] == 1
    assert (
        client.get("/api/v1/wins?date_from=2025-01-01&date_to=2025-01-02").data["count"]
        == 2
    )
    assert client.get("/api/v1/wins?show=music-bank").data["count"] == 3
    assert client.get("/api/v1/wins?song=Second").data["count"] == 1
    ascending = client.get("/api/v1/wins?ordering=date").data["results"]
    assert ascending[0]["date"] == "2024-01-01"
    assert client.get("/api/v1/wins?ordering=not-a-field").status_code == 400
    assert client.get("/api/v1/wins?year=nope").status_code == 400
    assert (
        client.get("/api/v1/wins?date_from=2025-02-01&date_to=2025-01-01").status_code
        == 400
    )


@pytest.mark.django_db
def test_artist_ordering_and_win_annotations(archive, django_assert_num_queries):
    client = APIClient()
    extra_song = Song.objects.create(artist=archive[1], title="Another")
    Win.objects.create(show=archive[0], song=extra_song, date=date(2025, 2, 1))
    no_wins = Artist.objects.create(name="Aardvark")

    with django_assert_num_queries(2):
        default = client.get("/api/v1/artists").data["results"]
    assert [artist["name"] for artist in default[:3]] == ["Alpha", "Beta", "Aardvark"]
    assert default[0] == {
        "id": archive[1].pk,
        "name": "Alpha",
        "total_wins": 3,
        "winning_songs": 2,
        "latest_win_date": "2025-02-01",
    }
    assert default[2] == {
        "id": no_wins.pk,
        "name": "Aardvark",
        "total_wins": 0,
        "winning_songs": 0,
        "latest_win_date": None,
    }

    ascending = client.get("/api/v1/artists?ordering=name").data["results"]
    descending = client.get("/api/v1/artists?ordering=-name").data["results"]
    assert [artist["name"] for artist in ascending[:3]] == [
        "Aardvark",
        "Alpha",
        "Beta",
    ]
    assert [artist["name"] for artist in descending[:3]] == [
        "Beta",
        "Alpha",
        "Aardvark",
    ]


@pytest.mark.django_db
def test_song_annotations_ordering_and_query_count(archive, django_assert_num_queries):
    client = APIClient()
    second_show = MusicShow.objects.create(slug="the-show", name="The Show")
    third_artist = Artist.objects.create(name="Aardvark")
    third_song = Song.objects.create(artist=third_artist, title="Alpha")
    Win.objects.create(show=second_show, song=archive[3], date=date(2025, 2, 1))
    Win.objects.create(show=second_show, song=third_song, date=date(2023, 1, 1))

    with django_assert_num_queries(2):
        default = client.get("/api/v1/songs").data["results"]
    assert default[0] == {
        "id": archive[3].pk,
        "title": "First",
        "artist": {"id": archive[1].pk, "name": "Alpha"},
        "total_wins": 3,
        "latest_win_date": "2025-02-01",
        "winning_shows": 2,
    }
    assert [
        song["title"]
        for song in client.get("/api/v1/songs?ordering=title,artist__name").data[
            "results"
        ]
    ] == ["Alpha", "First", "Second"]
    assert [
        song["artist"]["name"]
        for song in client.get("/api/v1/songs?ordering=artist__name,title").data[
            "results"
        ]
    ] == ["Aardvark", "Alpha", "Beta"]
    detail = client.get(f"/api/v1/songs/{archive[3].pk}")
    assert detail.data["latest_win_date"] == "2025-02-01"
    assert detail.data["winning_shows"] == 2


@pytest.mark.django_db
def test_show_annotations_do_not_grow_queries_per_show(
    archive, django_assert_num_queries
):
    for index in range(5):
        MusicShow.objects.create(slug=f"show-{index}", name=f"Show {index}")

    client = APIClient()
    with django_assert_num_queries(2):
        response = client.get("/api/v1/shows")

    assert response.status_code == 200
    assert response.data["count"] == 6
    empty_show = next(
        show for show in response.data["results"] if show["slug"] == "show-0"
    )
    assert empty_show["total_wins"] == 0
    assert empty_show["first_win_date"] is None
    assert empty_show["latest_win_date"] is None
    assert empty_show["latest_win"] is None


@pytest.mark.django_db
def test_leaderboards_are_dense_ranked_and_year_filtered(archive):
    client = APIClient()
    artist_c = Artist.objects.create(name="Gamma")
    song_c = Song.objects.create(artist=artist_c, title="Third")
    Win.objects.create(show=archive[0], song=song_c, date=date(2025, 2, 1))
    Win.objects.create(show=archive[0], song=song_c, date=date(2025, 2, 2))
    artists = client.get("/api/v1/leaderboards/artists").data["results"]
    songs = client.get("/api/v1/leaderboards/songs?year=2025").data["results"]

    assert [row["rank"] for row in artists] == [1, 1, 2]
    assert [row["wins"] for row in artists] == [2, 2, 1]
    assert [row["wins"] for row in songs] == [2, 1, 1]


@pytest.mark.django_db
def test_page_number_pagination(archive):
    for offset in range(98):
        Win.objects.create(
            show=archive[0],
            song=archive[3],
            date=date(2020, 1, 3) + timedelta(days=offset),
        )
    client = APIClient()
    response = client.get("/api/v1/wins")
    assert response.status_code == 200
    assert len(response.data["results"]) == settings.PAGE_SIZE
    assert response.data["next"]
    assert len(client.get("/api/v1/wins?page=2").data["results"]) == 1


@pytest.mark.django_db
def test_wins_serialization_has_no_per_row_song_count_queries(
    archive, django_assert_num_queries
):
    for offset in range(4):
        artist = Artist.objects.create(name=f"Extra Artist {offset}")
        song = Song.objects.create(artist=artist, title=f"Extra Song {offset}")
        Win.objects.create(
            show=archive[0],
            song=song,
            date=date(2023, 1, 1) + timedelta(days=offset),
        )

    client = APIClient()
    for win in Win.objects.all():
        WinReference.objects.create(
            win=win,
            reference_type="article",
            provider="publisher",
            url=f"https://example.com/references/{win.pk}",
        )

    with django_assert_num_queries(4):
        response = client.get("/api/v1/wins")

    assert response.status_code == 200
    assert len(response.data["results"]) == 7


@pytest.mark.django_db
def test_win_api_exposes_only_prefetched_active_references(archive):
    wins = list(Win.objects.order_by("date"))
    one_reference = WinReference.objects.create(
        win=wins[1],
        reference_type="video",
        provider="youtube",
        external_id="one",
        url="https://www.youtube.com/watch?v=one",
        title="First stage",
        publisher_name="Official channel",
        is_official=True,
    )
    two_references = [
        WinReference.objects.create(
            win=wins[2],
            reference_type="article",
            provider="publisher",
            external_id=str(index),
            url=f"https://example.com/articles/{index}",
        )
        for index in range(2)
    ]
    WinReference.objects.create(
        win=wins[2],
        reference_type="video",
        provider="youtube",
        external_id="unavailable",
        url="https://www.youtube.com/watch?v=unavailable",
        status=WinReference.Status.UNAVAILABLE,
    )

    results = APIClient().get("/api/v1/wins?ordering=date").data["results"]

    assert results[0]["references"] == []
    assert [item["id"] for item in results[1]["references"]] == [one_reference.pk]
    assert [item["id"] for item in results[2]["references"]] == [
        reference.pk for reference in two_references
    ]
    assert set(results[1]["references"][0]) == {
        "id",
        "reference_type",
        "provider",
        "external_id",
        "url",
        "title",
        "publisher_name",
        "is_official",
        "published_at",
        "last_verified_at",
    }
    assert "metadata" not in results[1]["references"][0]


@pytest.mark.django_db
def test_detail_and_documentation_routes(archive):
    client = APIClient()
    artist = archive[1]
    song = archive[3]
    assert client.get(f"/api/v1/artists/{artist.pk}").status_code == 200
    assert client.get(f"/api/v1/songs/{song.pk}").status_code == 200
    assert client.get("/api/v1/artists/nope").status_code == 404
    assert client.get("/api/v1/artists/999999").status_code == 404
    assert client.get("/api/v1/songs/nope").status_code == 404
    assert client.post("/api/v1/shows", {}).status_code == 405
    assert client.get("/api/schema/").status_code == 200
    assert client.get("/api/docs/").status_code == 200
    schema = json.loads(client.get("/api/schema/?format=json").content)
    assert schema["openapi"].startswith("3.")
    assert "/api/v1/wins/" in schema["paths"]
    assert "/api/v1/corrections/" in schema["paths"]


def correction_payload(**overrides):
    return {
        "page_or_record": "Music Bank — 2 January 2025",
        "correction": "The winning song title should be Second.",
        "supporting_source": "https://example.com/source",
        "contact": "Fan@example.com",
        "website": "",
        **overrides,
    }


@pytest.mark.django_db
def test_correction_delivery_is_structured_private_and_stateless(archive, settings):
    cache.clear()
    settings.DISCORD_CORRECTIONS_WEBHOOK_URL = "https://discord.example/webhook"
    response_mock = Mock()
    response_mock.raise_for_status.return_value = None
    main_models = tuple(apps.get_app_config("main").get_models())
    before_counts = {model: model.objects.count() for model in main_models}

    with patch("restapi.views.requests.post", return_value=response_mock) as post:
        response = APIClient().post(
            "/api/v1/corrections", correction_payload(), format="json"
        )

    assert response.status_code == 202
    assert {model: model.objects.count() for model in main_models} == before_counts
    post.assert_called_once()
    assert post.call_args.kwargs["timeout"] == 5
    payload = post.call_args.kwargs["json"]
    assert payload["allowed_mentions"] == {"parse": []}
    assert [field["name"] for field in payload["embeds"][0]["fields"]] == [
        "Feedback",
        "Related page or link",
        "Supporting source",
        "Contact",
    ]


@pytest.mark.django_db
def test_correction_validation_and_json_only():
    cache.clear()
    client = APIClient()
    invalid = client.post(
        "/api/v1/corrections",
        correction_payload(correction="", supporting_source="ftp://example.com"),
        format="json",
    )
    assert invalid.status_code == 400
    assert "correction" in invalid.data
    assert "supporting_source" in invalid.data
    assert (
        client.post(
            "/api/v1/corrections", "page_or_record=test", content_type="text/plain"
        ).status_code
        == 415
    )
    assert client.get("/api/v1/corrections").status_code == 405


@pytest.mark.django_db
def test_correction_missing_configuration_and_discord_failure(settings):
    cache.clear()
    settings.DISCORD_CORRECTIONS_WEBHOOK_URL = ""
    assert (
        APIClient()
        .post("/api/v1/corrections", correction_payload(), format="json")
        .status_code
        == 503
    )

    cache.clear()
    settings.DISCORD_CORRECTIONS_WEBHOOK_URL = "https://discord.example/webhook"
    with patch("restapi.views.requests.post", side_effect=requests.RequestException):
        response = APIClient().post(
            "/api/v1/corrections", correction_payload(), format="json"
        )
    assert response.status_code == 503
    assert "Discord" not in response.data["detail"]


@pytest.mark.django_db
def test_correction_honeypot_returns_success_without_delivery(settings):
    cache.clear()
    settings.DISCORD_CORRECTIONS_WEBHOOK_URL = ""
    with patch("restapi.views.requests.post") as post:
        response = APIClient().post(
            "/api/v1/corrections",
            correction_payload(website="spam.example"),
            format="json",
        )
    assert response.status_code == 202
    post.assert_not_called()


@pytest.mark.django_db
def test_correction_has_dedicated_anonymous_throttle(settings):
    cache.clear()
    settings.DISCORD_CORRECTIONS_WEBHOOK_URL = "https://discord.example/webhook"
    response_mock = Mock()
    response_mock.raise_for_status.return_value = None
    client = APIClient()
    with patch("restapi.views.requests.post", return_value=response_mock):
        for _ in range(5):
            assert (
                client.post(
                    "/api/v1/corrections",
                    correction_payload(contact="", supporting_source=""),
                    format="json",
                    REMOTE_ADDR="203.0.113.77",
                ).status_code
                == 202
            )
        assert (
            client.post(
                "/api/v1/corrections",
                correction_payload(),
                format="json",
                REMOTE_ADDR="203.0.113.77",
            ).status_code
            == 429
        )


@pytest.mark.django_db
def test_anonymous_throttle_is_enforced(archive):
    cache.clear()
    assert settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["anon"] == "60/min"
    client = APIClient()
    for _ in range(60):
        assert (
            client.get("/api/v1/shows", REMOTE_ADDR="203.0.113.42").status_code == 200
        )
    assert client.get("/api/v1/shows", REMOTE_ADDR="203.0.113.42").status_code == 429


@pytest.mark.django_db
def test_anonymous_throttle_distinguishes_clients_behind_frontend(archive, settings):
    cache.clear()
    settings.REST_FRAMEWORK["NUM_PROXIES"] = 1
    client = APIClient()
    shared_proxy = "172.20.0.5"
    for _ in range(60):
        assert (
            client.get(
                "/api/v1/shows",
                REMOTE_ADDR=shared_proxy,
                HTTP_X_FORWARDED_FOR="203.0.113.42",
            ).status_code
            == 200
        )
    assert (
        client.get(
            "/api/v1/shows",
            REMOTE_ADDR=shared_proxy,
            HTTP_X_FORWARDED_FOR="203.0.113.42",
        ).status_code
        == 429
    )
    assert (
        client.get(
            "/api/v1/shows",
            REMOTE_ADDR=shared_proxy,
            HTTP_X_FORWARDED_FOR="203.0.113.43",
        ).status_code
        == 200
    )


@pytest.mark.django_db
def test_temporary_ui_pages(archive):
    client = APIClient()
    leaderboard = client.get("/")
    artists = client.get("/artists?search=Alpha")
    detail = client.get(f"/artists/{archive[1].pk}")
    wins = client.get("/wins")
    assert leaderboard.status_code == 200
    assert b"Alpha" in leaderboard.content and b"2" in leaderboard.content
    assert artists.status_code == 200 and b"Alpha" in artists.content
    assert b"2 wins" in artists.content
    assert detail.status_code == 200
    assert b"First" in detail.content and b"Jan. 1, 2025" in detail.content
    assert wins.status_code == 200
    assert b"Music Bank" in wins.content and b"Second" in wins.content


@pytest.mark.django_db
def test_general_feedback_needs_only_a_message(settings):
    cache.clear()
    settings.DISCORD_CORRECTIONS_WEBHOOK_URL = "https://discord.example/webhook"
    with patch("restapi.views.requests.post") as post:
        response = APIClient().post(
            "/api/v1/corrections",
            {"correction": "Please improve song search."},
            format="json",
        )
    assert response.status_code == 202
    assert post.call_args.kwargs["json"]["embeds"][0]["fields"] == [
        {"name": "Feedback", "value": "Please improve song search."}
    ]
