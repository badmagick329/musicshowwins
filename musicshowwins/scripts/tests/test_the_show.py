import sys
from pathlib import Path
import pytest

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))
from scraper import WikiScraper, logging

LOG_LEVEL = logging.CRITICAL


def test_wins_2022():
    s = WikiScraper(log_level=LOG_LEVEL)
    url = "https://en.wikipedia.org/wiki/List_of_The_Show_Chart_winners_(2022)"
    data = s.read(url)
    songs = [x["Song"] for x in data]
    assert songs.count("DM") == 1
    assert songs.count("Candy Sugar Pop") == 1
    assert songs.count("Run2U") == 2
    assert songs.count("Guerrilla") == 2


def test_wins_2021():
    s = WikiScraper(log_level=LOG_LEVEL)
    url = "https://en.wikipedia.org/wiki/List_of_The_Show_Chart_winners_(2021)"
    data = s.read(url)
    songs = [x["Song"] for x in data]
    assert songs.count("Savage") == 1
    assert songs.count("Dun Dun Dance") == 2
