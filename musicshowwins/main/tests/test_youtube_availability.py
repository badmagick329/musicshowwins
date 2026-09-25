import json
from datetime import date, datetime, timezone
from io import StringIO
from unittest.mock import patch

import pytest
import requests
from django.core.management import call_command
from django.core.management.base import CommandError

from main.models import Artist, MusicShow, Song, Win, WinReference
from main.youtube_availability import check_youtube_references

NOW = datetime(2026, 9, 26, 4, 0, tzinfo=timezone.utc)


class FakeResponse:
    def __init__(self, payload, status=200):
        self.payload = payload
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, statuses, fail=False):
        self.statuses = statuses
        self.fail = fail
        self.batches = []

    def get(self, url, params, timeout):
        ids = params["id"].split(",")
        self.batches.append(ids)
        if self.fail:
            return FakeResponse({"error": {"message": "quotaExceeded"}}, 403)
        return FakeResponse(
            {
                "items": [
                    {"id": video_id, "status": self.statuses[video_id]}
                    for video_id in ids
                    if video_id in self.statuses
                ]
            }
        )


@pytest.fixture
def win(db):
    show = MusicShow.objects.create(slug="music-bank", name="Music Bank")
    song = Song.objects.create(
        artist=Artist.objects.create(name="Alpha"), title="First"
    )
    return Win.objects.create(show=show, song=song, date=date(2026, 1, 2))


def reference(win, video_id, status=WinReference.Status.ACTIVE, provider="youtube"):
    return WinReference.objects.create(
        win=win,
        reference_type=WinReference.ReferenceType.VIDEO,
        provider=provider,
        external_id=video_id,
        url=f"https://www.youtube.com/watch?v={video_id}",
        status=status,
    )


def test_hides_unwatchable_videos_and_restores_returning_ones(win):
    public = reference(win, "public")
    private = reference(win, "private")
    deleted = reference(win, "deleted")
    rejected = reference(win, "rejected")
    returned = reference(win, "returned", WinReference.Status.UNAVAILABLE)
    withdrawn = reference(win, "withdrawn", WinReference.Status.WITHDRAWN)
    other = reference(win, "naver-id", provider="naver")
    session = FakeSession(
        {
            "public": {"privacyStatus": "public", "uploadStatus": "processed"},
            "private": {"privacyStatus": "private", "uploadStatus": "processed"},
            "rejected": {"privacyStatus": "public", "uploadStatus": "rejected"},
            "returned": {"privacyStatus": "unlisted", "uploadStatus": "processed"},
            "withdrawn": {"privacyStatus": "public", "uploadStatus": "processed"},
        }
    )

    summary = check_youtube_references("key", session=session, now=NOW)

    assert (summary.checked, summary.became_unavailable, summary.restored) == (5, 3, 1)
    statuses = {item.external_id: item.status for item in WinReference.objects.all()}
    assert statuses == {
        "public": "active",
        "private": "unavailable",
        "deleted": "unavailable",
        "rejected": "unavailable",
        "returned": "active",
        "withdrawn": "withdrawn",
        "naver-id": "active",
    }
    for item in (public, private, deleted, rejected, returned):
        item.refresh_from_db()
        assert item.last_verified_at == NOW
    withdrawn.refresh_from_db()
    other.refresh_from_db()
    assert withdrawn.last_verified_at is None and other.last_verified_at is None


def test_looks_up_videos_in_batches_of_fifty(win):
    for index in range(51):
        reference(win, f"v{index:02d}")
    session = FakeSession({})

    check_youtube_references("key", session=session, now=NOW, dry_run=True)

    assert [len(batch) for batch in session.batches] == [50, 1]
    assert set(WinReference.objects.values_list("status", flat=True)) == {"active"}


def test_failed_lookup_changes_nothing(win, settings):
    settings.YOUTUBE_API_KEY = "key"
    reference(win, "gone")
    with patch(
        "main.youtube_availability.requests.Session",
        return_value=FakeSession({}, fail=True),
    ):
        with pytest.raises(CommandError, match="lookup failed"):
            call_command("check_win_references")
    assert WinReference.objects.get().status == "active"


def test_command_refreshes_cache_only_after_changes(win, settings):
    settings.YOUTUBE_API_KEY = "key"
    reference(win, "gone")
    output = StringIO()
    with (
        patch(
            "main.youtube_availability.requests.Session", return_value=FakeSession({})
        ),
        patch(
            "main.management.commands.check_win_references.invalidate_public_archive_cache"
        ) as refresh,
    ):
        call_command("check_win_references", stdout=output)
        call_command("check_win_references", stdout=StringIO())

    assert refresh.call_count == 1
    assert "1 became unavailable" in output.getvalue()


def test_command_requires_api_key(db, settings):
    settings.YOUTUBE_API_KEY = ""
    with pytest.raises(CommandError, match="YOUTUBE_API_KEY"):
        call_command("check_win_references")


def test_manifest_import_keeps_production_availability(win, tmp_path):
    checked = datetime(2026, 9, 20, tzinfo=timezone.utc)
    WinReference.objects.create(
        win=win,
        reference_type="video",
        provider="youtube",
        external_id="gone",
        url="https://www.youtube.com/watch?v=gone",
        status=WinReference.Status.UNAVAILABLE,
        last_verified_at=checked,
    )
    document = {
        "version": 1,
        "references": [
            {
                "win": {"show": "music-bank", "date": "2026-01-02"},
                "reference_type": "video",
                "provider": "youtube",
                "external_id": "gone",
                "url": "https://www.youtube.com/watch?v=gone",
                "status": "active",
                "last_verified_at": "2026-08-31T12:00:00Z",
            }
        ],
    }
    path = tmp_path / "references.json"
    path.write_text(json.dumps(document), encoding="utf-8")

    call_command("import_win_references", str(path), stdout=StringIO())

    stored = WinReference.objects.get()
    assert (stored.status, stored.last_verified_at) == ("unavailable", checked)
