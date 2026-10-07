"""Move TWS's Show Champion EP.524 win from 2024-07-04 to the day it aired.

Show Champion airs on Wednesdays and EP.524 aired 2024-07-03 (MBC Plus TOP5
post, the official 240703 encore upload and Reddit's episode page), but the
Wikipedia page dates it July 4. `SOURCE_DATE_CORRECTIONS` in `main/wikipedia.py`
keeps the sync from adding it back on the source date. Moving the row keeps its
references attached.
"""

from datetime import date

from django.db import migrations


def forwards(apps, schema_editor):
    Win = apps.get_model("main", "Win")
    wins = Win.objects.filter(show__slug="show-champion")
    if wins.filter(date=date(2024, 7, 3)).exists():
        raise RuntimeError("Show Champion 2024-07-03 already has a win")
    wins.filter(
        date=date(2024, 7, 4), song__artist__identity_key="tws"
    ).update(date=date(2024, 7, 3))


class Migration(migrations.Migration):
    dependencies = [("main", "0015_episodestatus")]

    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
