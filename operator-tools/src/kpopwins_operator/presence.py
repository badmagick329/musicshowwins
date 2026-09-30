"""Derive whether each winner performed on the winning broadcast.

Winners often keep winning after promotions end, so many wins have no stage
to link. r/kpop episode pages list every performer in tables headed "Artist"
above the WINNER section. Comparing Reddit's own winner line with Reddit's own
lineup avoids catalogue naming differences (for example "TXT" versus
"Tomorrow X Together"). Episodes without a usable lineup stay unknown and are
left out of the manifest rather than guessed.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from .config import Config
from .reddit import _read_cached_page, extract_winner_section
from .reddit_hydration import load_reddit_audit_report

MANIFEST_VERSION = 1
# Fewer rows than this usually means a special or partially documented episode.
MIN_LINEUP_ROWS = 5
_LINK_RE = re.compile(r"\[([^\]]*)\]\([^)]*\)")
_WINNER_ARTIST_RE = re.compile(r"^#+\s*\[?(.+?)\s+-\s+", re.M)
_WINNER_HEADING_RE = re.compile(r"(?im)^#+\s*winner\s*$")


# Broadcasts that aired a different week's episode. Music Bank's 2025-03-28
# episode was postponed to 2025-04-04, so that date's Reddit page documents the
# 03-28 win, while the 04-04 winner was only announced online (Soompi,
# 2025-04-04) and has no broadcast to have performed on.
EPISODE_WIN_OVERRIDES = {("music-bank", "2025-04-04"): ("music-bank", "2025-03-28")}


def _win_key(show: str | None, episode_date: str | None) -> tuple:
    key = (show, episode_date)
    return EPISODE_WIN_OVERRIDES.get(key, key)


@dataclass
class PresenceCounts:
    performed: int = 0
    absent: int = 0
    unknown: int = 0


def _normalize(text: str) -> str:
    return re.sub(r"[^0-9a-z가-힣]", "", text.casefold())


def _names(cell: str) -> set[str]:
    """Split "NAME (한글)" and collaboration cells into comparable names."""
    cell = _LINK_RE.sub(r"\1", cell).replace("&amp;", "&")
    names = set()
    for part in re.findall(r"[^()]+", cell):
        for name in re.split(r"\s*(?:,|&| x | X |/| feat\.? )\s*", part):
            normalized = _normalize(name)
            if len(normalized) >= 2:
                names.add(normalized)
    return names


def lineup_names(markdown: str) -> tuple[int, set[str]]:
    before_winner = _WINNER_HEADING_RE.split(markdown)[0]
    rows = 0
    names: set[str] = set()
    in_table = False
    for line in before_winner.splitlines():
        if "|" not in line:
            in_table = False
            continue
        cell = line.split("|")[0].strip()
        if cell.strip("*").casefold() == "artist":
            in_table = True
            continue
        # U+3164 is a filler Reddit editors use for blank rows.
        if not in_table or re.fullmatch(r":?-+:?", cell) or not cell.strip("ㅤ "):
            continue
        rows += 1
        names |= _names(cell)
    return rows, names


def winner_performed(markdown: str, catalogue_artist: str) -> bool | None:
    found, section = extract_winner_section(markdown)
    match = _WINNER_ARTIST_RE.search(section) if found else None
    rows, names = lineup_names(markdown)
    if match is None or rows < MIN_LINEUP_ROWS:
        return None
    winner = _names(match.group(1)) | _names(catalogue_artist)
    return bool(winner & names)


def _page_path(episode_url: str) -> str:
    return urlsplit(episode_url).path.removeprefix("/r/kpop/wiki/")


def build_presence(
    config: Config, report_path: Path, artists: dict[tuple[str, str], str]
) -> tuple[dict, PresenceCounts]:
    report = load_reddit_audit_report(report_path)
    counts = PresenceCounts()
    entries = {}
    for episode in report["episodes"]:
        key = _win_key(episode.get("show_slug"), episode.get("win_date"))
        if episode.get("has_local_win") is not True or key not in artists:
            continue
        markdown = _read_cached_page(config, _page_path(episode["episode_url"]))
        performed = (
            None if markdown is None else winner_performed(markdown, artists[key])
        )
        if performed is None:
            counts.unknown += 1
            continue
        if performed:
            counts.performed += 1
        else:
            counts.absent += 1
        entries[key] = performed
    document = {
        "version": MANIFEST_VERSION,
        "wins": [
            {"show": show, "date": win_date, "performed": performed}
            for (show, win_date), performed in sorted(entries.items())
        ],
    }
    return document, counts


def serialize_presence(document: dict) -> str:
    return json.dumps(document, ensure_ascii=False, indent=2) + "\n"
