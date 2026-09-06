from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("main", "0005_winmoment")]

    operations = [
        migrations.AlterField(
            model_name="winreference",
            name="status",
            field=models.CharField(
                choices=[
                    ("active", "Active"),
                    ("unavailable", "Unavailable"),
                    ("withdrawn", "Withdrawn"),
                ],
                default="active",
                max_length=20,
            ),
        ),
    ]
