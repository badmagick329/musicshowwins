"""Correct two Wikipedia sync artefacts that distorted win counts.

"Kim Sung Kyu" (Music Core 2015 page) and "Kim Sung-kyu" (The Show and Music
Bank pages) are one soloist, split across two thin artist pages. The hyphenated
spelling matches his Wikipedia article and already owns the indexed page, so it
keeps its slug; the alias routes the other spelling to it on future syncs.

M Countdown's "No.1 Special" episodes (2015-01-01, 2018-08-16) were imported as
winners although no act won; the parser now skips them.
"""

from django.db import migrations

CANONICAL = "Kim Sung-kyu"
VARIANT = "Kim Sung Kyu"
SPECIAL_EPISODE_ARTISTS = ("No.1 Special", "M Countdown No.1 Special")


def _key(value):
    return " ".join((value or "").split()).casefold()


def merge_kim_sung_kyu(Artist, ArtistAlias, Song, Win):
    target = Artist.objects.filter(identity_key=_key(CANONICAL)).first()
    source = Artist.objects.filter(identity_key=_key(VARIANT)).first()
    if target is None or source is None:
        return
    for song in Song.objects.filter(artist=source):
        existing = Song.objects.filter(
            artist=target, normalized_title=song.normalized_title
        ).first()
        if existing is None:
            song.artist = target
            song.save(update_fields=("artist",))
            continue
        Win.objects.filter(song=song).update(song=existing)
        song.delete()
    source.delete()
    ArtistAlias.objects.get_or_create(
        normalized_name=_key(VARIANT),
        defaults={"alias": VARIANT, "artist": target},
    )


def drop_special_episodes(Artist):
    # Cascades to their placeholder songs and wins.
    Artist.objects.filter(
        identity_key__in=[_key(name) for name in SPECIAL_EPISODE_ARTISTS]
    ).delete()


def forwards(apps, schema_editor):
    Artist = apps.get_model("main", "Artist")
    merge_kim_sung_kyu(
        Artist,
        apps.get_model("main", "ArtistAlias"),
        apps.get_model("main", "Song"),
        apps.get_model("main", "Win"),
    )
    drop_special_episodes(Artist)


class Migration(migrations.Migration):
    dependencies = [("main", "0008_artist_slug")]

    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
