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
    data = s.show_wins(2013, "music_bank")
    if not data:
        pytest.fail("No data returned")
    songs = [x["Song"] for x in data]
    artists = [x["Artist"] for x in data]
    assert songs.count("Gangnam Style") == 1
    assert songs.count("I Got a Boy") == 3
    assert songs.count("U&I") == 2
    assert artists.count("Girls' Generation") == 3
    assert artists.count("Exo") == 4


def test_wins_2014():
    s = WikiScraper(log_level=LOG_LEVEL)
    data = s.show_wins(2014, "music_bank")
    if not data:
        pytest.fail("No data returned")
    songs = [x["Song"] for x in data]
    artists = [x["Artist"] for x in data]
    assert songs.count("Luv") == 4
    assert songs.count("You You You") == 1
    assert songs.count("Last Romeo") == 2
    assert artists.count("Infinite") == 2


def test_wins_2015():
    s = WikiScraper(log_level=LOG_LEVEL)
    data = s.show_wins(2015, "music_bank")
    if not data:
        pytest.fail("No data returned")
    songs = [x["Song"] for x in data]
    artists = [x["Artist"] for x in data]
    assert songs.count("I") == 3
    assert songs.count("Let's Not Fall in Love") == 1
    assert songs.count("Up & Down") == 2
    assert artists.count("Exo") == 9


def test_wins_2016():
    s = WikiScraper(log_level=LOG_LEVEL)
    data = s.show_wins(2016, "music_bank")
    if not data:
        pytest.fail("No data returned")
    songs = [x["Song"] for x in data]
    artists = [x["Artist"] for x in data]
    assert songs.count("Whatta Man (Good Man)") == 1
    assert songs.count("Cheer Up") == 5
    assert artists.count("Twice") == 10


def test_wins_2017():
    s = WikiScraper(log_level=LOG_LEVEL)
    data = s.show_wins(2017, "music_bank")
    if not data:
        pytest.fail("No data returned")
    songs = [x["Song"] for x in data]
    artists = [x["Artist"] for x in data]
    assert songs.count("Palette") == 2
    assert songs.count("Pretend") == 2
    assert artists.count("Twice") == 9
    assert artists.count("IU") == 2


def test_wins_2018():
    s = WikiScraper(log_level=LOG_LEVEL)
    data = s.show_wins(2018, "music_bank")
    if not data:
        pytest.fail("No data returned")
    songs = [x["Song"] for x in data]
    artists = [x["Artist"] for x in data]
    assert songs.count("Universe") == 2
    assert songs.count("Fake Love") == 3
    assert artists.count("Red Velvet") == 3
    assert artists.count("Monsta X") == 1


def test_wins_2019():
    s = WikiScraper(log_level=LOG_LEVEL)
    data = s.show_wins(2019, "music_bank")
    if not data:
        pytest.fail("No data returned")
    songs = [x["Song"] for x in data]
    artists = [x["Artist"] for x in data]
    assert songs.count("Icy") == 2
    assert songs.count("Boy with Luv") == 7
    assert artists.count("BTS") == 7


def test_wins_2020():
    s = WikiScraper(log_level=LOG_LEVEL)
    data = s.show_wins(2020, "music_bank")
    if not data:
        pytest.fail("No data returned")
    songs = [x["Song"] for x in data]
    artists = [x["Artist"] for x in data]
    assert songs.count("On") == 4
    assert songs.count("Psycho") == 3
    assert artists.count("Red Velvet") == 3
    assert artists.count("Twice") == 3


def test_wins_2021():
    s = WikiScraper(log_level=LOG_LEVEL)
    data = s.show_wins(2021, "music_bank")
    if not data:
        pytest.fail("No data returned")
    songs = [x["Song"] for x in data]
    artists = [x["Artist"] for x in data]
    assert songs.count("Celebrity") == 4
    assert songs.count("Permission to Dance") == 2
    assert artists.count("IU") == 5
    assert artists.count("BTS") == 8


def test_wins_2022():
    s = WikiScraper(log_level=LOG_LEVEL)
    data = s.show_wins(2022, "music_bank")
    if not data:
        pytest.fail("No data returned")
    songs = [x["Song"] for x in data]
    artists = [x["Artist"] for x in data]
    assert songs.count("Sneakers") == 1
    assert songs.count("After Like") == 4
    assert artists.count("Kep1er") == 2
    assert artists.count("Ive") == 9


@pytest.mark.skip(reason="Avoid unnecessary requests")
def test_wins_2023():
    s = WikiScraper(log_level=LOG_LEVEL)
    data = s.show_wins(2023, "music_bank")
    if not data:
        pytest.fail("No data returned")
    songs = [x["Song"] for x in data]
    assert songs.count("OMG") == 1
    assert songs.count("Ditto") == 1
    assert songs.count("Queencard") == 2
