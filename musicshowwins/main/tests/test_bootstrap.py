from datetime import date

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from main.models import (
    Artist,
    ArtistAlias,
    ImportIssue,
    ImportRun,
    MusicShow,
    Song,
    SourcePage,
    Win,
)


@pytest.mark.django_db
def test_bootstrap_restores_exact_domain_dataset(capsys):
    call_command("restore_bootstrap")

    assert MusicShow.objects.count() == 6
    assert Artist.objects.count() == 296
    assert Song.objects.count() == 901
    assert Win.objects.count() == 2965
    assert ArtistAlias.objects.count() == 2
    assert not SourcePage.objects.exists()
    assert not ImportRun.objects.exists()
    assert not ImportIssue.objects.exists()

    assert set(ArtistAlias.objects.values_list("alias", "artist__name")) == {
        ("BigBang", "Big Bang"),
        ("Akdong Musician", "AKMU"),
    }
    assert not ArtistAlias.objects.filter(alias="Blackpink and Selena Gomez").exists()
    assert Win.objects.filter(source_type=Win.SourceType.LEGACY).count() == 2965
    assert Win.objects.filter(source_revision__isnull=False).count() == 0
    assert Win.objects.values_list("date", flat=True).order_by("date").first() >= date(
        2014, 1, 1
    )
    assert Win.objects.values_list("date", flat=True).order_by("-date").first() == date(
        2025, 8, 12
    )
    assert all(
        win.song.artist_id and win.show_id
        for win in Win.objects.select_related("song__artist", "show")
    )
    capsys.readouterr()


@pytest.mark.django_db
def test_bootstrap_requires_empty_domain_tables():
    MusicShow.objects.create(slug="music-bank", name="Music Bank")

    with pytest.raises(CommandError, match="empty domain tables"):
        call_command("restore_bootstrap")

    assert MusicShow.objects.count() == 1
    assert Artist.objects.count() == 0
