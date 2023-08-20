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


def chart(artist_name: str) -> str:
    if CONTAINERED:
        static_root = STATIC_ROOT
    else:
        static_root = BASE_DIR / "main" / "static"
    graphs_dir = static_root / "images" / "graphs"
    file_name = f"{artist_name}_wins.png"
    if (graphs_dir / file_name).exists():
        create_time = (graphs_dir / file_name).stat().st_ctime
        if datetime.now().timestamp() - create_time < 3600:
            print(f"Returning cached {file_name}")
            return file_name
    print(f"Creating new {file_name}")
    wins = (
        Win.objects.filter(song__artist__name__iexact=artist_name)
        .annotate(wins=models.Count("song__win"))
        .order_by("-wins")
    )
    wins_dict = {}
    for w in wins:
        wins_dict[w.song.name] = w.wins
    df = pd.DataFrame.from_dict(wins_dict, orient="index", columns=["wins"])
    df = df.sort_values(by="wins", ascending=False)
    fig, ax = plt.subplots()
    fig.set_size_inches(12, 8)
    ax.bar(df.index, df.wins, color="C3")
    ax.set_yticks(range(1, df.wins.max() + 1, 1))
    ax.set_ylabel("Wins", rotation=0, labelpad=20)
    ax.set_title(f"{artist_name} Music Show Wins")
    ax.grid(axis="y")
    ax.tick_params("x", labelrotation=75)
    fig.subplots_adjust(bottom=0.22)
    fig.savefig((graphs_dir / file_name), dpi=300)
    return file_name


if __name__ == "__main__":
    os.environ["DJANGO_SETTINGS_MODULE"] = "musicshowwins.settings"
    django.setup()
    chart("Twice")
