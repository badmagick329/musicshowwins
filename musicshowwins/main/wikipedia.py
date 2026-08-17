"""Revision-aware Wikipedia import services.

The importer intentionally keeps the network and parsing code independent from
the management command.  That makes the parser useful with saved fixtures and
keeps a failed page from partially changing the domain tables.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, timedelta
from datetime import datetime as naive_datetime
from typing import Any, Iterable

import requests
from bs4 import BeautifulSoup
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from main.models import (
    Artist,
    ArtistAlias,
    ImportIssue,
    ImportRun,
    MusicShow,
    Song,
    SourcePage,
    Win,
    normalize_key,
    normalize_text,
)

MIN_YEAR = 2014
WIKIMEDIA_API = "https://en.wikipedia.org/w/api.php"
DEFAULT_TIMEOUT = 30
NO_BROADCAST_MARKERS = (
    "no broadcast",
    "no chart",
    "no winner",
    "no show",
    "winner not announced",
    "winners were not announced",
    "rebroadcast",
    "special broadcast",
    "special edition",
    "episode did not air",
    "episode did not occur",
    "not held",
    "cancelled",
    "canceled",
    "lunar new year",
    "dream concert",
    "gayo daejun",
    "summer k-pop festival",
)


class WikipediaError(Exception):
    """Base exception for expected source and parse failures."""


class WikipediaFetchError(WikipediaError):
    """The Action API could not provide a page or revision."""


class WikipediaParseError(WikipediaError):
    """The returned page did not contain a complete wins table."""


@dataclass(frozen=True)
class SourceSpec:
    show_slug: str
    year: int
    title: str


@dataclass(frozen=True)
class RevisionPage:
    title: str
    revision: str


@dataclass(frozen=True)
class WinCandidate:
    date: date
    artist: str
    song: str

    @property
    def key(self) -> tuple[date, str, str]:
        return (self.date, normalize_key(self.artist), normalize_key(self.song))

    def as_dict(self) -> dict[str, str]:
        return {
            "date": self.date.isoformat(),
            "artist": self.artist,
            "song": self.song,
        }


@dataclass
class ImportSummary:
    pages_processed: int = 0
    wins_added: int = 0
    conflicts_found: int = 0
    failures: list[str] | None = None

    def __post_init__(self) -> None:
        if self.failures is None:
            self.failures = []


def source_title(show_slug: str, year: int) -> str:
    """Return the Wikipedia page containing a show's requested year."""

    if show_slug == "music-core":
        if year >= 2015:
            return f"List of Show! Music Core Chart winners ({year})"
        return "Show! Music Core"
    if show_slug == "inkigayo":
        return f"List of Inkigayo Chart winners ({year})"
    if show_slug == "m-countdown":
        return f"List of M Countdown Chart winners ({year})"
    if show_slug == "the-show":
        if year > 2020:
            return f"List of The Show Chart winners ({year})"
        return "The Show (South Korean TV program)"
    if show_slug == "show-champion":
        if year > 2020:
            return f"List of Show Champion Chart winners ({year})"
        return "Show Champion"
    if show_slug == "music-bank":
        return f"List of Music Bank Chart winners ({year})"
    raise ValueError(f"Unknown music show slug: {show_slug}")


def source_specs(shows: Iterable[str], years: Iterable[int]) -> list[SourceSpec]:
    """Build deterministic show/year targets for a sync run."""

    return [
        SourceSpec(show_slug=slug, year=year, title=source_title(slug, year))
        for slug in sorted(set(shows))
        for year in sorted(set(years))
    ]


class WikipediaClient:
    """Small sequential client for the Wikimedia Action API."""

    def __init__(
        self,
        session: requests.Session | None = None,
        *,
        api_url: str = WIKIMEDIA_API,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        self.session = session or requests.Session()
        self.api_url = api_url
        self.timeout = timeout
        self.headers = {
            "User-Agent": getattr(
                settings,
                "WIKI_AGENT",
                "musicshowwins/1.0 (community resource; contact administrator)",
            )
        }

    def _request(self, params: dict[str, Any]) -> dict[str, Any]:
        params = {
            "format": "json",
            "formatversion": "2",
            "redirects": "1",
            "maxlag": "5",
            **params,
        }
        try:
            response = self.session.get(
                self.api_url,
                params=params,
                headers=self.headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as exc:
            raise WikipediaFetchError(str(exc)) from exc
        if not isinstance(payload, dict):
            raise WikipediaFetchError("Wikimedia returned a non-object response")
        if payload.get("error"):
            error = payload["error"]
            raise WikipediaFetchError(
                str(error.get("info", error)) if isinstance(error, dict) else str(error)
            )
        return payload

    def latest_revision(self, title: str) -> RevisionPage:
        payload = self._request(
            {
                "action": "query",
                "prop": "revisions",
                "titles": title,
                "rvprop": "ids",
                "rvlimit": "1",
            }
        )
        pages = payload.get("query", {}).get("pages", [])
        if not pages:
            raise WikipediaFetchError(f"Wikipedia page not found: {title}")
        page = pages[0]
        if page.get("missing") or not page.get("revisions"):
            raise WikipediaFetchError(f"Wikipedia page not found: {title}")
        revision = page["revisions"][0].get("revid")
        if revision is None:
            raise WikipediaFetchError(f"No revision found for Wikipedia page: {title}")
        return RevisionPage(title=page.get("title", title), revision=str(revision))

    def html_for_revision(self, page: RevisionPage) -> str:
        payload = self._request(
            {
                "action": "parse",
                "oldid": page.revision,
                "prop": "text|revid",
            }
        )
        parsed = payload.get("parse")
        if not isinstance(parsed, dict):
            raise WikipediaFetchError(f"No parsed HTML returned for {page.title}")
        text = parsed.get("text", "")
        if isinstance(text, dict):
            text = text.get("*", "")
        if not isinstance(text, str) or not text.strip():
            raise WikipediaFetchError(f"Empty parsed HTML returned for {page.title}")
        return text


def _clean_cell(value: str) -> str:
    value = re.sub(r"\[[^\]]*\]", "", value)
    value = value.replace("†", "").replace("‡", "")
    return normalize_text(value)


def _label(value: str) -> str:
    compact = re.sub(r"[^a-z]", "", _clean_cell(value).casefold())
    if compact.startswith("date"):
        return "date"
    if compact.startswith("artist"):
        return "artist"
    if compact.startswith("song"):
        return "song"
    return ""


def _span_value(cell: Any) -> tuple[str, int, int]:
    text = _clean_cell(cell.get_text(" ", strip=True))

    def span(name: str) -> int:
        raw = str(cell.get(name, "1")).replace(";", "")
        match = re.search(r"\d+", raw)
        return max(1, int(match.group(0))) if match else 1

    return text, span("rowspan"), span("colspan")


def _expanded_rows(table: Any) -> list[list[str]]:
    """Expand HTML row/column spans into rectangular text rows."""

    rows: list[list[str]] = []
    active: dict[int, tuple[str, int]] = {}
    for tr in table.find_all("tr"):
        current: dict[int, str] = {
            column: value for column, (value, _) in active.items()
        }
        next_active: dict[int, tuple[str, int]] = {
            column: (value, remaining - 1)
            for column, (value, remaining) in active.items()
            if remaining > 1
        }
        column = 0
        for cell in tr.find_all(["th", "td"], recursive=False):
            while column in current:
                column += 1
            value, rowspan, colspan = _span_value(cell)
            for offset in range(colspan):
                current[column + offset] = value
                if rowspan > 1:
                    next_active[column + offset] = (value, rowspan - 1)
            column += colspan
        if current:
            max_column = max(current)
            rows.append([current.get(index, "") for index in range(max_column + 1)])
        active = next_active
    return rows


def _parse_date(value: str, year: int) -> date | None:
    value = _clean_cell(value).replace("–", "-").replace("—", "-")
    for fmt in ("%B %d, %Y", "%b %d, %Y", "%Y-%m-%d", "%Y.%m.%d"):
        try:
            return naive_datetime.strptime(value, fmt).date()
        except ValueError:
            pass
    for fmt in ("%B %d", "%b %d"):
        try:
            return naive_datetime.strptime(f"{value}, {year}", f"{fmt}, %Y").date()
        except ValueError:
            pass
    return None


def _is_no_broadcast(values: Iterable[str]) -> bool:
    text = " ".join(_clean_cell(value).casefold() for value in values)
    return any(marker in text for marker in NO_BROADCAST_MARKERS)


def _header_positions(rows: list[list[str]]) -> tuple[int, dict[str, int]] | None:
    for header_index, row in enumerate(rows):
        positions: dict[str, int] = {}
        for index, value in enumerate(row):
            field = _label(value)
            if field and field not in positions:
                positions[field] = index
        if set(positions) == {"date", "artist", "song"}:
            return header_index, positions
    return None


def _years_in_text(value: str) -> set[int]:
    return {int(match) for match in re.findall(r"(?<!\d)(?:19|20)\d{2}(?!\d)", value)}


def _table_scope_years(table: Any, requested_year: int | None = None) -> set[int]:
    """Find the nearest year-bearing section heading, caption, or table id."""

    heading_years: set[int] | None = None
    for heading in table.find_all_previous(["h2", "h3", "h4"]):
        years = _years_in_text(heading.get_text(" ", strip=True))
        if years:
            heading_years = years
            break

    caption = table.find("caption")
    caption_years: set[int] = set()
    if caption is not None:
        caption_years = _years_in_text(caption.get_text(" ", strip=True))
    id_years = _years_in_text(str(table.get("id", "")))

    if requested_year is not None:
        for years in (heading_years, caption_years, id_years):
            if years and requested_year in years:
                return years
    if heading_years:
        return heading_years
    if caption_years:
        return caption_years
    return id_years


SONG_QUOTE_PAIRS = {
    '"': '"',
    "'": "'",
    "“": "”",
    "‘": "’",
}


def _strip_song_quotes(value: str) -> str:
    value = normalize_text(value)
    if len(value) >= 2 and SONG_QUOTE_PAIRS.get(value[0]) == value[-1]:
        return normalize_text(value[1:-1])
    return value


def _candidate_rows(table: Any, year: int) -> list[WinCandidate]:
    rows = _expanded_rows(table)
    header = _header_positions(rows)
    if header is None:
        raise WikipediaParseError("No complete Date/Artist/Song table found")
    header_index, positions = header

    candidates: list[WinCandidate] = []
    for values in rows[header_index + 1 :]:
        if sum(bool(_clean_cell(value)) for value in values) == 0:
            continue
        if sum(_label(value) in {"date", "artist", "song"} for value in values) >= 2:
            continue
        if _is_no_broadcast(values):
            continue
        largest = max(positions.values())
        if len(values) <= largest:
            raise WikipediaParseError("Malformed wins row has too few columns")
        raw_date = values[positions["date"]]
        raw_artist = values[positions["artist"]]
        raw_song = values[positions["song"]]
        if not any(
            (_clean_cell(raw_date), _clean_cell(raw_artist), _clean_cell(raw_song))
        ):
            continue
        parsed_date = _parse_date(raw_date, year)
        artist = _clean_cell(raw_artist)
        song = _strip_song_quotes(_clean_cell(raw_song))
        if parsed_date is None:
            raise WikipediaParseError(f"Invalid date in wins row: {raw_date!r}")
        if parsed_date.year != year:
            raise WikipediaParseError(
                f"Source page contains a date outside {year}: {parsed_date.isoformat()}"
            )
        if not artist or not song:
            raise WikipediaParseError("Wins row has an empty artist or song")
        candidates.append(WinCandidate(parsed_date, artist, song))

    if not candidates:
        raise WikipediaParseError("Wins table contains no valid wins")
    return candidates


def parse_wikipedia_html(html: str, year: int) -> list[WinCandidate]:
    """Parse and validate the complete Date/Artist/Song source page."""

    if year < MIN_YEAR:
        raise WikipediaParseError(f"Years before {MIN_YEAR} are not supported")
    soup = BeautifulSoup(html, "lxml")
    tables = soup.find_all("table")
    if not tables:
        raise WikipediaParseError("Wikipedia page contains no tables")
    identified = [
        (table, _table_scope_years(table, year))
        for table in tables
        if _header_positions(_expanded_rows(table)) is not None
    ]
    if not identified:
        raise WikipediaParseError("No complete Date/Artist/Song table found")

    scoped = [(table, scopes) for table, scopes in identified if scopes]
    if scoped:
        selected = [(table, scopes) for table, scopes in scoped if year in scopes]
        if not selected:
            raise WikipediaParseError(f"No wins table scoped to {year}")
    else:
        selected = identified

    candidates: list[WinCandidate] = []
    for table, _ in selected:
        candidates.extend(_candidate_rows(table, year))
    keys = [candidate.key for candidate in candidates]
    if len(keys) != len(set(keys)):
        raise WikipediaParseError("Source page contains duplicate wins")
    return candidates


def _year_bounds(year: int) -> tuple[date, date]:
    return date(year, 1, 1), date(year + 1, 1, 1) - timedelta(days=1)


class WikipediaImporter:
    """Apply validated Wikipedia pages to the domain models."""

    def __init__(self, client: WikipediaClient | None = None) -> None:
        self.client = client or WikipediaClient()

    @staticmethod
    def _artist_reference(name: str) -> tuple[Artist | None, str]:
        key = normalize_key(name)
        alias = (
            ArtistAlias.objects.select_related("artist")
            .filter(normalized_name=key)
            .first()
        )
        if alias:
            return alias.artist, alias.artist.identity_key
        artist = Artist.objects.filter(identity_key=key).first()
        return artist, key

    @staticmethod
    def _existing_wins(show: MusicShow, year: int) -> list[Win]:
        start, end = _year_bounds(year)
        return list(
            Win.objects.filter(show=show, date__range=(start, end)).select_related(
                "song__artist"
            )
        )

    @staticmethod
    def _issue(
        run: ImportRun | None,
        issue_type: str,
        *,
        source_page: SourcePage | None = None,
        candidate: dict[str, Any] | None = None,
        notes: str = "",
    ) -> None:
        candidate = candidate or {}
        if run is not None:
            for issue in ImportIssue.objects.filter(
                source_page=source_page,
                issue_type=issue_type,
                resolution=ImportIssue.Resolution.OPEN,
            ):
                if issue.candidate == candidate:
                    return
            ImportIssue.objects.create(
                import_run=run,
                source_page=source_page,
                issue_type=issue_type,
                candidate=candidate,
                notes=notes,
            )

    def _apply_page(
        self,
        show: MusicShow,
        spec: SourceSpec,
        page: RevisionPage,
        candidates: list[WinCandidate],
        run: ImportRun,
    ) -> tuple[int, int]:
        added = 0
        conflicts_found = 0
        with transaction.atomic():
            source, _ = SourcePage.objects.select_for_update().get_or_create(
                show=show,
                year=spec.year,
                defaults={"page_title": page.title},
            )
            source.page_title = page.title
            source.latest_revision = page.revision
            source.last_synced_at = timezone.now()
            source.save(
                update_fields=("page_title", "latest_revision", "last_synced_at")
            )

            existing = self._existing_wins(show, spec.year)
            expected: set[tuple[date, str, str]] = set()
            for candidate in candidates:
                artist, identity = self._artist_reference(candidate.artist)
                title_key = normalize_key(candidate.song)
                expected.add((candidate.date, identity, title_key))
                song = (
                    Song.objects.filter(
                        artist=artist, normalized_title=title_key
                    ).first()
                    if artist
                    else None
                )
                exact = (
                    Win.objects.filter(
                        show=show, date=candidate.date, song=song
                    ).first()
                    if song
                    else None
                )
                conflicts = Win.objects.filter(show=show, date=candidate.date)
                if song:
                    conflicts = conflicts.exclude(song=song)
                if conflicts.exists():
                    self._issue(
                        run,
                        ImportIssue.IssueType.CONFLICT,
                        source_page=source,
                        candidate={"show": spec.show_slug, **candidate.as_dict()},
                        notes=(
                            "Wikipedia winner differs from an existing winner "
                            "on this date."
                        ),
                    )
                    conflicts_found += 1
                    continue
                if exact:
                    if (
                        exact.source_page_id != source.pk
                        or exact.source_revision != page.revision
                    ):
                        exact.source_type = Win.SourceType.WIKIPEDIA
                        exact.source_page = source
                        exact.source_revision = page.revision
                        exact.save(
                            update_fields=(
                                "source_type",
                                "source_page",
                                "source_revision",
                            )
                        )
                    continue
                if artist is None:
                    artist = Artist.objects.create(name=candidate.artist)
                if song is None:
                    song = Song.objects.create(artist=artist, title=candidate.song)
                Win.objects.create(
                    show=show,
                    song=song,
                    date=candidate.date,
                    source_type=Win.SourceType.WIKIPEDIA,
                    source_page=source,
                    source_revision=page.revision,
                )
                added += 1

            for win in existing:
                key = (
                    win.date,
                    win.song.artist.identity_key,
                    win.song.normalized_title,
                )
                if key not in expected:
                    self._issue(
                        run,
                        ImportIssue.IssueType.MISSING_WIN,
                        source_page=source,
                        candidate={
                            "show": spec.show_slug,
                            "date": win.date.isoformat(),
                            "artist": win.song.artist.name,
                            "song": win.song.title,
                        },
                        notes=(
                            "Existing historical win was not present in the source "
                            "page; it was retained."
                        ),
                    )
        return added, conflicts_found

    def _dry_run_page(
        self,
        show: MusicShow,
        spec: SourceSpec,
        candidates: list[WinCandidate],
    ) -> tuple[int, int]:
        existing = self._existing_wins(show, spec.year)
        existing_map = {
            (win.date, win.song.artist.identity_key, win.song.normalized_title): win
            for win in existing
        }
        candidate_keys: set[tuple[date, str, str]] = set()
        added = 0
        conflicts = 0
        for candidate in candidates:
            _, identity = self._artist_reference(candidate.artist)
            key = (candidate.date, identity, normalize_key(candidate.song))
            candidate_keys.add(key)
            if key in existing_map:
                continue
            if any(win.date == candidate.date for win in existing):
                conflicts += 1
            else:
                added += 1
        return added, conflicts

    def sync(
        self,
        *,
        shows: Iterable[str],
        years: Iterable[int],
        dry_run: bool = False,
    ) -> ImportSummary:
        shows = list(shows)
        years = list(years)
        if any(year < MIN_YEAR for year in years):
            raise ValueError(f"Years before {MIN_YEAR} are not supported")
        specs = source_specs(shows, years)
        show_map = {
            show.slug: show
            for show in MusicShow.objects.filter(
                slug__in={spec.show_slug for spec in specs}
            )
        }
        missing = sorted({spec.show_slug for spec in specs} - set(show_map))
        if missing:
            raise ValueError(f"Unknown music show slug(s): {', '.join(missing)}")

        run = None
        if not dry_run:
            run = ImportRun.objects.create(
                requested_shows=sorted(set(shows)), requested_years=sorted(set(years))
            )
        summary = ImportSummary()
        try:
            for spec in specs:
                show = show_map[spec.show_slug]
                source = SourcePage.objects.filter(show=show, year=spec.year).first()
                try:
                    revision_page = self.client.latest_revision(spec.title)
                    if source and source.latest_revision == revision_page.revision:
                        summary.pages_processed += 1
                        continue
                    html = self.client.html_for_revision(revision_page)
                    candidates = parse_wikipedia_html(html, spec.year)
                    if dry_run:
                        added, conflicts = self._dry_run_page(show, spec, candidates)
                        summary.wins_added += added
                        summary.conflicts_found += conflicts
                    else:
                        assert run is not None
                        added, conflicts = self._apply_page(
                            show, spec, revision_page, candidates, run
                        )
                        summary.wins_added += added
                        summary.conflicts_found += conflicts
                    summary.pages_processed += 1
                except (WikipediaError, ValueError) as exc:
                    detail = f"{spec.show_slug}/{spec.year}: {exc}"
                    summary.failures.append(detail)
                    if run is not None:
                        self._issue(
                            run,
                            ImportIssue.IssueType.INVALID_SOURCE
                            if isinstance(exc, WikipediaParseError)
                            else ImportIssue.IssueType.FETCH_ERROR,
                            candidate={
                                "show": spec.show_slug,
                                "year": spec.year,
                                "page_title": spec.title,
                            },
                            notes=str(exc),
                        )
            if run is not None:
                run.pages_processed = summary.pages_processed
                run.wins_added = summary.wins_added
                run.conflicts_found = summary.conflicts_found
                run.status = (
                    ImportRun.Status.FAILED
                    if summary.failures
                    else ImportRun.Status.COMPLETED
                )
                run.failure_summary = "\n".join(summary.failures)
                run.finished_at = timezone.now()
                run.save(
                    update_fields=(
                        "pages_processed",
                        "wins_added",
                        "conflicts_found",
                        "status",
                        "failure_summary",
                        "finished_at",
                    )
                )
            return summary
        except Exception:
            if run is not None:
                run.status = ImportRun.Status.FAILED
                run.finished_at = timezone.now()
                run.failure_summary = "Unexpected importer failure"
                run.save(update_fields=("status", "finished_at", "failure_summary"))
            raise
