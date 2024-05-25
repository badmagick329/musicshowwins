import logging
import sys
from pathlib import Path

import pytest

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))
from wikiscraper.wikiscraper import WikiScraper

LOG_LEVEL = logging.CRITICAL


def test_wins_2014():
    s = WikiScraper(log_level=LOG_LEVEL)
    data = s.show_wins(2014, "the_show")
    if not data:
        pytest.fail("No data returned")
    songs = [x["Song"] for x in data]
    artists = [x["Artist"] for x in data]
    assert songs.count("Luv") == 3
    assert artists.count("VIXX") == 2


def test_wins_2015():
    s = WikiScraper(log_level=LOG_LEVEL)
    data = s.show_wins(2015, "the_show")
    if not data:
        pytest.fail("No data returned")
    songs = [x["Song"] for x in data]
    artists = [x["Artist"] for x in data]
    assert songs.count("Up & Down") == 1
    assert songs.count("If You Do") == 3
    assert artists.count("EXID") == 2


def test_wins_2016():
    s = WikiScraper(log_level=LOG_LEVEL)
    data = s.show_wins(2016, "the_show")
    if not data:
        pytest.fail("No data returned")
    songs = [x["Song"] for x in data]
    artists = [x["Artist"] for x in data]
    assert songs.count("Rough") == 2
    assert songs.count("Navillera") == 3
    assert artists.count("GFriend") == 5
    assert artists.count("Exo-CBX") == 1


def test_wins_2017():
    s = WikiScraper(log_level=LOG_LEVEL)
    data = s.show_wins(2017, "the_show")
    if not data:
        pytest.fail("No data returned")
    songs = [x["Song"] for x in data]
    artists = [x["Artist"] for x in data]
    assert songs.count("My First and Last") == 3
    assert songs.count("DNA") == 1
    assert artists.count("Red Velvet") == 2


def test_wins_2018():
    s = WikiScraper(log_level=LOG_LEVEL)
    data = s.show_wins(2018, "the_show")
    if not data:
        pytest.fail("No data returned")
    songs = [x["Song"] for x in data]
    artists = [x["Artist"] for x in data]
    assert songs.count("Save Me, Save You") == 1
    assert songs.count("Latata") == 2
    assert artists.count("Oh My Girl") == 2


def test_wins_2019():
    s = WikiScraper(log_level=LOG_LEVEL)
    data = s.show_wins(2019, "the_show")
    if not data:
        pytest.fail("No data returned")
    songs = [x["Song"] for x in data]
    artists = [x["Artist"] for x in data]
    assert songs.count("All Night") == 1
    assert songs.count("Violeta") == 2
    assert artists.count("Iz*One") == 2


def test_wins_2020():
    s = WikiScraper(log_level=LOG_LEVEL)
    data = s.show_wins(2020, "the_show")
    if not data:
        pytest.fail("No data returned")
    songs = [x["Song"] for x in data]
    artists = [x["Artist"] for x in data]
    assert songs.count("Secret Story of the Swan") == 2
    assert songs.count("Apple") == 1
    assert artists.count("Iz*One") == 5


def test_wins_2021():
    s = WikiScraper(log_level=LOG_LEVEL)
    data = s.show_wins(2021, "the_show")
    if not data:
        pytest.fail("No data returned")
    songs = [x["Song"] for x in data]
    artists = [x["Artist"] for x in data]
    assert songs.count("Savage") == 1
    assert songs.count("Dun Dun Dance") == 2
    assert artists.count("Oh My Girl") == 2


def test_wins_2022():
    s = WikiScraper(log_level=LOG_LEVEL)
    data = s.show_wins(2022, "the_show")
    if not data:
        pytest.fail("No data returned")
    songs = [x["Song"] for x in data]
    assert songs.count("DM") == 1
    assert songs.count("Candy Sugar Pop") == 1
    assert songs.count("Run2U") == 2
    assert songs.count("Guerrilla") == 2


@pytest.mark.skip(reason="Avoid unnecessary requests")
def test_wins_2023():
    s = WikiScraper(log_level=LOG_LEVEL)
    data = s.show_wins(2023, "the_show")
    if not data:
        pytest.fail("No data returned")
    songs = [x["Song"] for x in data]
    assert songs.count("Teddy Bear") == 1
    assert songs.count("Wish Lanterns") == 1
    assert songs.count("#menow") == 1
    assert songs.count("Bouncy (K-Hot Chilli Peppers)") == 2
