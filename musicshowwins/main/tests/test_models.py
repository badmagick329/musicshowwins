from datetime import date

import pytest
from django.db import IntegrityError, transaction

from main.models import (
    Artist,
    ArtistAlias,
    MusicShow,
    Song,
    SourcePage,
    Win,
    WinReference,
)


def test_model_text_fields_use_nfkc_and_whitespace_normalization(db):
    show = MusicShow.objects.create(slug="Music Bank", name="  Music\u00a0\tBank  ")
    artist = Artist.objects.create(name="  Ａｌｐｈａ\u00a0\t Beta  ")
    song = Song.objects.create(artist=artist, title="  Ｆｉｒｓｔ\n Song  ")

    assert show.slug == "music-bank"
    assert show.name == "Music Bank"
    assert artist.name == "Alpha Beta"
    assert artist.identity_key == "alpha beta"
    assert song.title == "First Song"
    assert song.normalized_title == "first song"


def test_identity_and_song_uniqueness_are_database_enforced(db):
    artist = Artist.objects.create(name="Alpha")
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Artist.objects.create(name="  ＡＬＰＨＡ ")

    Song.objects.create(artist=artist, title="First")
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Song.objects.create(artist=artist, title=" first ")


def test_aliases_resolve_to_one_canonical_artist(db):
    artist = Artist.objects.create(name="Big Bang")
    alias = ArtistAlias.objects.create(alias=" BigBang ", artist=artist)

    assert alias.alias == "BigBang"
    assert alias.normalized_name == "bigbang"
    assert artist.aliases.get(normalized_name="bigbang") == alias

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            ArtistAlias.objects.create(alias="BIGBANG", artist=artist)


def test_win_and_source_page_keep_provenance(db):
    show = MusicShow.objects.create(slug="music-bank", name="Music Bank")
    artist = Artist.objects.create(name="Alpha")
    song = Song.objects.create(artist=artist, title="First")
    source = SourcePage.objects.create(
        show=show,
        year=2025,
        page_title="List of Music Bank Chart winners (2025)",
        latest_revision="12345",
    )
    win = Win.objects.create(
        show=show,
        song=song,
        date=date(2025, 1, 3),
        source_type=Win.SourceType.WIKIPEDIA,
        source_page=source,
        source_revision="12345",
    )

    assert win.source_type == Win.SourceType.WIKIPEDIA
    assert win.source_page == source
    assert win.source_revision == "12345"
    assert source.wins.get(pk=win.pk) == win


def test_win_reference_defaults_and_relationship(db):
    show = MusicShow.objects.create(slug="music-bank", name="Music Bank")
    artist = Artist.objects.create(name="Alpha")
    song = Song.objects.create(artist=artist, title="First")
    win = Win.objects.create(show=show, song=song, date=date(2025, 1, 3))

    reference = WinReference.objects.create(
        win=win,
        reference_type=WinReference.ReferenceType.VIDEO,
        provider="youtube",
        url="https://www.youtube.com/watch?v=abc123",
    )

    assert win.references.get() == reference
    assert reference.external_id == ""
    assert reference.is_official is False
    assert reference.status == WinReference.Status.ACTIVE
    assert reference.metadata == {}
    assert reference.discovered_at is not None
    assert reference.created_at is not None
    assert reference.updated_at is not None


def test_win_reference_uniqueness_is_scoped_to_a_win(db):
    show = MusicShow.objects.create(slug="music-bank", name="Music Bank")
    artist = Artist.objects.create(name="Alpha")
    song = Song.objects.create(artist=artist, title="First")
    first_win = Win.objects.create(show=show, song=song, date=date(2025, 1, 3))
    second_win = Win.objects.create(show=show, song=song, date=date(2025, 1, 10))
    values = {
        "reference_type": WinReference.ReferenceType.VIDEO,
        "provider": "youtube",
        "external_id": "abc123",
        "url": "https://example.com/reference",
    }
    WinReference.objects.create(win=first_win, **values)

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            WinReference.objects.create(
                win=first_win,
                **{**values, "external_id": "different"},
            )
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            WinReference.objects.create(
                win=first_win,
                **{**values, "url": "https://example.com/other"},
            )

    same_resource = WinReference.objects.create(win=second_win, **values)
    assert same_resource.win == second_win


def test_blank_external_ids_do_not_conflict(db):
    show = MusicShow.objects.create(slug="music-bank", name="Music Bank")
    artist = Artist.objects.create(name="Alpha")
    song = Song.objects.create(artist=artist, title="First")
    win = Win.objects.create(show=show, song=song, date=date(2025, 1, 3))

    for suffix in ("one", "two"):
        WinReference.objects.create(
            win=win,
            reference_type=WinReference.ReferenceType.OTHER,
            provider="publisher",
            external_id="",
            url=f"https://example.com/{suffix}",
        )

    assert win.references.count() == 2
