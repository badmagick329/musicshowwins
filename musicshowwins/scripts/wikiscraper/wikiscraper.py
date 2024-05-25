import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Literal

import pandas as pd
from dotenv import load_dotenv
from scripts.wikiscraper.consts import CACHE_DIR, CSV_DIR
from scripts.wikiscraper.wikiparser import WikiParser
from scripts.wikiscraper.wikirequests import WikiRequests

LOG_LEVEL = logging.DEBUG
TESTING = False
MIN_YEAR = 2013

ShowType = Literal[
    "music_core",
    "inkigayo",
    "mcountdown",
    "the_show",
    "show_champion",
    "music_bank",
]
ShowCsvs = dict[tuple[ShowType, int], str]
ShowUrls = dict[tuple[ShowType, int], tuple[str, int]]


class WikiScraper:
    RESP_FILE = CACHE_DIR / "responses.json"
    PAST_RESULTS = CACHE_DIR / "past_results.json"

    wiki_requests: WikiRequests
    logger: logging.Logger
    past_results: dict[str, list[dict[str, str]]]
    show_urls: ShowUrls
    show_csvs: ShowCsvs

    def __init__(self, log_level=logging.INFO) -> None:
        log = logging.getLogger(__name__)
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        )
        log.addHandler(handler)
        log.setLevel(log_level)
        self.logger = log
        self.wiki_requests = WikiRequests()
        self.past_results = self._load(self.PAST_RESULTS)
        self.show_urls = dict()
        self.show_csvs = dict()
        self._generate_sources()

    def _generate_sources(self):
        shows = [
            "music_core",
            "inkigayo",
            "mcountdown",
            "the_show",
            "show_champion",
            "music_bank",
        ]
        current_year = datetime.today().year
        for s in shows:
            for y in range(MIN_YEAR + 1, current_year + 1):
                url = self._generate_url_and_offset(s, y)  # type: ignore
                if not url:
                    continue
                url, offset = url
                self.show_urls[(s, y)] = (url, offset)  # type: ignore
        self.show_csvs = {
            ("music_core", 2016): "2016_music_core.csv",
            ("show_champion", 2013): "2013_show_champion.csv",
            ("show_champion", 2013): "2013_inkigayo.csv",
        }

    def get_sources(self) -> list[str]:
        sources = list()
        for _, v in self.show_urls.items():
            sources.append(v[0])
        sources = list(set(sources))
        sources.sort()
        sources.append(
            "https://www.reddit.com/r/kpop/comments/5paj2t/yearend_2016_tally_of_music_show_wins/ - Music Core (2016)"
        )
        return sources

    def _load(self, file: Path) -> dict:
        if file.exists():
            with open(file, "r", encoding="utf-8") as f:
                return json.load(f)
        return dict()

    def _save(self, data: dict, file: Path) -> None:
        with open(file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    def _get_and_parse(
        self,
        url: str,
        year: int,
        offset: int = 0,
        cache: bool = True,
    ) -> pd.DataFrame | None:
        resp = self._get_html(url, offset)
        if resp is None or isinstance(resp, Exception):
            return None
        if isinstance(resp, pd.DataFrame):
            return resp
        assert isinstance(resp, str)
        return self._parse_and_save(resp, url, year, offset, cache)

    def _get_html(self, url: str, offset: int = 0) -> str | Exception | None:
        if f"{url}__{offset}" in self.past_results:
            # self.logger.info(f"Using cached results for {url}__{offset}")
            data = self.past_results[f"{url}__{offset}"]
            return pd.DataFrame.from_dict(data, orient="columns")  # type: ignore
        html = self.wiki_requests.get(url)
        if html is None:
            return None
        if isinstance(html, Exception):
            raise html
        return html

    def _parse_and_save(
        self,
        html: str,
        url: str,
        year: int,
        offset: int = 0,
        cache: bool = True,
    ) -> pd.DataFrame | None:
        try:
            df = WikiParser.parse(html, year, offset)
        except Exception as e:
            self.logger.error(f"Error while parsing {url}: {e}")
            return None
        if datetime.now().year != year and cache:
            self.past_results[f"{url}__{offset}"] = df.to_dict("records")
            self._save(self.past_results, self.PAST_RESULTS)
        return df

    def fetch_show_wins(
        self, year: int, show: ShowType, cache: bool = True
    ) -> list[dict[str, str]] | None:
        """Get show wins for a given year"""
        # Note: Dates for this music_core 2016 are missing so
        # all wins are entered as 2016-01-01
        if year < MIN_YEAR:
            raise ValueError(f"Year must be after {MIN_YEAR}")

        if (show, year) in self.show_csvs:
            csv = self.show_csvs[(show, year)]  # type: ignore
            df = WikiParser.parse_csv((CSV_DIR / csv), year)
            df["Show"] = show
            return df.to_dict("records")

        if (show, year) in self.show_urls:
            url, offset = self.show_urls[(show, year)]
            df = self._get_and_parse(url, year, offset, cache)
            if df is None:
                return None

            df["Show"] = show
            return df.to_dict("records")

    def fetch_all_wins(self, cache: bool = True) -> list[dict[str, str]]:
        """
        Return a list of dicts with the following keys:
        - Artist
        - Song
        - Date
        - Show
        """
        shows = [
            "music_core",
            "inkigayo",
            "mcountdown",
            "the_show",
            "show_champion",
            "music_bank",
        ]
        data = list()
        current_year = datetime.today().year
        if TESTING:
            current_year -= 1
        for s in shows:
            for y in range(2014, current_year + 1):
                wins = self.fetch_show_wins(y, s, cache)  # type: ignore
                if wins is None:
                    continue
                data.extend(wins)
        return data

    def _generate_url_and_offset(
        self, show: ShowType, year: int
    ) -> tuple[str, int] | None:
        """
        Returns the url and offset for a given show and year.

        For older years the data was entered on the same page, offset
        helps to indicate which table should be read on that page
        """
        MUSIC_CORE_BASE = (
            "https://en.wikipedia.org/wiki/List_of_Show!_Music_Core_Chart_winners_({})"
        )
        MUSIC_CORE_OLD = "https://en.wikipedia.org/wiki/Show!_Music_Core"
        MCOUNTDOWN_BASE = (
            "https://en.wikipedia.org/wiki/List_of_M_Countdown_Chart_winners_({})"
        )
        SHOW_CHAMPION_BASE = (
            "https://en.wikipedia.org/wiki/List_of_Show_Champion_Chart_winners_({})"
        )
        SHOW_CHAMPION_OLD = "https://en.wikipedia.org/wiki/Show_Champion"
        THE_SHOW_BASE = (
            "https://en.wikipedia.org/wiki/List_of_The_Show_Chart_winners_({})"
        )
        THE_SHOW_OLD = (
            "https://en.wikipedia.org/wiki/The_Show_(South_Korean_TV_program)"
        )
        INKIGAYO_BASE = (
            "https://en.wikipedia.org/wiki/List_of_Inkigayo_Chart_winners_({})"
        )
        MUSIC_BANK_BASE = (
            "https://en.wikipedia.org/wiki/List_of_Music_Bank_Chart_winners_({})"
        )
        if year < MIN_YEAR:
            raise ValueError(f"Year must be after {MIN_YEAR}")
        if show == "music_core":
            if year > 2018:
                return MUSIC_CORE_BASE.format(year), 0
            elif year == 2016:
                return None
            else:
                offset = 5
                for i in range(2018, MIN_YEAR - 1, -1):
                    if i == 2016:
                        continue
                    if year == i:
                        return MUSIC_CORE_OLD, offset
                    offset -= 1
        elif show == "mcountdown":
            return MCOUNTDOWN_BASE.format(year), 0
        elif show == "show_champion":
            if year > 2020:
                return SHOW_CHAMPION_BASE.format(year), 0
            elif year == 2013:
                return None
            else:
                offset = 6
                for i in range(2020, MIN_YEAR - 1, -1):
                    if year == i:
                        return SHOW_CHAMPION_OLD, offset
                    offset -= 1
        elif show == "the_show":
            if year > 2020:
                return THE_SHOW_BASE.format(year), 0
            elif year == 2013:
                # Data for 2013 is missing for the show
                return None
            else:
                offset = 6
                for i in range(2020, MIN_YEAR - 1, -1):
                    if year == i:
                        return THE_SHOW_OLD, offset
                    offset -= 1
        elif show == "inkigayo":
            if year > 2013:
                return INKIGAYO_BASE.format(year), 0
            elif year == 2013:
                return None
        elif show == "music_bank":
            return MUSIC_BANK_BASE.format(year), 0


def main():
    s = WikiScraper(log_level=LOG_LEVEL)
    data = s.fetch_all_wins()
    for d in data:
        print(d)


if __name__ == "__main__":
    load_dotenv()
    main()
