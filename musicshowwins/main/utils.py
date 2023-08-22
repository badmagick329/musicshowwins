import os
import sys
from datetime import datetime
from pathlib import Path

import django
import pandas as pd
from django.db import models
from matplotlib import pyplot as plt

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from main.models import Artist, Win
from musicshowwins.settings import CONTAINERED, STATIC_ROOT

plt.style.use("dark_background")
if CONTAINERED:
    STATIC_DIR = STATIC_ROOT
else:
    STATIC_DIR = BASE_DIR / "main" / "static"
CACHE_FOR = 3600 # seconds


def song_chart(artist_name: str) -> str:
    graphs_dir = STATIC_DIR / "images" / "graphs"
    file_name = f"{artist_name}_wins.png"
    if (graphs_dir / file_name).exists():
        create_time = (graphs_dir / file_name).stat().st_ctime
        if datetime.now().timestamp() - create_time < CACHE_FOR:
            return file_name
    win_values = (
        Win.objects.filter(song__artist__name__iexact=artist_name)
        .annotate(wins=models.Count("song__win"))
        .values("song__name", "wins")
        .order_by("-wins")
        .distinct()
    )
    df = pd.DataFrame.from_records(
        win_values, columns=["song__name", "wins"], index="song__name"
    )
    total_wins = df.wins.sum()
    fig, ax = plt.subplots()
    fig.set_size_inches(10, 7)
    ax.bar(df.index, df.wins, color="C3")
    ax.set_yticks(range(1, df.wins.max() + 1, 1))
    ax.set_ylabel("Wins", rotation=0, labelpad=20)
    ax.set_title(f"{artist_name} Wins - Total: {total_wins}")
    ax.grid(axis="y")
    ax.tick_params("x", labelrotation=75)
    fig.subplots_adjust(bottom=0.22)
    fig.savefig((graphs_dir / file_name), dpi=300)
    return file_name


if __name__ == "__main__":
    os.environ["DJANGO_SETTINGS_MODULE"] = "musicshowwins.settings"
    django.setup()
    song_chart("Twice")
