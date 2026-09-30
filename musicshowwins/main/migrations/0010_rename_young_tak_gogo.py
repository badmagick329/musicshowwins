"""Rename Young Tak's 2026 Music Bank winner from "Gogo" to "Kkeokgeo".

Wikipedia credits the album *GOGO*; the winning title track is 꺾어 (Sports
Kyunghyang track list, 2026-09-14). The importer maps the Wikipedia title to
the same canonical one, so future syncs match this song.
"""

from django.db import migrations

ARTIST = "young tak"
SOURCE_TITLE = "gogo"
TITLE = "Kkeokgeo"


def forwards(apps, schema_editor):
    Song = apps.get_model("main", "Song")
    # The historical model lacks Song.save(), so set the normalized key here.
    Song.objects.filter(
        artist__identity_key=ARTIST, normalized_title=SOURCE_TITLE
    ).update(title=TITLE, normalized_title=TITLE.casefold())


class Migration(migrations.Migration):
    dependencies = [("main", "0009_merge_kim_sung_kyu_drop_no1_specials")]

    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
