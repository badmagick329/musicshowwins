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
    url = "https://en.wikipedia.org/wiki/List_of_M_Countdown_Chart_winners_(2022)"
    data = s.read(url)
    songs = [x["Song"] for x in data]
    assert songs.count("Candy") == 1
    assert songs.count("Still Life") == 3
    assert songs.count("Yet to Come") == 3
    assert songs.count("Pink Venom") == 3
    assert songs.count("Shut Down") == 3
    assert songs.count("Wa Da Da") == 2


def test_wins_2021():
    s = WikiScraper(log_level=LOG_LEVEL)
    url = "https://en.wikipedia.org/wiki/List_of_M_Countdown_Chart_winners_(2021)"
    data = s.read(url)
    songs = [x["Song"] for x in data]
    assert songs.count("Hwaa") == 3
    assert songs.count("Hot Sauce") == 3
    assert songs.count("Dumb Dumb") == 1
    assert songs.count("Favorite (Vampire)") == 2
