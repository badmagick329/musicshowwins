from datetime import date, timedelta

import pytest
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.test import Client, RequestFactory
from django.urls import reverse
from django.utils import timezone

from main.admin import (
    ImportIssueAdmin,
    WinAdmin,
    WinReferenceAdmin,
    WinReferenceInline,
)
from main.models import Artist, ImportIssue, MusicShow, Song, Win, WinReference


def _admin_client() -> Client:
    user = get_user_model().objects.create_superuser(
        username="admin", email="admin@example.com", password="test-password"
    )
    client = Client()
    client.force_login(user)
    return client


def _legacy_discrepancy(**candidate_overrides) -> ImportIssue:
    candidate = {
        "date": "2025-06-25",
        "show": "show-champion",
        "artist": "Xlov",
        "song": "Bizness",
        "retained": {"artist": "Kang Daniel", "song": "Episode"},
    }
    candidate.update(candidate_overrides)
    return ImportIssue.objects.create(
        issue_type=ImportIssue.IssueType.LEGACY_DISCREPANCY,
        candidate=candidate,
        notes="Current Wikipedia credits Kang Daniel as the winner.",
    )


@pytest.mark.django_db
def test_import_issue_changelist_explains_legacy_records():
    issue = _legacy_discrepancy()

    response = _admin_client().get(reverse("admin:main_importissue_changelist"))

    assert response.status_code == 200
    content = response.content.decode()
    assert "Legacy discrepancy" in content
    assert "2025-06-25" in content
    assert "Show Champion" in content
    assert "Xlov — Bizness" in content
    assert "Kang Daniel — Episode" in content
    assert "Current Wikipedia credits Kang Daniel" in content
    assert "Needs review" in content
    assert str(issue.pk) in content


@pytest.mark.django_db
def test_import_issue_changelist_searches_candidate_and_evidence():
    _legacy_discrepancy()

    response = _admin_client().get(
        reverse("admin:main_importissue_changelist"), {"q": "Kang Daniel"}
    )

    assert response.status_code == 200
    assert response.context["cl"].result_count == 1


@pytest.mark.django_db
def test_import_issue_detail_uses_labeled_escaped_fields_not_raw_json():
    issue = _legacy_discrepancy(
        artist="<script>alert('x')</script>",
        song="Song & title",
    )

    response = _admin_client().get(
        reverse("admin:main_importissue_change", args=(issue.pk,))
    )

    assert response.status_code == 200
    content = response.content.decode()
    assert "Quarantined candidate" in content
    assert "Current public record" in content
    assert "Xlov" not in content
    assert "&lt;script&gt;alert(&#x27;x&#x27;)&lt;/script&gt;" in content
    assert "Song &amp; title" in content
    assert '"date": "2025-06-25"' not in content
    assert "Exact dates" not in content


@pytest.mark.django_db
def test_legacy_undated_detail_explains_aggregate_status():
    issue = ImportIssue.objects.create(
        issue_type=ImportIssue.IssueType.LEGACY_UNDATED,
        candidate={
            "show": "music-core",
            "year": 2016,
            "artist": "EXO",
            "song": "Monster",
            "expected_wins": 3,
        },
        notes="Restored from aggregate-only history.",
    )

    response = _admin_client().get(
        reverse("admin:main_importissue_change", args=(issue.pk,))
    )
    content = response.content.decode()

    assert "2016" in content
    assert "Music Core" in content
    assert "EXO" in content
    assert "Monster" in content
    assert "3" in content
    assert "Exact dates are unknown" in content
    assert "not a public dated win" in content


@pytest.mark.django_db
def test_import_issue_resolution_choices_are_durable_and_evidence_is_read_only():
    issue = _legacy_discrepancy()
    admin_obj = ImportIssueAdmin(ImportIssue, AdminSite())
    request = RequestFactory().get("/")
    request.user = get_user_model().objects.create_superuser(
        username="admin", email="admin@example.com", password="test-password"
    )

    form = admin_obj.get_form(request, issue)()
    choices = dict(form.fields["resolution"].choices)

    assert choices[ImportIssue.Resolution.OPEN] == "Needs review"
    assert choices[ImportIssue.Resolution.ACCEPTED] == "Candidate accepted"
    assert choices[ImportIssue.Resolution.REJECTED] == "Keep current public record"
    assert not {
        "issue_type",
        "candidate",
        "source_page",
        "notes",
    }.intersection(form.base_fields)

    accepted_issue = _legacy_discrepancy()
    accepted_issue.resolution = ImportIssue.Resolution.ACCEPTED
    accepted_help = admin_obj.decision_help(accepted_issue)
    assert "accepted as correct" in accepted_help
    assert "does not itself rewrite Win data" in accepted_help
    assert "still required" not in accepted_help


@pytest.mark.django_db
def test_import_issue_admin_maintains_resolved_at_without_changing_wins():
    admin_obj = ImportIssueAdmin(ImportIssue, AdminSite())
    request = RequestFactory().post("/")
    request.user = get_user_model().objects.create_superuser(
        username="admin", email="admin@example.com", password="test-password"
    )

    issue = _legacy_discrepancy()
    admin_obj.save_model(request, issue, None, change=True)
    issue.refresh_from_db()
    assert issue.resolved_at is None

    issue.resolution = ImportIssue.Resolution.ACCEPTED
    before = timezone.now()
    admin_obj.save_model(request, issue, None, change=True)
    issue.refresh_from_db()
    assert issue.resolved_at is not None
    assert issue.resolved_at >= before - timedelta(seconds=1)

    original_timestamp = issue.resolved_at
    issue.resolution = ImportIssue.Resolution.REJECTED
    admin_obj.save_model(request, issue, None, change=True)
    issue.refresh_from_db()
    assert issue.resolved_at == original_timestamp

    issue.resolution = ImportIssue.Resolution.OPEN
    admin_obj.save_model(request, issue, None, change=True)
    issue.refresh_from_db()
    assert issue.resolved_at is None


@pytest.mark.django_db
def test_win_reference_admin_list_filters_and_search():
    show = MusicShow.objects.create(slug="music-bank", name="Music Bank")
    artist = Artist.objects.create(name="Alpha")
    song = Song.objects.create(artist=artist, title="First")
    win = Win.objects.create(show=show, song=song, date=date(2026, 1, 2))
    reference = WinReference.objects.create(
        win=win,
        reference_type="video",
        provider="youtube",
        external_id="abc123",
        url="https://www.youtube.com/watch?v=abc123",
        title="Winner stage",
        publisher_name="KBS Kpop",
        is_official=True,
    )
    client = _admin_client()

    response = client.get(reverse("admin:main_winreference_changelist"))
    filtered = client.get(
        reverse("admin:main_winreference_changelist"),
        {"status__exact": "active", "q": "Alpha"},
    )

    assert response.status_code == filtered.status_code == 200
    content = response.content.decode()
    assert "Music Bank" in content
    assert "Alpha" in content
    assert "First" in content
    assert "Winner stage" in content
    assert "KBS Kpop" in content
    assert str(reference.pk) in content
    assert filtered.context["cl"].result_count == 1

    admin_obj = WinReferenceAdmin(WinReference, AdminSite())
    assert admin_obj.autocomplete_fields == ("win",)
    assert set(admin_obj.readonly_fields) == {
        "discovered_at",
        "created_at",
        "updated_at",
    }
    assert set(admin_obj.list_filter) == {
        "reference_type",
        "provider",
        "is_official",
        "status",
        "win__show",
        "win__date",
    }


@pytest.mark.django_db
def test_win_admin_exposes_compact_reference_inline():
    show = MusicShow.objects.create(slug="music-bank", name="Music Bank")
    artist = Artist.objects.create(name="Alpha")
    song = Song.objects.create(artist=artist, title="First")
    win = Win.objects.create(show=show, song=song, date=date(2026, 1, 2))
    WinReference.objects.create(
        win=win,
        reference_type="article",
        provider="publisher",
        url="https://example.com/article",
    )

    response = _admin_client().get(reverse("admin:main_win_change", args=(win.pk,)))

    assert response.status_code == 200
    assert WinReferenceInline in WinAdmin.inlines
    content = response.content.decode()
    assert "Win references" in content
    assert "https://example.com/article" in content
