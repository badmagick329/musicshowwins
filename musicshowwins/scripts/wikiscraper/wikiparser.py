from datetime import datetime
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup as bs
from bs4.element import ResultSet, Tag


class WikiParser:
    @staticmethod
    def parse(html: str, year: int, offset: int = 0) -> pd.DataFrame:
        """Parse html table into a list of dicts"""
        soup = bs(html, "lxml")
        tables = soup.select("table")
        tables = WikiParser._find_tables(tables)
        if isinstance(tables, ValueError):
            raise tables
        table = tables[offset]
        WikiParser._fix_span(table)
        parsed_table = pd.read_html(str(table))
        if not parsed_table:
            raise ValueError("Error parsing table")
        df = parsed_table[0]
        df = WikiParser._clean(df)
        df.loc[:, "Date"] = df["Date"].apply(
            lambda x: WikiParser._parse_date(f"{x}, {year}")
        )
        df = df[["Date", "Artist", "Song"]]
        df.loc[:, "Artist"] = df["Artist"].apply(
            lambda x: x.split("feat.")[0].strip().replace(", ", " ")
        )
        df.loc[:, "Song"] = df["Song"].apply(lambda x: x.strip())
        return df

    @staticmethod
    def parse_csv(csv_file: Path, year: int) -> pd.DataFrame:
        df = pd.read_csv(csv_file)
        df.loc[:, "Date"] = df["Date"].apply(
            lambda x: WikiParser._parse_date(f"{x}, {year}")
        )
        df = df[["Date", "Artist", "Song"]]
        df.loc[:, "Artist"] = df["Artist"].apply(lambda x: x.strip().replace(", ", " "))
        df.loc[:, "Song"] = df["Song"].apply(lambda x: x.strip())
        return df

    @staticmethod
    def _clean(df: pd.DataFrame) -> pd.DataFrame:
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
        df["Song"] = df["Song"].apply(lambda x: WikiParser._clean_song(x))
        df = WikiParser._remove_no_show(df)
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
            "rebroadcast",
            "winners were not announced",
            "special broadcast",
            "episode did not air",
            "m countdown no.1 special",
            "special edition",
            "denotes an episode did not air",
            "episode special",
            "summer k-pop festival",
            "dream concert",
            "gayo daejun",
            "lunar new year",
            "no.1 special",
            "‹See TfM›",
        ]
        remove_artists = set()
        for c in df["Artist"]:
            for ns in no_shows:
                if ns in c.lower():
                    remove_artists.add(c)
        if remove_artists:
            df = df[~df["Artist"].isin(remove_artists)]
        df = df[df["Artist"] != ""]
        return df
