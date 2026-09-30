"""Correct presence for Music Bank's postponed 2025-03-28 episode.

The episode aired on 2025-04-04 instead, with NMIXX winning and performing an
encore (KBS clip dated 250404). The 2025-04-04 chart winner, Ten, was only
announced on the website (Soompi, 2025-04-04), so no broadcast exists to judge
presence by. The presence export crediting the 04-04 lineup to Ten is fixed in
operator-tools; the import cannot clear a flag, hence this migration.
"""

from datetime import date

from django.db import migrations


def forwards(apps, schema_editor):
    Win = apps.get_model("main", "Win")
    wins = Win.objects.filter(show__slug="music-bank")
    wins.filter(date=date(2025, 3, 28)).update(performed=True)
    wins.filter(date=date(2025, 4, 4)).update(performed=None)


class Migration(migrations.Migration):
    dependencies = [("main", "0012_retiredartistslug")]

    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
