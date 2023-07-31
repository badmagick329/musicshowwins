import sys
from pathlib import Path

import pandas as pd
import pytest

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))
from scraper import WikiScraper, logging

LOG_LEVEL = logging.CRITICAL


def test_wins_2013():
    s = WikiScraper(log_level=LOG_LEVEL)
    url = "https://en.wikipedia.org/wiki/Show!_Music_Core"
    data = s.read(url, 1)
    songs = [x["Song"] for x in data]
    assert songs.count("Man in Love") == 1
    assert songs.count("Growl") == 3
    assert songs.count("Shadow") == 1
    assert songs.count("Stupid In Love") == 1


def test_wins_2014():
    s = WikiScraper(log_level=LOG_LEVEL)
    url = "https://en.wikipedia.org/wiki/Show!_Music_Core"
    data = s.read(url, 2)
    songs = [x["Song"] for x in data]
    assert songs.count("Friday") == 1
    assert songs.count("Something") == 2
    assert songs.count("Lonely") == 2
    assert songs.count("Mr.Mr.") == 2
    assert songs.count("Red Light") == 1
    assert songs.count("12:30") == 2


def test_wins_2015():
    s = WikiScraper(log_level=LOG_LEVEL)
    url = "https://en.wikipedia.org/wiki/Show!_Music_Core"
    data = s.read(url, 3)
    songs = [x["Song"] for x in data]
    assert songs.count("Luv") == 2
    assert songs.count("Déjà-Boo") == 2
    assert songs.count("Ice Cream Cake") == 1
    assert songs.count("Love Me Right") == 3
    assert songs.count("Lion Heart") == 2
    assert songs.count("I") == 1


def test_wins_2016():
    csv_file = Path(__file__).parent.parent / "data" / "2016_music_core.csv"
    df = pd.read_csv(csv_file)
    data = df.to_dict("records")
    songs = [x["Song"] for x in data]
    assert songs.count("Rough") == 3
    assert songs.count("Navillera") == 3
    assert songs.count("TT") == 2
    assert songs.count("You're So Fine") == 1
    assert songs.count("L.I.E") == 0
    assert songs.count("Toy") == 1


def test_wins_2017():
    s = WikiScraper(log_level=LOG_LEVEL)
    url = "https://en.wikipedia.org/wiki/Show!_Music_Core"
    data = s.read(url, 4)
    songs = [x["Song"] for x in data]
    assert songs.count("Really Really") == 1
    assert songs.count("Palette") == 2
    assert songs.count("Signal") == 2
    assert songs.count("Energetic") == 3
    assert songs.count("Beautiful") == 4
    assert songs.count("Heart Shaker") == 1


def test_wins_2018():
    s = WikiScraper(log_level=LOG_LEVEL)
    url = "https://en.wikipedia.org/wiki/Show!_Music_Core"
    data = s.read(url, 5)
    songs = [x["Song"] for x in data]
    assert songs.count("Heart Shaker") == 1
    assert songs.count("Love Scenario") == 3
    assert songs.count("Fake Love") == 3
    assert songs.count("Ddu-Du Ddu-Du") == 4
    assert songs.count("Fiancé") == 2


def test_wins_2019():
    s = WikiScraper(log_level=LOG_LEVEL)
    url = "https://en.wikipedia.org/wiki/List_of_Show!_Music_Core_Chart_winners_(2019)"
    data = s.read(url)
    songs = [x["Song"] for x in data]
    assert songs.count("Icy") == 3
    assert songs.count("Workaholic") == 2
    assert songs.count("Boy with Luv") == 9
    assert songs.count("Dalla Dalla") == 2


def test_wins_2020():
    s = WikiScraper(log_level=LOG_LEVEL)
    url = "https://en.wikipedia.org/wiki/List_of_Show!_Music_Core_Chart_winners_(2020)"
    data = s.read(url)
    songs = [x["Song"] for x in data]
    assert songs.count("Psycho") == 3
    assert songs.count("Any Song") == 4
    assert songs.count("On") == 5
    assert songs.count("2U") == 1
    assert songs.count("Let's Love") == 1
    assert songs.count("Nonstop") == 1
    assert songs.count("How You Like That") == 3


def test_wins_2021():
    s = WikiScraper(log_level=LOG_LEVEL)
    url = "https://en.wikipedia.org/wiki/List_of_Show!_Music_Core_Chart_winners_(2021)"
    data = s.read(url)
    songs = [x["Song"] for x in data]
    assert songs.count("Celebrity") == 3
    assert songs.count("Life Goes On") == 3
    assert songs.count("Butter") == 5
    assert songs.count("Queendom") == 3
    assert songs.count("Savage") == 2
    assert songs.count("Bad Love") == 1


def test_wins_2022():
    s = WikiScraper(log_level=LOG_LEVEL)
    url = "https://en.wikipedia.org/wiki/List_of_Show!_Music_Core_Chart_winners_(2022)"
    data = s.read(url)
    songs = [x["Song"] for x in data]
    assert songs.count("INVU") == 4
    assert songs.count("Nxde") == 3
    assert songs.count("Eleven") == 3
    assert songs.count("At That Moment") == 2
    assert songs.count("Antifragile") == 3
    assert songs.count("Shut Down") == 1
