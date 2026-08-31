import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("main", "0003_resolve_historical_issues")]

    operations = [
        migrations.CreateModel(
            name="WinReference",
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
                (
                    "reference_type",
                    models.CharField(
                        choices=[
                            ("video", "Video"),
                            ("article", "Article"),
                            ("other", "Other"),
                        ],
                        max_length=20,
                    ),
                ),
                ("provider", models.CharField(max_length=80)),
                ("external_id", models.CharField(blank=True, max_length=255)),
                ("url", models.URLField(max_length=2048)),
                ("title", models.CharField(blank=True, max_length=500)),
                ("publisher_name", models.CharField(blank=True, max_length=300)),
                (
                    "publisher_external_id",
                    models.CharField(blank=True, max_length=255),
                ),
                ("is_official", models.BooleanField(default=False)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("active", "Active"),
                            ("unavailable", "Unavailable"),
                        ],
                        default="active",
                        max_length=20,
                    ),
                ),
                ("published_at", models.DateTimeField(blank=True, null=True)),
                ("discovered_at", models.DateTimeField(auto_now_add=True)),
                ("last_verified_at", models.DateTimeField(blank=True, null=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "win",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="references",
                        to="main.win",
                    ),
                ),
            ],
            options={
                "ordering": ("win__date", "provider", "external_id", "url"),
                "indexes": [
                    models.Index(
                        fields=["win", "status"],
                        name="main_winref_win_status_idx",
                    ),
                    models.Index(
                        fields=["reference_type", "provider"],
                        name="main_winref_type_provider_idx",
                    ),
                    models.Index(
                        fields=["provider", "external_id"],
                        name="main_winref_provider_ext_idx",
                    ),
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("win", "url"), name="unique_win_reference_url"
                    ),
                    models.UniqueConstraint(
                        condition=models.Q(("external_id", ""), _negated=True),
                        fields=("win", "provider", "external_id"),
                        name="unique_win_reference_provider_external_id",
                    ),
                ],
            },
        )
    ]
