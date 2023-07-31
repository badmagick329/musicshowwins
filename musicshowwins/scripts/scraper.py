import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from pprint import pprint as pp

import pandas as pd
import praw
import requests
from bs4 import BeautifulSoup as bs
from bs4.element import ResultSet, Tag

LOG_LEVEL = logging.DEBUG
DJANGO_BASE = Path(__file__).resolve().parent.parent
if str(DJANGO_BASE) not in sys.path:
    sys.path.append(str(DJANGO_BASE))
from musicshowwins.settings import REDDIT_AGENT, REDDIT_ID, REDDIT_SECRET


class WikiScraper:
    CACHE_DIR = Path(__file__).resolve().parent / "cached"
    RESP_FILE = CACHE_DIR / "responses.json"
    PAST_RESULTS = CACHE_DIR / "past_results.json"

    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:67.0) Gecko/20100101 Firefox/67.0",
        "Accept-Language": "en-US,en;q=0.9,en-GB;q=0.8",
        "Accept-Encoding": "gzip, deflate",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
        "Accept-Charset": "utf-8",
        "Referrer": "https://www.google.com/",
    }

    def __init__(self, log_level) -> None:
        log = logging.getLogger(__name__)
        handler = logging.StreamHandler()
        # handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        )
        log.addHandler(handler)
        log.setLevel(log_level)
        self.logger = log
        self.saved_responses = self._load(self.RESP_FILE)
        self.past_results = self._load(self.PAST_RESULTS)
        # self.reddit = praw.Reddit(
        #     client_id=REDDIT_ID,
        #     client_secret=REDDIT_SECRET,
        #     user_agent=REDDIT_AGENT,
        # )

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

    def read(
        self, url: str, offset: int = 0, cache: bool = True
    ) -> list[dict[str, str]]:
        """Wrapper around get and parse that caches results"""
        if f"{url}__{offset}" in self.past_results:
            self.logger.info(f"Using cached results for {url}__{offset}")
            return self.past_results[f"{url}__{offset}"]
        html = self.get(url)
        if isinstance(html, Exception):
            raise html
        results = self.parse(html, offset)
        if f"({datetime.today().year})" not in url and cache:
            self.past_results[f"{url}__{offset}"] = results
            self._save(self.past_results, self.PAST_RESULTS)
        return results

    def get(self, url) -> str | Exception:
        """Wrapper around requests.get that caches results"""
        if url in self.saved_responses:
            self.logger.info(f"Using saved data for {url}")
            return self.saved_responses[url]
        try:
            response = requests.get(url, headers=self.headers)
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

    def parse(self, html: str, offset: int = 0) -> list[dict[str, str]]:
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
        return df.to_dict("records")

    def _clean(self, df: pd.DataFrame) -> pd.DataFrame:
        if "Ref." in df.columns:
            df.drop(columns=["Ref."], inplace=True)
        if "Episode" in df.columns:
            df.drop(columns=["Episode"], inplace=True)
        if "Ep." in df.columns:
            df.drop(columns=["Ep."], inplace=True)
        df["Song"] = df["Song"].apply(lambda x: self._clean_song(x))
        df = self._remove_no_show(df)
        return df

    def _fix_span(self, table: Tag) -> None:
        # A ; used after a number in rowspan and colspan was breaking the
        # pandas parser
        rowspans = table.find_all("td", {"rowspan": True})
        colspans = table.find_all("td", {"colspan": True})
        for r in rowspans:
            r["rowspan"] = r["rowspan"].replace(";", "")
        for c in colspans:
            c["colspan"] = c["colspan"].replace(";", "")

    def _find_tables(self, tables: ResultSet[Tag]) -> list[Tag] | ValueError:
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

    def _remove_no_show(self, df: pd.DataFrame) -> pd.DataFrame:
        no_shows = [
            "no chart",
            "no broadcast",
            "no winner",
            "no show",
        ]
        remove_rows = []
        for c in df["Song"]:
            for ns in no_shows:
                if ns in c.lower():
                    remove_rows.append(c)
        if remove_rows:
            self.logger.debug(f"Removing {len(remove_rows)} rows")
            df = df[~df["Song"].isin(remove_rows)]
        return df


def main():
    scraper = WikiScraper(LOG_LEVEL)
    html = scraper.get(
        "https://en.wikipedia.org/wiki/List_of_Show!_Music_Core_Chart_winners_(2019)"
    )
    data = scraper.parse(html)

if __name__ == "__main__":
    main()
