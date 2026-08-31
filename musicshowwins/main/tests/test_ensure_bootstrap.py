from datetime import date

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from main.management.commands.ensure_bootstrap import Command
from main.models import Artist, ArtistAlias, MusicShow, Song, Win


@pytest.mark.django_db
def test_completely_empty_archive_is_detected():
    assert Command._archive_is_empty()


@pytest.mark.django_db
def test_first_run_restores_the_tracked_bootstrap():
    call_command("ensure_bootstrap")
    assert MusicShow.objects.count() == 6
    assert Artist.objects.count() == 292
    assert Song.objects.count() == 882
    assert Win.objects.count() == 2905
    assert ArtistAlias.objects.count() == 4


@pytest.mark.django_db
def test_later_run_is_a_noop(capsys):
    call_command("ensure_bootstrap")
    counts = tuple(model.objects.count() for model in (MusicShow, Artist, Song, Win))
    call_command("ensure_bootstrap")
    assert (
        tuple(model.objects.count() for model in (MusicShow, Artist, Song, Win))
        == counts
    )
    assert "already present" in capsys.readouterr().out


@pytest.mark.django_db
def test_archive_above_the_baseline_is_accepted():
    call_command("restore_bootstrap")
    show = MusicShow.objects.create(slug="extra-show", name="Extra Show")
    artist = Artist.objects.create(name="Extra Artist")
    song = Song.objects.create(artist=artist, title="Extra Song")
    Win.objects.create(show=show, song=song, date=date(2026, 1, 1))

    call_command("ensure_bootstrap")

    assert Artist.objects.filter(name="Extra Artist").exists()
    assert Win.objects.filter(show=show, date=date(2026, 1, 1)).exists()


@pytest.mark.django_db
def test_partial_archive_is_rejected():
    call_command("restore_bootstrap")
    Win.objects.order_by("date").first().delete()

    with pytest.raises(CommandError, match="complete bootstrap baseline is missing"):
        call_command("ensure_bootstrap")
