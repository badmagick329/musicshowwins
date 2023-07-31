import sys
from pathlib import Path

import pytest

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))
from scraper import WikiScraper, logging

LOG_LEVEL = logging.CRITICAL


@pytest.mark.skip(reason="Avoiding hitting Wikipedia too much")
def test_wins_2023():
    s = WikiScraper(log_level=LOG_LEVEL)
    url = "https://en.wikipedia.org/wiki/List_of_Show_Champion_Chart_winners_(2023)"
    data = s.read(url)
    songs = [x["Song"] for x in data]
    assert songs.count("Super") == 1
    assert songs.count("Teddy Bear") == 2
    assert songs.count("Set Me Free") == 1
    assert songs.count("Flower") == 3
    assert songs.count("S-Class") == 2


def test_wins_2022():
    s = WikiScraper(log_level=LOG_LEVEL)
    url = "https://en.wikipedia.org/wiki/List_of_Show_Champion_Chart_winners_(2022)"
    data = s.read(url)
    songs = [x["Song"] for x in data]
    assert songs.count("DM") == 1
    assert songs.count("Tomboy") == 1
    assert songs.count("Shut Down") == 3
    assert songs.count("Case 143") == 2


def test_wins_2021():
    s = WikiScraper(log_level=LOG_LEVEL)
    url = "https://en.wikipedia.org/wiki/List_of_Show_Champion_Chart_winners_(2021)"
    data = s.read(url)
    songs = [x["Song"] for x in data]
    assert songs.count("Celebrity") == 1
    assert songs.count("Maverick") == 1
    assert songs.count("Don't Call Me") == 2
    assert songs.count("Butter") == 3
