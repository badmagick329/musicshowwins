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
    data = s.show_wins(2013, "mcountdown")
    if not data:
        pytest.fail("No data returned")
    songs = [x["Song"] for x in data]
    assert songs.count("Caffeine") == 1
    assert songs.count("I Got a Boy") == 3
    assert songs.count("Dream Girl") == 3
    assert songs.count("Gentleman") == 3
    assert songs.count("Everybody") == 1
    assert songs.count("Hush") == 1


def test_wins_2014():
    s = WikiScraper(log_level=LOG_LEVEL)
    data = s.show_wins(2014, "mcountdown")
    if not data:
        pytest.fail("No data returned")
    songs = [x["Song"] for x in data]
    artists = [x["Artist"] for x in data]
    assert songs.count("Miracles in December") == 1
    assert songs.count("Something") == 5
    assert artists.count("Girl's Day") == 2
    assert artists.count("TVXQ") == 3
    assert songs.count("Come Back Home") == 2
    assert songs.count("200%") == 3
    assert songs.count("Eyes, Nose, Lips") == 3
    assert songs.count("Empty") == 3


def test_wins_2015():
    s = WikiScraper(log_level=LOG_LEVEL)
    data = s.show_wins(2015, "mcountdown")
    if not data:
        pytest.fail("No data returned")
    songs = [x["Song"] for x in data]
    assert songs.count("Up & Down") == 2
    assert songs.count("Love Equation") == 1
    assert songs.count("Sniper") == 3
    assert songs.count("Bang Bang Bang") == 2
    assert songs.count("Daddy") == 2


def test_wins_2016():
    s = WikiScraper(log_level=LOG_LEVEL)
    data = s.show_wins(2016, "mcountdown")
    if not data:
        pytest.fail("No data returned")
    songs = [x["Song"] for x in data]
    assert songs.count("Daddy") == 1
    assert songs.count("Dumb & Dumber") == 3
    assert songs.count("Cheer Up") == 3
    assert songs.count("Monster") == 3
    assert songs.count("TT") == 2


def test_wins_2017():
    s = WikiScraper(log_level=LOG_LEVEL)
    data = s.show_wins(2017, "mcountdown")
    if not data:
        pytest.fail("No data returned")
    songs = [x["Song"] for x in data]
    assert songs.count("Fxxk It") == 2
    assert songs.count("Last Goodbye") == 1
    assert songs.count("Excuse Me") == 1
    assert songs.count("Rookie") == 2
    assert songs.count("Knock Knock") == 2
    assert songs.count("Yes I Am") == 3


def test_wins_2018():
    s = WikiScraper(log_level=LOG_LEVEL)
    data = s.show_wins(2018, "mcountdown")
    if not data:
        pytest.fail("No data returned")
    songs = [x["Song"] for x in data]
    assert songs.count("Bboom Bboom") == 2
    assert songs.count("Love Scenario") == 3
    assert songs.count("Light") == 1
    assert songs.count("Yes or Yes") == 1


def test_wins_2019():
    s = WikiScraper(log_level=LOG_LEVEL)
    data = s.show_wins(2019, "mcountdown")
    if not data:
        pytest.fail("No data returned")
    songs = [x["Song"] for x in data]
    assert songs.count("Millions") == 1
    assert songs.count("%% (Eung Eung)") == 1
    assert songs.count("Home") == 3
    assert songs.count("Icy") == 2
    assert songs.count("Hip") == 2


def test_wins_2020():
    s = WikiScraper(log_level=LOG_LEVEL)
    data = s.show_wins(2020, "mcountdown")
    if not data:
        pytest.fail("No data returned")
    songs = [x["Song"] for x in data]
    assert songs.count("Wannabe") == 3
    assert songs.count("Not Shy") == 3
    assert songs.count("More & More") == 1
    assert songs.count("How You Like That") == 2
    assert songs.count("Aya") == 1


def test_wins_2021():
    s = WikiScraper(log_level=LOG_LEVEL)
    data = s.show_wins(2021, "mcountdown")
    if not data:
        pytest.fail("No data returned")
    songs = [x["Song"] for x in data]
    assert songs.count("Hwaa") == 3
    assert songs.count("Hot Sauce") == 3
    assert songs.count("Dumb Dumb") == 1
    assert songs.count("Favorite (Vampire)") == 2


def test_wins_2022():
    s = WikiScraper(log_level=LOG_LEVEL)
    data = s.show_wins(2022, "mcountdown")
    if not data:
        pytest.fail("No data returned")
    songs = [x["Song"] for x in data]
    assert songs.count("Candy") == 1
    assert songs.count("Still Life") == 3
    assert songs.count("Yet to Come") == 3
    assert songs.count("Pink Venom") == 3
    assert songs.count("Shut Down") == 3
    assert songs.count("Wa Da Da") == 2


@pytest.mark.skip(reason="Avoid unnecessary requests")
def test_wins_2023():
    s = WikiScraper(log_level=LOG_LEVEL)
    data = s.show_wins(2023, "mcountdown")
    if not data:
        pytest.fail("No data returned")
    songs = [x["Song"] for x in data]
    assert songs.count("OMG") == 2
    assert songs.count("On the Street") == 2
    assert songs.count("Vibe") == 1
    assert songs.count("Flower") == 1
