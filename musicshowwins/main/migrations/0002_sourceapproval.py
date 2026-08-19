from django.db import migrations, models
import django.db.models.deletion
from django.utils import timezone


def approve_existing_source_pages(apps, schema_editor):
    SourceApproval = apps.get_model("main", "SourceApproval")
    SourcePage = apps.get_model("main", "SourcePage")
    for source in SourcePage.objects.all().iterator():
        SourceApproval.objects.create(
            show_id=source.show_id,
            year=source.year,
            approved=True,
            approved_at=source.last_synced_at or timezone.now(),
            approved_by="migration",
            notes="Approved because this source page was already synced before approval gating.",
        )


def remove_seeded_approvals(apps, schema_editor):
    SourceApproval = apps.get_model("main", "SourceApproval")
    SourceApproval.objects.filter(approved_by="migration").delete()


class Migration(migrations.Migration):
    dependencies = [("main", "0001_initial")]

    operations = [
        migrations.CreateModel(
            name="SourceApproval",
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
                ("year", models.PositiveSmallIntegerField()),
                ("approved", models.BooleanField(default=False)),
                ("approved_at", models.DateTimeField(blank=True, null=True)),
                ("approved_by", models.CharField(blank=True, max_length=150)),
                ("notes", models.TextField(blank=True)),
                (
                    "show",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="source_approvals",
                        to="main.musicshow",
                    ),
                ),
            ],
            options={"ordering": ("-year", "show__name")},
        ),
        migrations.AddConstraint(
            model_name="sourceapproval",
            constraint=models.UniqueConstraint(
                fields=("show", "year"), name="unique_source_approval_show_year"
            ),
        ),
        migrations.RunPython(approve_existing_source_pages, remove_seeded_approvals),
    ]
