from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name="PublicReadBudget",
            fields=[
                (
                    "scope",
                    models.CharField(max_length=32, primary_key=True, serialize=False),
                ),
                ("window", models.BigIntegerField()),
                ("count", models.PositiveIntegerField(default=0)),
            ],
        ),
    ]
