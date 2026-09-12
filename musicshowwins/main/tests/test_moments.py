import json
from copy import deepcopy
from datetime import date
from unittest.mock import patch

import pytest
from django.core.exceptions import ValidationError
from django.core.management import call_command

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
                "matching_state": "matched",
                "status": "published",
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
    assert import_moments(document, dry_run=True) == (1, 0, 0)
    assert WinMoment.objects.count() == 0
    assert import_moments(document) == (1, 0, 0)
    assert import_moments(document) == (0, 0, 1)
    assert WinMoment.objects.get(win=win).status == "published"
    assert WinReference.objects.count() == 1


@pytest.mark.django_db
def test_import_normalizes_validated_text_without_mutating_document(moment_document):
    win, document = moment_document
    entry = document["moments"][0]
    entry["event"] = {key: f" {value} " for key, value in entry["event"].items()}
    entry["heading"] = "  A sourced heading  "
    entry["citations"][0]["provider"] = "  SOOMPI  "
    original = deepcopy(document)

    assert import_moments(document, dry_run=True) == (1, 0, 0)
    assert import_moments(document) == (1, 0, 0)
    assert document == original
    moment = WinMoment.objects.get(win=win)
    assert moment.heading == "A sourced heading"
    assert moment.citations.get().provider == "soompi"


@pytest.mark.django_db
@pytest.mark.parametrize("version", [True, 1.0, "1"])
def test_document_version_must_be_an_integer(moment_document, version):
    _, document = moment_document
    document["version"] = version

    with pytest.raises(MomentDocumentError, match="version 1"):
        import_moments(document, dry_run=True)


@pytest.mark.django_db
def test_malformed_matching_state_raises_a_document_error(moment_document):
    _, document = moment_document
    document["moments"][0]["matching_state"] = ["matched"]

    with pytest.raises(MomentDocumentError, match="state must be matched or pending"):
        import_moments(document, dry_run=True)


@pytest.mark.django_db
@pytest.mark.parametrize("dry_run", [True, False])
def test_duplicate_moment_events_are_rejected_before_writing(moment_document, dry_run):
    _, document = moment_document
    duplicate = deepcopy(document["moments"][0])
    duplicate["heading"] = "Conflicting heading"
    document["moments"].append(duplicate)

    with pytest.raises(MomentDocumentError, match="Entry 2: duplicate event"):
        import_moments(document, dry_run=dry_run, update_existing=True)

    assert WinMoment.objects.count() == WinReference.objects.count() == 0


@pytest.mark.django_db
def test_selected_artist_cannot_hide_pending_entry_behind_matched_entry(
    moment_document,
):
    _, document = moment_document
    pending = deepcopy(document["moments"][0])
    pending["event"]["date"] = "2015-05-06"
    pending["matching_state"] = "pending"
    pending["pending_reason"] = "Catalogue event is absent."
    document["moments"].insert(0, pending)

    with pytest.raises(MomentDocumentError, match="BTS is pending"):
        import_moments(document, artists={"bts"})

    assert WinMoment.objects.count() == 0


@pytest.mark.django_db
def test_reverse_citation_links_require_the_same_win(moment_document):
    win, _ = moment_document
    other = Win.objects.create(show=win.show, song=win.song, date=date(2015, 5, 6))
    moment = WinMoment.objects.create(win=win, heading="Story", body="Body")
    wrong_reference = WinReference.objects.create(
        win=other,
        reference_type="article",
        provider="source",
        url="https://example.com/other",
    )
    right_reference = WinReference.objects.create(
        win=win,
        reference_type="article",
        provider="source",
        url="https://example.com/right",
    )

    right_reference.moments.add(moment)
    assert list(moment.citations.all()) == [right_reference]
    with pytest.raises(ValidationError, match="same win"):
        wrong_reference.moments.add(moment)


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
    document["moments"][0]["status"] = "draft"
    import_moments(document)
    from rest_framework.test import APIClient

    assert APIClient().get("/api/v1/wins").data["results"][0]["moment"] is None
    document["moments"][0]["status"] = "published"
    import_moments(document, update_existing=True)
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
    pending["moments"][0]["matching_state"] = "pending"
    pending["moments"][0]["pending_reason"] = "Catalogue event is absent."
    with pytest.raises(MomentDocumentError, match="BTS is pending"):
        import_moments(pending, artists={"bts"}, dry_run=True)
    with pytest.raises(MomentDocumentError, match="Unknown selected artist"):
        import_moments(pending, artists={"unknown"}, dry_run=True)


@pytest.mark.django_db
def test_deployment_sync_replaces_editorial_changes_and_reference_state(
    moment_document,
):
    win, document = moment_document
    import_moments(document)
    moment = WinMoment.objects.get(win=win)
    reference = moment.citations.get()
    moment.heading = "Editor heading"
    moment.body = "Editor body"
    moment.status = WinMoment.Status.DRAFT
    moment.save()
    reference.title = "Editor reference title"
    reference.status = WinReference.Status.UNAVAILABLE
    reference.save()

    assert import_moments(document, update_existing=True) == (0, 1, 0)
    moment.refresh_from_db()
    reference.refresh_from_db()
    assert (moment.heading, moment.body, moment.status) == (
        "BTS's first win",
        "A sourced story.",
        WinMoment.Status.PUBLISHED,
    )
    assert reference.title == "Report"
    assert reference.status == WinReference.Status.ACTIVE
    assert list(moment.citations.values_list("pk", flat=True)) == [reference.pk]

    assert import_moments(document, update_existing=True) == (0, 1, 0)
    assert WinMoment.objects.count() == 1
    assert WinReference.objects.count() == 1

    document["moments"][0]["status"] = "draft"
    assert import_moments(document, update_existing=True) == (0, 1, 0)
    moment.refresh_from_db()
    reference.refresh_from_db()
    assert moment.heading == "BTS's first win"
    assert moment.status == WinMoment.Status.DRAFT
    assert reference.title == "Report"
    assert reference.status == WinReference.Status.ACTIVE

    assert import_moments({"version": 1, "moments": []}, update_existing=True) == (
        0,
        0,
        0,
    )
    assert WinMoment.objects.filter(pk=moment.pk).exists()


@pytest.mark.django_db
def test_deployment_sync_skips_unavailable_cache_revalidation(
    moment_document, tmp_path
):
    _, document = moment_document
    path = tmp_path / "moments.json"
    path.write_text(json.dumps(document), encoding="utf-8")

    with patch(
        "main.management.commands.import_win_moments.invalidate_public_archive_cache",
        side_effect=RuntimeError("frontend and API are unavailable"),
    ) as invalidate:
        call_command(
            "import_win_moments",
            str(path),
            update_existing=True,
            skip_cache_revalidation=True,
        )

    invalidate.assert_not_called()
    assert WinMoment.objects.get().status == WinMoment.Status.PUBLISHED
