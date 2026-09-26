from django.db import migrations, models
from django.utils.text import slugify


def assign_slugs(apps, schema_editor):
    Artist = apps.get_model("main", "Artist")
    taken: set[str] = set()
    # ID order gives the longest-standing artist the unsuffixed slug.
    for artist in Artist.objects.order_by("pk"):
        base = slugify(artist.name) or "artist"
        if base.isdigit():
            base = f"{base}-artist"
        slug, suffix = base, 2
        while slug in taken:
            slug, suffix = f"{base}-{suffix}", suffix + 1
        taken.add(slug)
        artist.slug = slug
        artist.save(update_fields=("slug",))


class Migration(migrations.Migration):
    dependencies = [("main", "0007_win_performed")]

    operations = [
        migrations.AddField(
            model_name="artist",
            name="slug",
            field=models.SlugField(max_length=220, null=True, db_index=False),
        ),
        migrations.RunPython(assign_slugs, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="artist",
            name="slug",
            field=models.SlugField(max_length=220, unique=True),
        ),
    ]
