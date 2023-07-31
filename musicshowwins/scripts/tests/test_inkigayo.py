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
    url = "https://en.wikipedia.org/wiki/List_of_Inkigayo_Chart_winners_(2023)"
    data = s.read(url)
    songs = [x["Song"] for x in data]
    assert songs.count("Ditto") == 3
    assert songs.count("OMG") == 3
    assert songs.count("Hype Boy") == 1
    assert songs.count("Kitsch") == 1
    assert songs.count("I Am") == 3
    assert songs.count("Flower") == 3


def test_wins_2022():
    s = WikiScraper(log_level=LOG_LEVEL)
    url = "https://en.wikipedia.org/wiki/List_of_Inkigayo_Chart_winners_(2022)"
    data = s.read(url)
    songs = [x["Song"] for x in data]
    assert songs.count("Eleven") == 3
    assert songs.count("INVU") == 3
    assert songs.count("Love Dive") == 3
    assert songs.count("Tomboy") == 3
    assert songs.count("Pop!") == 3
    assert songs.count("Sneakers") == 1

def test_wins_2021():
    s = WikiScraper(log_level=LOG_LEVEL)
    url = "https://en.wikipedia.org/wiki/List_of_Inkigayo_Chart_winners_(2021)"
    data = s.read(url)
    songs = [x["Song"] for x in data]
    assert songs.count("Celebrity") == 3
    assert songs.count("Hello Future") == 1
    assert songs.count("Queendom") == 2
    assert songs.count("Savage") == 3
    assert songs.count("Scientist") == 1


def test_wins_2020():
    s = WikiScraper(log_level=LOG_LEVEL)
    url = "https://en.wikipedia.org/wiki/List_of_Inkigayo_Chart_winners_(2020)"
    data = s.read(url)
    songs = [x["Song"] for x in data]
    assert songs.count("Psycho") == 3
    assert songs.count("I Can't Stop Me") == 2
    assert songs.count("Life Goes On") == 3

def test_wins_2019():
    s = WikiScraper(log_level=LOG_LEVEL)
    url = "https://en.wikipedia.org/wiki/List_of_Inkigayo_Chart_winners_(2019)"
    data = s.read(url)
    songs = [x["Song"] for x in data]
    assert songs.count("Dalla Dalla") == 3
    assert songs.count("Zimzalabim") == 1
    assert songs.count("Hip") == 3
    assert songs.count("Icy") == 2
    assert songs.count("Blueming") == 3


def test_wins_2018():
    s = WikiScraper(log_level=LOG_LEVEL)
    url = "https://en.wikipedia.org/wiki/List_of_Inkigayo_Chart_winners_(2018)"
    data = s.read(url)
    songs = [x["Song"] for x in data]
    assert songs.count("Heart Shaker") == 1
    assert songs.count("Heroine") == 2
    assert songs.count("Starry Night") == 3
    assert songs.count("Dance the Night Away") == 3
    assert songs.count("Idol") == 3
    assert songs.count("Yes or Yes") == 1


def test_wins_2017():
    s = WikiScraper(log_level=LOG_LEVEL)
    url = "https://en.wikipedia.org/wiki/List_of_Inkigayo_Chart_winners_(2017)"
    data = s.read(url)
    songs = [x["Song"] for x in data]
    assert songs.count("Fxxk It") == 2
    assert songs.count("Rookie") == 2
    assert songs.count("Knock Knock") == 3
    assert songs.count("Gashina") == 3
    assert songs.count("Snow") == 1
