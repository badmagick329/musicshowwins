"""Add GOT7's Show Champion EP.287 win, which the source page omits.

EP.287 aired 2018-10-03 with a chart that GOT7's "Lullaby" won (Herald POP's
same-night report), but the Wikipedia page spans September 26's "No Chart and
Winner" over it. `SOURCE_OMITTED_WINS` in `main/wikipedia.py` makes the sync
expect the win. A fresh database has no show yet; its bootstrap adds the win.
"""

from datetime import date

from django.db import migrations

AIRED = date(2018, 10, 3)


def forwards(apps, schema_editor):
    MusicShow = apps.get_model("main", "MusicShow")
    Song = apps.get_model("main", "Song")
    Win = apps.get_model("main", "Win")
    EpisodeStatus = apps.get_model("main", "EpisodeStatus")
    show = MusicShow.objects.filter(slug="show-champion").first()
    if show is None:
        return
    if Win.objects.filter(show=show, date=AIRED).exists():
        raise RuntimeError("Show Champion 2018-10-03 already has a win")
    song = Song.objects.get(artist__identity_key="got7", normalized_title="lullaby")
    Win.objects.create(show=show, song=song, date=AIRED)
    EpisodeStatus.objects.filter(show=show, date=AIRED).delete()


class Migration(migrations.Migration):
    dependencies = [("main", "0017_show_champion_2018_10_17_date")]

    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
