from datetime import date
from pathlib import Path

import pytest

from main.models import Artist, MusicShow, Song, Win
from main.win_reference_io import validate_document as validate_backend_document


@pytest.mark.django_db
def test_operator_manifest_is_accepted_by_backend_v1_contract(monkeypatch):
    repository_root = Path(__file__).resolve().parents[3]
    monkeypatch.syspath_prepend(str(repository_root / "operator-tools" / "src"))
    from kpopwins_operator.manifest import validate_document

    show = MusicShow.objects.create(slug="music-bank", name="Music Bank")
    artist = Artist.objects.create(name="Alpha")
    song = Song.objects.create(artist=artist, title="First")
    Win.objects.create(show=show, song=song, date=date(2026, 1, 2))
    operator_document = validate_document(
        {
            "version": 1,
            "references": [
                {
                    "win": {"show": " music-bank ", "date": " 2026-01-02 "},
                    "reference_type": " video ",
                    "provider": " YouTube ",
                    "external_id": " abc123 ",
                    "url": " https://www.youtube.com/watch?v=abc123 ",
                    "title": " Winner stage ",
                    "publisher_name": " Official channel ",
                    "publisher_external_id": " channel-id ",
                    "is_official": True,
                    "status": " active ",
                    "published_at": " 2026-01-02T12:00:00Z ",
                    "last_verified_at": " 2026-08-31T12:00:00Z ",
                    "metadata": {"duration": 180},
                }
            ],
        }
    )

    validated = validate_backend_document(operator_document)

    assert len(validated) == 1
    assert validated[0].values["provider"] == "youtube"
    assert validated[0].values["url"] == ("https://www.youtube.com/watch?v=abc123")
