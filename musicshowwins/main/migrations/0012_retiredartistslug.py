"""Keep merged-away artist URLs working by pointing them at the merged page.

Migrations 0009 and 0011 deleted the duplicate pages below; their links now
resolve to the artist that absorbed them.
"""

import django.db.models.deletion
from django.db import migrations, models

# (retired slug, slug of the merged page)
RETIRED = (
    ("kim-sung-kyu", "kim-sung-kyu-2"),
    ("wjsn", "cosmic-girls"),
    ("i-dle", "gi-dle"),
    ("bap-2", "bap"),
    ("im-chang-jung-2", "im-chang-jung"),
    ("jung-yonghwa", "jung-yong-hwa"),
)


def forwards(apps, schema_editor):
    Artist = apps.get_model("main", "Artist")
    RetiredArtistSlug = apps.get_model("main", "RetiredArtistSlug")
    for slug, target_slug in RETIRED:
        target = Artist.objects.filter(slug=target_slug).first()
        # A fresh database assigns slugs anew, so a live page may own the slug.
        if target is None or Artist.objects.filter(slug=slug).exists():
            continue
        RetiredArtistSlug.objects.get_or_create(slug=slug, defaults={"artist": target})


class Migration(migrations.Migration):
    dependencies = [
        ("main", "0011_merge_split_artists_and_songs"),
    ]

    operations = [
        migrations.CreateModel(
            name="RetiredArtistSlug",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("slug", models.SlugField(max_length=220, unique=True)),
                (
                    "artist",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="retired_slugs",
                        to="main.artist",
                    ),
                ),
            ],
            options={
                "ordering": ("slug",),
            },
        ),
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
