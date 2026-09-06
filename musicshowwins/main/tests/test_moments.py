import json
from datetime import date

import pytest
from django.core.exceptions import ValidationError

from main.models import Artist, MusicShow, Song, Win, WinMoment, WinReference
from main.moment_io import MomentDocumentError, import_moments


@pytest.fixture
def moment_document(db):
    show = MusicShow.objects.create(slug="the-show", name="The Show")
    artist = Artist.objects.create(name="BTS")
    song = Song.objects.create(artist=artist, title="I Need U")
    win = Win.objects.create(show=show, song=song, date=date(2015, 5, 5))
    return win, {
        "version": 1,
        "moments": [
            {
                "state": "matched",
                "event": {
                    "show": "the-show",
                    "date": "2015-05-05",
                    "artist": "BTS",
                    "song": "I Need U",
                },
                "heading": "BTS's first win",
                "body": "A sourced story.",
                "citations": [
                    {
                        "provider": "soompi",
                        "publisher_name": "Soompi",
                        "title": "Report",
                        "url": "https://example.com/report",
                    }
                ],
            }
        ],
    }


@pytest.mark.django_db
def test_import_is_dry_run_idempotent_and_publishable(moment_document):
    win, document = moment_document
    assert import_moments(document, dry_run=True) == (1, 0)
    assert WinMoment.objects.count() == 0
    assert import_moments(document) == (1, 0)
    assert import_moments(document, publish=True) == (0, 1)
    assert WinMoment.objects.get(win=win).status == "published"
    assert WinReference.objects.count() == 1


@pytest.mark.django_db
def test_wrong_event_and_cross_win_citations_are_rejected(moment_document):
    win, document = moment_document
    wrong = json.loads(json.dumps(document))
    wrong["moments"][0]["event"]["song"] = "Not This Song"
    with pytest.raises(MomentDocumentError, match="does not match"):
        import_moments(wrong)
    other = Win.objects.create(show=win.show, song=win.song, date=date(2015, 5, 6))
    citation = WinReference.objects.create(
        win=other,
        reference_type="article",
        provider="source",
        url="https://example.com/other",
    )
    moment = WinMoment.objects.create(win=win, heading="Story", body="Body")
    with pytest.raises(ValidationError, match="same win"):
        moment.citations.add(citation)


@pytest.mark.django_db
def test_public_api_hides_drafts_and_unsupported_published_moments(moment_document):
    win, document = moment_document
    import_moments(document)
    from rest_framework.test import APIClient

    assert APIClient().get("/api/v1/wins").data["results"][0]["moment"] is None
    import_moments(document, publish=True)
    assert (
        APIClient().get("/api/v1/wins").data["results"][0]["moment"]["heading"]
        == "BTS's first win"
    )
    WinReference.objects.update(status="unavailable")
    assert APIClient().get("/api/v1/wins").data["results"][0]["moment"] is None


@pytest.mark.django_db
def test_import_rejects_invalid_urls_and_explicit_pending_or_unknown_artists(
    moment_document,
):
    _, document = moment_document
    document["moments"][0]["citations"][0]["url"] = "not a URL"
    with pytest.raises(MomentDocumentError, match="valid HTTP or HTTPS URL"):
        import_moments(document, dry_run=True)
    assert WinMoment.objects.count() == 0

    pending = json.loads(json.dumps(document))
    pending["moments"][0]["citations"][0]["url"] = "https://example.com/report"
    pending["moments"][0]["state"] = "pending"
    pending["moments"][0]["pending_reason"] = "Catalogue event is absent."
    with pytest.raises(MomentDocumentError, match="BTS is pending"):
        import_moments(pending, artists={"bts"}, dry_run=True)
    with pytest.raises(MomentDocumentError, match="Unknown selected artist"):
        import_moments(pending, artists={"unknown"}, dry_run=True)
