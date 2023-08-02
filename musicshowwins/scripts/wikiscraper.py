import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Literal

import pandas as pd
import requests
from bs4 import BeautifulSoup as bs
from bs4.element import ResultSet, Tag
from dotenv import load_dotenv

load_dotenv()

LOG_LEVEL = logging.DEBUG
WIKI_AGENT = os.environ.get("WIKI_AGENT", "")

show_type = Literal[
    "music_core",
    "inkigayo",
    "mcountdown",
    "the_show",
    "show_champion",
    "music_bank",
]


class WikiScraper:
    CACHE_DIR = Path(__file__).resolve().parent / "cached"
    RESP_FILE = CACHE_DIR / "responses.json"
    PAST_RESULTS = CACHE_DIR / "past_results.json"

    headers = {
        "User-Agent": WIKI_AGENT,
    }

    def __init__(self, log_level) -> None:
        log = logging.getLogger(__name__)
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        )
        log.addHandler(handler)
        log.setLevel(log_level)
        self.logger = log
        self.saved_responses = self._load(self.RESP_FILE)
        self.past_results = self._load(self.PAST_RESULTS)
        self.last_fetch = None
        self.delay = 0.2

    def _load(self, file: str) -> dict:
        self.CACHE_DIR.mkdir(exist_ok=True)
        if file.exists():
            with open(file, "r", encoding="utf-8") as f:
                return json.load(f)
        else:
            return dict()

    def _save(self, data: dict, file: str) -> None:
        with open(file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    def get_and_parse(
        self, url: str, year: int, offset: int = 0, cache: bool = True
    ) -> list[dict[str, str]]:
        """Wrapper around get and parse that caches results"""
        if f"{url}__{offset}" in self.past_results:
            self.logger.info(f"Using cached results for {url}__{offset}")
            return self.past_results[f"{url}__{offset}"]
        html = self._get(url)
        if isinstance(html, Exception):
            raise html
        results = self._parse(html, year, offset)
        if datetime.now().year != year and cache:
            self.past_results[f"{url}__{offset}"] = results
            self._save(self.past_results, self.PAST_RESULTS)
        return results

    def _get(self, url) -> str | Exception:
        """
        Wrapper around requests.get that caches results and delays
        requests if necessary
        """
        if url in self.saved_responses:
            self.logger.info(f"Using saved data for {url}")
            return self.saved_responses[url]
        try:
            if self.last_fetch:
                time_since = datetime.now() - self.last_fetch
                if time_since.total_seconds() < self.delay:
                    time.sleep(self.delay - time_since.total_seconds())
            response = requests.get(url, headers=self.headers)
            self.last_fetch = datetime.now()
            if response.status_code == 200:
                self.logger.info(f"Fetched {url}")
                if f"({datetime.today().year})" not in url:
                    self.saved_responses[url] = response.text
                    self._save(self.saved_responses, self.RESP_FILE)
                return response.text
            else:
                return ValueError(f"Error {response.status_code} while fetching {url}")
        except Exception as e:
            self.logger.error(f"Error while fetching {url}: {e}")
            return e

    def _parse(self, html: str, year: int, offset: int = 0) -> list[dict[str, str]]:
        """Parse html table into a list of dicts"""
        soup = bs(html, "lxml")
        tables = soup.select("table")
        tables = self._find_tables(tables)
        if isinstance(tables, ValueError):
            raise tables
        table = tables[offset]
        self._fix_span(table)
        parsed_table = pd.read_html(str(table))
        if not parsed_table:
            raise ValueError("Error parsing table")
        df = parsed_table[0]
        df = self._clean(df)
        df.loc[:, "Date"] = df["Date"].apply(lambda x: self._parse_date(f"{x}, {year}"))
        return df.to_dict("records")

    def show_wins(
        self, year: int, show: show_type, cache: bool = True
    ) -> list[dict[str, str]] | None:
        """Get show wins for a given year"""
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
        MIN_YEAR = 2013
        if year < MIN_YEAR:
            raise ValueError(f"Year must be after {MIN_YEAR}")
        if show == "music_core":
            if year > 2018:
                return self.get_and_parse(MUSIC_CORE_BASE.format(year), year, 0, cache)
            elif year == 2016:
                csv_file = Path(__file__).parent / "data" / "2016_music_core.csv"
                df = pd.read_csv(csv_file)
                df["Show"] = df["Show"] = "music_core"
                return df.to_dict("records")
            else:
                offset = 5
                for i in range(2018, MIN_YEAR - 1, -1):
                    if i == 2016:
                        continue
                    if year == i:
                        return self.get_and_parse(MUSIC_CORE_OLD, year, offset, cache)
                    offset -= 1
        elif show == "mcountdown":
            return self.get_and_parse(MCOUNTDOWN_BASE.format(year), year, 0, cache)
        elif show == "show_champion":
            if year > 2020:
                return self.get_and_parse(
                    SHOW_CHAMPION_BASE.format(year), year, 0, cache
                )
            elif year == 2013:
                csv_file = Path(__file__).parent / "data" / "2013_show_champion.csv"
                df = pd.read_csv(csv_file)
                return df.to_dict("records")
            else:
                offset = 6
                for i in range(2020, MIN_YEAR - 1, -1):
                    if year == i:
                        return self.get_and_parse(
                            SHOW_CHAMPION_OLD, year, offset, cache
                        )
                    offset -= 1
        elif show == "the_show":
            if year > 2020:
                return self.get_and_parse(THE_SHOW_BASE.format(year), year, 0, cache)
            elif year == 2013:
                return dict()
            else:
                offset = 6
                for i in range(2020, MIN_YEAR - 1, -1):
                    if year == i:
                        return self.get_and_parse(THE_SHOW_OLD, year, offset, cache)
                    offset -= 1
        elif show == "inkigayo":
            if year > 2013:
                return self.get_and_parse(INKIGAYO_BASE.format(year), year, 0, cache)
            elif year == 2013:
                csv_file = Path(__file__).parent / "data" / "2013_inkigayo.csv"
                df = pd.read_csv(csv_file)
                return df.to_dict("records")
        elif show == "music_bank":
            return self.get_and_parse(MUSIC_BANK_BASE.format(year), year, 0, cache)

    def all_wins(self, cache: bool = True) -> dict[str, list[dict[str, str]]]:
        shows = [
            "music_core",
            "inkigayo",
            "mcountdown",
            "the_show",
            "show_champion",
            "music_bank",
        ]
        data = dict()
        for s in shows:
            print(s)
            data.setdefault(s, list())
            for y in range(2014, 2023):
                print(y)
                d = self.show_wins(y, s, cache)
                if d:
                    data[s].extend(d)
        return data

    def _clean(self, df: pd.DataFrame) -> pd.DataFrame:
        if "Ref." in df.columns:
            df.drop(columns=["Ref."], inplace=True)
        if "Episode" in df.columns:
            df.drop(columns=["Episode"], inplace=True)
        if "Ep." in df.columns:
            df.drop(columns=["Ep."], inplace=True)
        # df.dropna(axis=0, how="any", inplace=True)
        df["Artist"].fillna("", inplace=True)
        df["Song"].fillna("", inplace=True)
        df["Date"].fillna("", inplace=True)
        df["Song"] = df["Song"].apply(lambda x: self._clean_song(x))
        df = self._remove_no_show(df)
        return df

    @staticmethod
    def _fix_span(table: Tag) -> None:
        # A ; used after a number in rowspan and colspan was breaking the
        # pandas parser
        rowspans = table.find_all("td", {"rowspan": True})
        colspans = table.find_all("td", {"colspan": True})
        for r in rowspans:
            r["rowspan"] = r["rowspan"].replace(";", "")
        for c in colspans:
            c["colspan"] = c["colspan"].replace(";", "")

    @staticmethod
    def _parse_date(date: str) -> str:
        try:
            return datetime.strptime(date, "%B %d, %Y").strftime("%Y-%m-%d")
        except ValueError:
            return ""

    @staticmethod
    def _find_tables(tables: ResultSet[Tag]) -> list[Tag] | ValueError:
        found_tables = list()
        for t in tables:
            rows = t.find_all("tr")
            if not rows:
                continue
            headers = rows[0].find_all("th")
            if not headers or len(headers) < 3:
                continue
            # Sometimes Date,Artist,Song are 0,1,2
            if headers[0].text.strip() == "Date":
                a = 1
                s = 2
            elif headers[1].text.strip() == "Date":
                a = 2
                s = 3
            else:
                continue
            found_artist = headers[a].text.strip() == "Artist"
            found_song = headers[s].text.strip() == "Song"
            if found_artist and found_song:
                found_tables.append(t)
        if not found_tables:
            return ValueError("No table found")
        for ft in found_tables:
            rows = list(ft.find_all("tr"))
            if not rows:
                return ValueError(f"No rows found in {ft}")
        return found_tables

    @staticmethod
    def _clean_song(song: str) -> str:
        chars = ['"', "†", "‡"]
        for c in chars:
            song = song.replace(c, "")
        return song.strip()

    @staticmethod
    def _remove_no_show(df: pd.DataFrame) -> pd.DataFrame:
        no_shows = [
            "no chart",
            "no broadcast",
            "no winner",
            "no show",
            "winner not announced",
        ]
        remove_rows = set()
        for c in df["Artist"]:
            for ns in no_shows:
                if ns in c.lower():
                    remove_rows.add(c)
        if remove_rows:
            df = df[~df["Song"].isin(remove_rows)]
        return df


def main():
    pass


if __name__ == "__main__":
    main()
