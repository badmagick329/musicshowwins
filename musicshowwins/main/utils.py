import os
import sys
from datetime import datetime
from pathlib import Path

import django
import pandas as pd
from django.db import models
from django.db.models import QuerySet
from matplotlib import pyplot as plt

from main.models import Artist, Song, Win

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))
if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "musicshowwins.settings")
    django.setup()

from main.models import Artist, Win
from musicshowwins.settings import CONTAINERED, STATIC_ROOT

plt.style.use("dark_background")
if CONTAINERED:
    STATIC_DIR = STATIC_ROOT
else:
    STATIC_DIR = BASE_DIR / "main" / "static"
CHARTS_DIR = STATIC_DIR / "images" / "charts"
CACHE_SECONDS = 3600


def song_chart(artist_name: str) -> tuple[str, dict[str, str]]:
    file_name = f"{artist_name}_wins.png"
    wins = Win.objects.filter(song__artist__name__iexact=artist_name)
    song_years = dict()
    for song in wins.values("song__name", "year"):
        song_years.setdefault(song["song__name"], song["year"])
        if song["year"] < song_years[song["song__name"]]:
            song_years[song["song__name"]] = song["year"]
    win_values = (
        wins.annotate(wins=models.Count("song__win"))
        .values("song__name", "wins")
        .order_by("-wins")
        .distinct()
    )
    df = pd.DataFrame.from_records(win_values, columns=["song__name", "wins"])
    total_wins = df.wins.sum()
    if cached_file(file_name):
        return file_name, {"total_wins": total_wins}
    df.song__name = df.song__name.apply(lambda x: f"{x} ({song_years[x]})")
    fig, ax = plt.subplots()
    width, height = chart_dims(df.song__name, df.wins)
    fig.set_size_inches(width, height)
    ax.bar(df.song__name, df.wins, color="C3")
    ax.set_yticks(range(1, df.wins.max() + 1, 1))
    ax.set_ylabel("Wins", rotation=0, labelpad=20)
    ax.set_title(f"{artist_name} Song Wins")
    ax.grid(axis="y")
    ax.tick_params("x", labelrotation=65)
    fig.subplots_adjust(bottom=0.28)
    fig.savefig((CHARTS_DIR / file_name), dpi=300)
    return file_name, {"total_wins": total_wins}


def year_chart(artist_name: str) -> tuple[str, dict[str, str]]:
    file_name = f"{artist_name}_year_wins.png"
    year_values = (
        Win.objects.filter(song__artist__name__iexact=artist_name)
        .values("year")
        .annotate(wins=models.Count("id"))
        .order_by("year")
    )
    df = pd.DataFrame.from_records(year_values, columns=["year", "wins"])
    if cached_file(file_name):
        return file_name, {"best_year": df.wins.idxmax()}
    fig, ax = plt.subplots()
    width, height = chart_dims(df.year, df.wins)
    fig.set_size_inches(width, height)
    ax.bar(df.year, df.wins, color="C3")
    ax.set_yticks(range(1, df.wins.max() + 1, 1))
    ax.set_ylabel("Wins", rotation=0, labelpad=20)
    ax.set_title(f"{artist_name} Yearly Wins")
    ax.grid(axis="y")
    ax.tick_params("x", labelrotation=45)
    ax.set_xticks(df.year)
    fig.subplots_adjust(bottom=0.10)
    fig.savefig((CHARTS_DIR / file_name), dpi=300)
    return file_name, {"best_year": df.wins.idxmax()}


def cached_file(file_name: str) -> str | None:
    if (CHARTS_DIR / file_name).exists():
        create_time = (CHARTS_DIR / file_name).stat().st_ctime
        if datetime.now().timestamp() - create_time < CACHE_SECONDS:
            return file_name


def chart_dims(row, y_counts):
    if len(row) > 8:
        width = 12
    elif len(row) < 4:
        width = 6
    else:
        width = 10
    if y_counts.max() > 40:
        height = 12
    elif y_counts.max() > 30:
        height = 10
    elif y_counts.max() < 10:
        height = 7
    else:
        height = 8
    print(f"{width=} {height=}")
    return width, height


def chart_test(artist_name: str):
    year_values = (
        Win.objects.filter(song__artist__name__iexact=artist_name)
        .values("year")
        .annotate(wins=models.Count("id"))
        .order_by("year")
    )
    print(year_values.query.get_compiler("default").as_sql())
    df = pd.DataFrame.from_records(year_values, columns=["year", "wins"], index="year")
    print(df.head(10))
    fig, ax = plt.subplots()
    fig.set_size_inches(12, 8)
    ax.bar(df.index, df.wins, color="C3")
    ax.set_yticks(range(1, df.wins.max() + 1, 1))
    ax.set_ylabel("Wins", rotation=0, labelpad=20)
    ax.set_title(f"{artist_name} Wins for each year")
    ax.grid(axis="y")
    ax.tick_params("x", labelrotation=75)
    ax.set_xticks(df.index)
    fig.subplots_adjust(bottom=0.22)
    fig.savefig((CHARTS_DIR / f"chart_test.png"), dpi=300)


def add_ranks(items: QuerySet[Artist | Song]):
    """Assumes the queryset is sorted by wins in descending order"""
    rank = None
    previous_win_count = None
    for item in items:
        if rank is None:
            rank = 1
            item.rank = rank
            previous_win_count = item.wins
            continue
        if item.wins < previous_win_count:
            rank += 1
        item.rank = rank
        previous_win_count = item.wins


if __name__ == "__main__":
    chart_test("Twice")
