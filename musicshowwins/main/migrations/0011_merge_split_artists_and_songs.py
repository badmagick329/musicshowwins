"""Merge acts and songs that Wikipedia spelled differently across show pages.

Each split left a thin duplicate page and understated the real act or song.
Merged artists keep the larger page's slug so its URLs survive; the other
spelling becomes an alias so syncs resolve it. WJSN and I-dle take their
current names over the pre-rename credits "Cosmic Girls" and "(G)I-dle".
Songs merge into the title with more wins (official spelling on ties), and the
importer maps each variant to it. Songs and artists left without wins are
parse artefacts ("‹See TfM›" titles, rejected candidates) and are removed.
"""

import re
import unicodedata

from django.db import migrations

# (merged-away credit, credit that owns the kept page, final name)
ARTIST_MERGES = (
    ("WJSN", "Cosmic Girls", "WJSN"),
    ("I-dle", "(G)I-dle", "I-dle"),
    ("B.A.P.", "B.A.P", "B.A.P"),
    ("Im Chang Jung", "Im Chang-jung", "Im Chang-jung"),
    ("Jung Yonghwa", "Jung Yong-hwa", "Jung Yong-hwa"),
)

# (artist after ARTIST_MERGES, final title, variant titles)
SONG_MERGES = (
    ("Girls' Generation", "Mr.Mr.", ("Mr. Mr.",)),
    ("EXID", "L.I.E.", ("L.I.E",)),
    ("NU'EST", "I'm in Trouble", ("I’m in Trouble",)),
    ("Hyuna", "How's This?", ("How's This",)),
    ("Epik High", "Lovedrunk", ("Love Drunk",)),
    ("Niel", "Lovekiller", ("Love Killer", "Lovekiller (Bad Girl)")),
    ("I-dle", "Hann (Alone)", ("Hann",)),
    ("Oh My Girl", "Bungee (Fall in Love)", ("Bungee", "Bungee (Fall In Love)")),
    ("I.O.I", "Whatta Man", ("Whatta Man (Good Man)",)),
    ("Shinhwa", "Sniper", ("Sniper (Target)",)),
    ("NCT U", "Universe (Let's Play Ball)", ("Universe",)),
    ("Enhypen", "Future Perfect", ("Future Perfect (Pass the MIC)",)),
    ("WayV", "Frequency", ("Frequency (Korean Ver.)",)),
)


def _text(value):
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", value or "")).strip()


def _key(value):
    return _text(value).casefold()


def _move_songs(Song, Win, source, target):
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


def merge_artists(Artist, ArtistAlias, Song, Win):
    for source_name, target_name, final_name in ARTIST_MERGES:
        target = Artist.objects.filter(identity_key=_key(target_name)).first()
        if target is None:
            continue
        source = Artist.objects.filter(identity_key=_key(source_name)).first()
        if source is not None:
            _move_songs(Song, Win, source, target)
            source.delete()
        target.name = final_name
        target.identity_key = _key(final_name)
        target.save(update_fields=("name", "identity_key"))
        for alias in {source_name, target_name} - {final_name}:
            ArtistAlias.objects.update_or_create(
                normalized_name=_key(alias),
                defaults={"alias": alias, "artist": target},
            )


def merge_songs(Artist, Song, Win):
    for artist_name, title, variants in SONG_MERGES:
        artist = Artist.objects.filter(identity_key=_key(artist_name)).first()
        if artist is None:
            continue
        songs = list(
            Song.objects.filter(
                artist=artist,
                normalized_title__in={_key(t) for t in (title, *variants)},
            )
        )
        if not songs:
            continue
        keeper = next((s for s in songs if s.normalized_title == _key(title)), songs[0])
        for song in songs:
            if song.pk != keeper.pk:
                Win.objects.filter(song=song).update(song=keeper)
                song.delete()
        keeper.title = title
        keeper.normalized_title = _key(title)
        keeper.save(update_fields=("title", "normalized_title"))


def drop_winless(Artist, Song):
    Song.objects.filter(wins__isnull=True).delete()
    Artist.objects.filter(songs__isnull=True).delete()


def forwards(apps, schema_editor):
    Artist = apps.get_model("main", "Artist")
    Song = apps.get_model("main", "Song")
    Win = apps.get_model("main", "Win")
    merge_artists(Artist, apps.get_model("main", "ArtistAlias"), Song, Win)
    merge_songs(Artist, Song, Win)
    drop_winless(Artist, Song)


class Migration(migrations.Migration):
    dependencies = [("main", "0010_rename_young_tak_gogo")]

    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
