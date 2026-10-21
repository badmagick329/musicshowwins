from django.db import models


class PublicReadBudget(models.Model):
    """One fixed row bounds public frontend misses across API processes."""

    scope = models.CharField(max_length=32, primary_key=True)
    window = models.BigIntegerField()
    count = models.PositiveIntegerField(default=0)
