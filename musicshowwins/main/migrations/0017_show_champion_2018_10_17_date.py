"""Move iKON's Show Champion EP.289 win from 2018-10-14 to the day it aired.

Show Champion airs on Wednesdays and EP.289 aired 2018-10-17 (Chosun's
same-day win report and Reddit's episode page), but the Wikipedia page repeats
that week's Inkigayo date, October 14. `SOURCE_DATE_CORRECTIONS` in
`main/wikipedia.py` keeps the sync from adding it back on the source date.
"""

from datetime import date

from django.db import migrations


def forwards(apps, schema_editor):
    Win = apps.get_model("main", "Win")
    wins = Win.objects.filter(show__slug="show-champion")
    if wins.filter(date=date(2018, 10, 17)).exists():
        raise RuntimeError("Show Champion 2018-10-17 already has a win")
    wins.filter(date=date(2018, 10, 14), song__artist__identity_key="ikon").update(
        date=date(2018, 10, 17)
    )


class Migration(migrations.Migration):
    dependencies = [("main", "0016_show_champion_2024_07_03_date")]

    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
