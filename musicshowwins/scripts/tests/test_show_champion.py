import logging
import sys
from pathlib import Path

import pytest

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))
from wikiscraper.wikiscraper import WikiScraper

LOG_LEVEL = logging.CRITICAL


def test_wins_2013():
    s = WikiScraper(log_level=LOG_LEVEL)
    data = s.show_wins(2013, "show_champion")
    if not data:
        pytest.fail("No data returned")
    songs = [x["Song"] for x in data]
    artists = [x["Artist"] for x in data]
    assert songs.count("I'm Sorry") == 3
    assert songs.count("Dream Girl") == 4
    assert songs.count("Love, at first") == 2
    assert artists.count("Exo") == 5


def test_wins_2014():
    s = WikiScraper(log_level=LOG_LEVEL)
    data = s.show_wins(2014, "show_champion")
    if not data:
        pytest.fail("No data returned")
    songs = [x["Song"] for x in data]
    artists = [x["Artist"] for x in data]
    assert songs.count("Lonely") == 3
    assert songs.count("Red") == 2
    assert artists.count("Girl's Day") == 2


def test_wins_2015():
    s = WikiScraper(log_level=LOG_LEVEL)
    data = s.show_wins(2015, "show_champion")
    if not data:
        pytest.fail("No data returned")
    songs = [x["Song"] for x in data]
    artists = [x["Artist"] for x in data]
    assert songs.count("Call Me Baby") == 3
    assert songs.count("Ice Cream Cake") == 1
    assert artists.count("Exo") == 6


def test_wins_2016():
    s = WikiScraper(log_level=LOG_LEVEL)
    data = s.show_wins(2016, "show_champion")
    if not data:
        pytest.fail("No data returned")
    songs = [x["Song"] for x in data]
    artists = [x["Artist"] for x in data]
    assert songs.count("Dynamite") == 1
    assert songs.count("Rough") == 3
    assert artists.count("GFriend") == 5


def test_wins_2017():
    s = WikiScraper(log_level=LOG_LEVEL)
    data = s.show_wins(2017, "show_champion")
    if not data:
        pytest.fail("No data returned")
    songs = [x["Song"] for x in data]
    artists = [x["Artist"] for x in data]
    assert songs.count("I'll Be Yours") == 1
    assert songs.count("Signal") == 2
    assert artists.count("Twice") == 4


def test_wins_2018():
    s = WikiScraper(log_level=LOG_LEVEL)
    data = s.show_wins(2018, "show_champion")
    if not data:
        pytest.fail("No data returned")
    songs = [x["Song"] for x in data]
    artists = [x["Artist"] for x in data]
    assert songs.count("What Is Love?") == 3
    assert songs.count("Bad Boy") == 1
    assert artists.count("Red Velvet") == 3


def test_wins_2019():
    s = WikiScraper(log_level=LOG_LEVEL)
    data = s.show_wins(2019, "show_champion")
    if not data:
        pytest.fail("No data returned")
    songs = [x["Song"] for x in data]
    artists = [x["Artist"] for x in data]
    assert songs.count("Violeta") == 2
    assert songs.count("Home") == 2
    assert songs.count("Millions") == 1
    assert songs.count("Flash") == 2
    assert artists.count("Twice") == 3


def test_wins_2020():
    s = WikiScraper(log_level=LOG_LEVEL)
    data = s.show_wins(2020, "show_champion")
    if not data:
        pytest.fail("No data returned")
    songs = [x["Song"] for x in data]
    artists = [x["Artist"] for x in data]
    assert songs.count("On") == 3
    assert songs.count("Fiesta") == 1
    assert songs.count("Love Killa") == 1
    assert artists.count("BTS") == 6


def test_wins_2021():
    s = WikiScraper(log_level=LOG_LEVEL)
    data = s.show_wins(2021, "show_champion")
    if not data:
        pytest.fail("No data returned")
    songs = [x["Song"] for x in data]
    artists = [x["Artist"] for x in data]
    assert songs.count("Celebrity") == 1
    assert songs.count("Maverick") == 1
    assert songs.count("Don't Call Me") == 2
    assert songs.count("Butter") == 3
    assert artists.count("(G)I-dle") == 1


def test_wins_2022():
    s = WikiScraper(log_level=LOG_LEVEL)
    data = s.show_wins(2022, "show_champion")
    if not data:
        pytest.fail("No data returned")
    songs = [x["Song"] for x in data]
    artists = [x["Artist"] for x in data]
    assert songs.count("DM") == 1
    assert songs.count("Tomboy") == 1
    assert songs.count("Shut Down") == 3
    assert songs.count("Case 143") == 2
    assert artists.count("Fromis 9") == 2


@pytest.mark.skip(reason="Avoid unnecessary requests")
def test_wins_2023():
    s = WikiScraper(log_level=LOG_LEVEL)
    data = s.show_wins(2023, "show_champion")
    if not data:
        pytest.fail("No data returned")
    songs = [x["Song"] for x in data]
    assert songs.count("Super") == 1
    assert songs.count("Teddy Bear") == 2
    assert songs.count("Set Me Free") == 1
    assert songs.count("Flower") == 3
    assert songs.count("S-Class") == 2
