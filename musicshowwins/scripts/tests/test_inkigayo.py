import sys
from pathlib import Path

import pytest

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))
from wikiscraper import WikiScraper, logging

LOG_LEVEL = logging.CRITICAL


def test_wins_2013():
    s = WikiScraper(log_level=LOG_LEVEL)
    data = s.show_wins(2013, "inkigayo")
    if not data:
        pytest.fail("No data returned")
    songs = [x["Song"] for x in data]
    artists = [x["Artist"] for x in data]
    assert songs.count("It's Over") == 1
    assert songs.count("Give It To Me") == 2
    assert songs.count("Female President") == 1


def test_wins_2014():
    s = WikiScraper(log_level=LOG_LEVEL)
    data = s.show_wins(2014, "inkigayo")
    if not data:
        pytest.fail("No data returned")
    songs = [x["Song"] for x in data]
    artists = [x["Artist"] for x in data]
    assert songs.count("Friday") == 1
    assert songs.count("Something") == 3
    assert artists.count("Girl's Day") == 3
    assert artists.count("TVXQ") == 1
    assert songs.count("Darling") == 1
    assert songs.count("200%") == 3
    assert songs.count("12:30") == 2
    assert songs.count("Luv") == 3


def test_wins_2015():
    s = WikiScraper(log_level=LOG_LEVEL)
    data = s.show_wins(2015, "inkigayo")
    if not data:
        pytest.fail("No data returned")
    songs = [x["Song"] for x in data]
    assert songs.count("Good Boy") == 1
    assert songs.count("Up & Down") == 1
    assert songs.count("You from the Same Time") == 1
    assert songs.count("Call Me Baby") == 3
    assert songs.count("Loser") == 3
    assert songs.count("Bang Bang Bang") == 2
    assert songs.count("I") == 3


def test_wins_2016():
    s = WikiScraper(log_level=LOG_LEVEL)
    data = s.show_wins(2016, "inkigayo")
    if not data:
        pytest.fail("No data returned")
    songs = [x["Song"] for x in data]
    assert songs.count("Again") == 1
    assert songs.count("Lonely Night") == 1
    assert songs.count("Dream") == 3


def test_wins_2017():
    s = WikiScraper(log_level=LOG_LEVEL)
    data = s.show_wins(2017, "inkigayo")
    if not data:
        pytest.fail("No data returned")
    songs = [x["Song"] for x in data]
    assert songs.count("Fxxk It") == 2
    assert songs.count("Rookie") == 2
    assert songs.count("Knock Knock") == 3
    assert songs.count("Gashina") == 3
    assert songs.count("Snow") == 1


def test_wins_2018():
    s = WikiScraper(log_level=LOG_LEVEL)
    data = s.show_wins(2018, "inkigayo")
    if not data:
        pytest.fail("No data returned")
    songs = [x["Song"] for x in data]
    assert songs.count("Heart Shaker") == 1
    assert songs.count("Heroine") == 2
    assert songs.count("Starry Night") == 3
    assert songs.count("Dance the Night Away") == 3
    assert songs.count("Idol") == 3
    assert songs.count("Yes or Yes") == 1


def test_wins_2019():
    s = WikiScraper(log_level=LOG_LEVEL)
    data = s.show_wins(2019, "inkigayo")
    if not data:
        pytest.fail("No data returned")
    songs = [x["Song"] for x in data]
    assert songs.count("Dalla Dalla") == 3
    assert songs.count("Zimzalabim") == 1
    assert songs.count("Hip") == 3
    assert songs.count("Icy") == 2
    assert songs.count("Blueming") == 3


def test_wins_2020():
    s = WikiScraper(log_level=LOG_LEVEL)
    data = s.show_wins(2020, "inkigayo")
    if not data:
        pytest.fail("No data returned")
    songs = [x["Song"] for x in data]
    assert songs.count("Psycho") == 3
    assert songs.count("I Can't Stop Me") == 2
    assert songs.count("Life Goes On") == 3


def test_wins_2021():
    s = WikiScraper(log_level=LOG_LEVEL)
    data = s.show_wins(2021, "inkigayo")
    if not data:
        pytest.fail("No data returned")
    songs = [x["Song"] for x in data]
    assert songs.count("Celebrity") == 3
    assert songs.count("Hello Future") == 1
    assert songs.count("Queendom") == 2
    assert songs.count("Savage") == 3
    assert songs.count("Scientist") == 1


def test_wins_2022():
    s = WikiScraper(log_level=LOG_LEVEL)
    data = s.show_wins(2022, "inkigayo")
    if not data:
        pytest.fail("No data returned")
    songs = [x["Song"] for x in data]
    assert songs.count("Eleven") == 3
    assert songs.count("INVU") == 3
    assert songs.count("Love Dive") == 3
    assert songs.count("Tomboy") == 3
    assert songs.count("Pop!") == 3
    assert songs.count("Sneakers") == 1


@pytest.mark.skip(reason="Avoid unnecessary requests")
def test_wins_2023():
    s = WikiScraper(log_level=LOG_LEVEL)
    data = s.show_wins(2023, "inkigayo")
    if not data:
        pytest.fail("No data returned")
    songs = [x["Song"] for x in data]
    assert songs.count("Ditto") == 3
    assert songs.count("OMG") == 3
    assert songs.count("Hype Boy") == 1
    assert songs.count("Kitsch") == 1
    assert songs.count("I Am") == 3
    assert songs.count("Flower") == 3
