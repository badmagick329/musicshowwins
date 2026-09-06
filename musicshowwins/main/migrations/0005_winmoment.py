from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("main", "0004_winreference")]
    operations = [
        migrations.CreateModel(
            name="WinMoment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("heading", models.CharField(max_length=300)),
                ("body", models.TextField()),
                ("status", models.CharField(choices=[("draft", "Draft"), ("published", "Published")], default="draft", max_length=20)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("citations", models.ManyToManyField(blank=True, related_name="moments", to="main.winreference")),
                ("win", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="moment", to="main.win")),
            ],
            options={"ordering": ("win__date", "pk")},
        )
    ]
