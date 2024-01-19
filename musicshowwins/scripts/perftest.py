import os
import sys
from pathlib import Path
from time import perf_counter

DJANGO_DIR = Path(__file__).resolve().parent.parent
if str(DJANGO_DIR) not in sys.path:
    sys.path.append(str(DJANGO_DIR))

os.environ["DJANGO_SETTINGS_MODULE"] = "musicshowwins.settings"
import django

django.setup()
from main.models import Win


def main():
    print("Starting performance test...")
    print("Getting top songs")
    start = perf_counter()
    _ = Win.top_songs()
    print(f"Got top songs in {(perf_counter() - start):.5f} seconds")
    print("Getting top songs by year")
    start = perf_counter()
    for year in range(2014, 2023):
        _ = Win.top_songs(year=year)
    end = perf_counter()
    num_years = len(range(2014, 2023))
    print(
        f"Got top songs by year in {((end - start)/num_years):.5f} seconds. "
        f"({num_years} years)"
    )
    print("Getting top songs by an artist")
    start = perf_counter()
    _ = Win.top_songs(artist="IU")
    end = perf_counter()
    print(f"Got top songs by an artist in {(end - start):.5f} seconds")


if __name__ == "__main__":
    main()
