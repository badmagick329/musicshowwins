from __future__ import annotations

import json
import re
import sqlite3
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any, Callable, TextIO
from urllib.parse import parse_qs, unquote, urlsplit

import requests

from .config import Config
from .manifest import write_atomic

USER_AGENT = "KpopWinsOperator/0.1 (+https://github.com/badmagick329/musicshowwins)"
REDDIT_INDEX_PAGE = "music-shows"
REDDIT_ARCHIVE_PREFIX = "music-shows/"
REDDIT_ENTRY_POINT = "https://www.reddit.com/r/kpop/wiki/music-shows/"
REDDIT_SHOW_ARCHIVES = {
    "inkigayo": "music-shows/inkigayo",
    "m-countdown": "music-shows/m-countdown",
    "music-bank": "music-shows/music-bank",
    "music-core": "music-shows/show-music-core",
    "show-champion": "music-shows/show-champion",
    "the-show": "music-shows/the-show",
}
WIKI_LINK_HOSTS = {
    "reddit.com",
    "www.reddit.com",
    "old.reddit.com",
    "np.reddit.com",
    "oauth.reddit.com",
}
YOUTUBE_HOSTS = {"youtube.com", "m.youtube.com", "music.youtube.com"}
VIDEO_ID_RE = re.compile(r"[A-Za-z0-9_-]{5,}")
HEADING_RE = re.compile(r"^#{1,6}\s*(.+?)\s*$")
MAX_INDEX_PAGES_PER_SHOW = 200
TOKEN_EXPIRY_SKEW_SECONDS = 300
MAX_ATTEMPTS = 4


class RedditError(RuntimeError):
    pass


class RedditCredentialsMissing(RedditError):
    pass


@dataclass(frozen=True)
class ParsedLink:
    provider: str
    external_id: str
    canonical_url: str


@dataclass(frozen=True)
class EpisodeRef:
    show_slug: str
    page_path: str
    win_date: str

    @property
    def sort_key(self) -> tuple[str, str]:
        return self.show_slug, self.win_date


@dataclass
class ExtractedLink:
    link_url: str
    provider: str
    external_id: str
    canonical_url: str
    classification: str
    video_title: str = ""
    publisher_name: str = ""
    publisher_external_id: str = ""
    existing_review_status: str = ""
    existing_candidate_id: int | None = None
    local_video_status: str = ""


@dataclass
class EpisodeOutcome:
    ref: EpisodeRef
    source: str
    outcome: str
    has_local_win: bool
    winner_text: str = ""
    local_artist: str = ""
    local_song: str = ""
    error: str = ""
    links: list[ExtractedLink] = field(default_factory=list)


@dataclass
class AuditOutcome:
    report_path: Path
    tsv_path: Path
    more_remaining: bool
    collection_complete: bool
    totals: dict[str, int]


def _fixed_clock(instant: datetime) -> Callable[[], datetime]:
    def clock() -> datetime:
        return instant

    return clock


class RedditClient:
    def __init__(
        self,
        config: Config,
        *,
        session: requests.Session | None = None,
        clock: Callable[[], datetime] | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        missing = [
            name
            for name, value in (
                ("REDDIT_CLIENT_ID", config.reddit_client_id),
                ("REDDIT_CLIENT_SECRET", config.reddit_client_secret),
                ("REDDIT_USER_AGENT", config.reddit_user_agent),
            )
            if not value
        ]
        if missing:
            raise RedditCredentialsMissing(
                "Reddit credentials are missing: " + ", ".join(missing) + "."
            )
        self._client_id = config.reddit_client_id
        self._client_secret = config.reddit_client_secret
        self._user_agent = config.reddit_user_agent
        self._token_url = config.reddit_token_url
        self._api_base = config.reddit_api_base_url
        self._session = session or requests.Session()
        self._clock = clock or (lambda: datetime.now(UTC))
        self._sleep = sleep
        self._token: str | None = None
        self._token_expires_at: datetime | None = None

    def _utc_now(self) -> datetime:
        instant = self._clock()
        if instant.tzinfo is None:
            instant = instant.replace(tzinfo=UTC)
        return instant

    def _retry_delay(self, response: requests.Response, attempt: int) -> float:
        value = response.headers.get("Retry-After")
        if value:
            try:
                return min(max(float(value), 0), 30)
            except ValueError:
                pass
        return min(2**attempt, 8)

    def _ensure_token(self) -> None:
        instant = self._utc_now()
        if self._token and self._token_expires_at and instant < self._token_expires_at:
            return
        for attempt in range(MAX_ATTEMPTS):
            try:
                response = self._session.post(
                    self._token_url,
                    data={"grant_type": "client_credentials"},
                    auth=(self._client_id, self._client_secret),
                    headers={"User-Agent": self._user_agent},
                    timeout=(5, 30),
                )
            except requests.RequestException as exc:
                if attempt == MAX_ATTEMPTS - 1:
                    raise RedditError("Reddit token request failed.") from exc
                self._sleep(min(2**attempt, 8))
                continue
            if response.status_code == 429 or 500 <= response.status_code <= 599:
                if attempt < MAX_ATTEMPTS - 1:
                    self._sleep(self._retry_delay(response, attempt))
                    continue
                raise RedditError(
                    f"Reddit token request failed with HTTP {response.status_code}."
                )
            if response.status_code >= 400:
                raise RedditError(
                    f"Reddit token request failed with HTTP {response.status_code}."
                )
            try:
                payload = response.json()
            except ValueError as exc:
                raise RedditError("Reddit token response was not valid JSON.") from exc
            token = payload.get("access_token") if isinstance(payload, dict) else None
            expires_in = (
                payload.get("expires_in") if isinstance(payload, dict) else None
            )
            if not isinstance(token, str) or not token:
                raise RedditError("Reddit token response is incomplete.")
            try:
                seconds = int(expires_in)
            except (TypeError, ValueError):
                seconds = 3600
            self._token = token
            self._token_expires_at = instant + timedelta(
                seconds=max(seconds - TOKEN_EXPIRY_SKEW_SECONDS, 60)
            )
            return
        raise RedditError("Reddit token request failed.")

    def get_json(self, path: str) -> dict[str, Any]:
        self._ensure_token()
        url = f"{self._api_base}{path}"
        for attempt in range(MAX_ATTEMPTS):
            try:
                response = self._session.get(
                    url,
                    headers={
                        "Authorization": f"Bearer {self._token}",
                        "User-Agent": self._user_agent,
                        "Accept": "application/json",
                    },
                    timeout=(5, 30),
                )
            except requests.RequestException as exc:
                if attempt == MAX_ATTEMPTS - 1:
                    raise RedditError("Reddit API request failed.") from exc
                self._sleep(min(2**attempt, 8))
                continue
            if response.status_code == 429 or 500 <= response.status_code <= 599:
                if attempt < MAX_ATTEMPTS - 1:
                    self._sleep(self._retry_delay(response, attempt))
                    continue
            if response.status_code >= 400:
                raise RedditError(
                    f"Reddit API request failed with HTTP {response.status_code}."
                )
            try:
                payload = response.json()
            except ValueError as exc:
                raise RedditError("Reddit API returned invalid JSON.") from exc
            if not isinstance(payload, dict):
                raise RedditError("Reddit API returned an invalid response.")
            return payload
        raise RedditError("Reddit API request failed.")

    def wiki_page(self, page: str) -> str:
        payload = self.get_json(f"/r/kpop/wiki/{page}")
        data = payload.get("data")
        content = data.get("content_md") if isinstance(data, dict) else None
        if not isinstance(content, str):
            raise RedditError(f"Reddit wiki page {page} returned no content.")
        return content


def normalize_wiki_target(target: str) -> str | None:
    cleaned = target.strip().strip("<>")
    if not cleaned:
        return None
    parsed = urlsplit(cleaned)
    if parsed.scheme:
        if parsed.scheme not in {"http", "https"}:
            return None
        host = (parsed.hostname or "").lower()
        if host not in WIKI_LINK_HOSTS:
            return None
        path = parsed.path
    elif cleaned.startswith("/"):
        path = parsed.path
    else:
        return None
    prefix = "/r/kpop/wiki/"
    if not path.startswith(prefix):
        return None
    page = unquote(path[len(prefix) :])
    page = re.sub(r"/+", "/", page).strip("/")
    return page or None


SECTION_TARGET_RE = re.compile(
    r"\[[^\]]*\]\((?P<markdown>[^)\s]+)"
    r"|<(?P<autolink>https?://[^>\s]+)>"
    r"|(?P<bare>https?://[^\s<>()\[\]]+)"
)


def _candidate_targets(markdown: str) -> list[str]:
    targets: list[str] = []
    for match in SECTION_TARGET_RE.finditer(markdown):
        target = (
            match.group("markdown") or match.group("autolink") or match.group("bare")
        )
        if target:
            targets.append(target)
    return targets


def extract_wiki_links(markdown: str) -> list[str]:
    pages: list[str] = []
    seen: set[str] = set()
    for target in _candidate_targets(markdown):
        page = normalize_wiki_target(target)
        if page is None:
            continue
        key = page.casefold()
        if key in seen:
            continue
        seen.add(key)
        pages.append(page)
    return pages


def episode_date(page_path: str) -> str | None:
    final = page_path.rstrip("/").rsplit("/", 1)[-1]
    if not re.fullmatch(r"\d{8}", final):
        return None
    try:
        parsed = date_from_components(int(final[:4]), int(final[4:6]), int(final[6:]))
    except ValueError:
        return None
    return parsed


def date_from_components(year: int, month: int, day: int) -> str:
    return date(year, month, day).isoformat()


def canonical_watch_url(video_id: str) -> str:
    return f"https://www.youtube.com/watch?v={video_id}"


def parse_video_link(url: str) -> ParsedLink | None:
    cleaned = url.strip().strip("<>")
    try:
        parsed = urlsplit(cleaned)
    except ValueError:
        return None
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return None
    host = parsed.hostname.lower()
    if host.startswith("www."):
        host = host[4:]
    path = unquote(parsed.path)
    segments = [segment for segment in path.split("/") if segment]
    if host == "youtu.be":
        video_id = segments[0] if segments else ""
        if not VIDEO_ID_RE.fullmatch(video_id):
            return None
        return ParsedLink("youtube", video_id, canonical_watch_url(video_id))
    if host in YOUTUBE_HOSTS:
        if segments and segments[0] == "shorts":
            video_id = segments[1] if len(segments) >= 2 else ""
            if not VIDEO_ID_RE.fullmatch(video_id):
                return None
            return ParsedLink("youtube", video_id, canonical_watch_url(video_id))
        if segments and segments[0] == "watch":
            video_id = (parse_qs(parsed.query).get("v") or [""])[0].strip()
            if not VIDEO_ID_RE.fullmatch(video_id):
                return None
            return ParsedLink("youtube", video_id, canonical_watch_url(video_id))
        return ParsedLink("other", "", cleaned)
    if host in {"tv.naver.com", "m.tv.naver.com", "naver.tv"}:
        external_id = ""
        if host == "naver.tv" and segments and segments[0].isdigit():
            external_id = segments[0]
        elif len(segments) >= 2 and segments[0] == "v" and segments[1].isdigit():
            external_id = segments[1]
        return ParsedLink("naver", external_id, cleaned)
    return ParsedLink("other", "", cleaned)


def extract_section_links(section_markdown: str) -> list[str]:
    links: list[str] = []
    seen: set[str] = set()
    for target in _candidate_targets(section_markdown):
        url = target.strip().strip("<>").rstrip(".,;:!?'\"")
        if not url or url in seen:
            continue
        seen.add(url)
        links.append(url)
    return links


def extract_winner_section(markdown: str) -> tuple[bool, str]:
    lines = markdown.splitlines()
    start = None
    for index, line in enumerate(lines):
        match = HEADING_RE.match(line)
        if match and match.group(1).strip().casefold() == "winner":
            start = index + 1
            break
    if start is None:
        return False, ""
    collected: list[str] = []
    for line in lines[start:]:
        if HEADING_RE.match(line):
            break
        collected.append(line)
    return True, "\n".join(collected).strip()


def is_na_winner(text: str) -> bool:
    stripped = re.sub(r"[*_~`]", "", text).strip().rstrip(".").strip()
    return stripped.casefold() == "n/a"


def _page_cache_path(config: Config, page_path: str) -> Path:
    parts = [
        re.sub(r"[^a-z0-9_-]+", "_", part.casefold()) or "_"
        for part in page_path.split("/")
    ]
    return config.reddit_dir.joinpath("pages", *parts).with_suffix(".md")


def _read_cached_page(config: Config, page_path: str) -> str | None:
    path = _page_cache_path(config, page_path)
    return path.read_text(encoding="utf-8") if path.is_file() else None


def _store_page(config: Config, page_path: str, content: str) -> None:
    write_atomic(_page_cache_path(config, page_path), content)


def _load_state(config: Config) -> dict[str, Any]:
    path = config.reddit_dir / "state.json"
    if not path.is_file():
        return {"version": 1}
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"version": 1}
    return state if isinstance(state, dict) else {"version": 1}


def _store_state(config: Config, state: dict[str, Any]) -> None:
    write_atomic(
        config.reddit_dir / "state.json",
        json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )


def _resolve_archive_path(mapped: str, index_links: list[str]) -> str:
    folded = {link.casefold(): link for link in index_links}
    if mapped.casefold() in folded:
        return folded[mapped.casefold()]
    normalized = mapped.casefold().replace("-", "").rsplit("/", 1)[-1]
    for link in index_links:
        if not link.casefold().startswith(REDDIT_ARCHIVE_PREFIX):
            continue
        suffix = link.casefold().rsplit("/", 1)[-1].replace("-", "")
        if suffix == normalized:
            return link
    return mapped


@dataclass
class _Discovery:
    episodes: dict[str, list[EpisodeRef]]
    archive_paths: dict[str, str]
    archive_pages_scanned: int = 0
    indexes_fetched: int = 0


def _discover_episodes(
    client: RedditClient,
    config: Config,
    shows: list[str],
    *,
    refresh_indexes: bool,
    state: dict[str, Any],
    timestamp: str,
) -> _Discovery:
    episodes: dict[str, list[EpisodeRef]] = {show: {} for show in shows}
    archive_paths: dict[str, str] = {}
    scanned = 0
    fetched = 0

    def read_index(page_path: str) -> str:
        nonlocal scanned, fetched
        scanned += 1
        content = None if refresh_indexes else _read_cached_page(config, page_path)
        if content is None:
            content = client.wiki_page(page_path)
            _store_page(config, page_path, content)
            state.setdefault("indexes", {})[page_path.casefold()] = {
                "fetched_at": timestamp
            }
            fetched += 1
        return content

    main_links = extract_wiki_links(read_index(REDDIT_INDEX_PAGE))
    for show in shows:
        mapped = REDDIT_SHOW_ARCHIVES[show]
        archive_path = _resolve_archive_path(mapped, main_links)
        archive_paths[show] = archive_path
        prefix = archive_path.casefold() + "/"
        queue: deque[str] = deque([archive_path])
        visited: set[str] = set()
        scanned_for_show = 0
        while queue and scanned_for_show < MAX_INDEX_PAGES_PER_SHOW:
            page_path = queue.popleft()
            key = page_path.casefold()
            if key in visited:
                continue
            visited.add(key)
            scanned_for_show += 1
            content = read_index(page_path)
            for link in extract_wiki_links(content):
                link_key = link.casefold()
                if link_key == archive_path.casefold() or not link_key.startswith(
                    prefix
                ):
                    continue
                win_date = episode_date(link)
                if win_date is not None:
                    episodes[show][link_key] = EpisodeRef(show, link, win_date)
                elif len(visited) + len(queue) < MAX_INDEX_PAGES_PER_SHOW:
                    queue.append(link)
    return _Discovery(
        episodes={
            show: sorted(pages.values(), key=lambda ref: ref.sort_key)
            for show, pages in episodes.items()
        },
        archive_paths=archive_paths,
        archive_pages_scanned=scanned,
        indexes_fetched=fetched,
    )


def _local_wins(
    connection: sqlite3.Connection, shows: list[str]
) -> dict[tuple[str, str], sqlite3.Row]:
    placeholders = ",".join("?" for _ in shows)
    rows = connection.execute(
        f"""
        SELECT show_slug, win_date, artist_name, song_title
        FROM wins
        WHERE is_current = 1 AND show_slug IN ({placeholders})
        """,
        shows,
    )
    return {(row["show_slug"], row["win_date"]): row for row in rows}


def _candidate_index(
    connection: sqlite3.Connection, shows: list[str]
) -> dict[tuple[str, str], dict[str, dict[str, sqlite3.Row]]]:
    placeholders = ",".join("?" for _ in shows)
    rows = connection.execute(
        f"""
        SELECT id, show_slug, win_date, provider, external_id, url,
               review_status, status, title, publisher_name,
               publisher_external_id
        FROM reference_candidates
        WHERE show_slug IN ({placeholders})
        """,
        shows,
    )
    index: dict[tuple[str, str], dict[str, dict[str, sqlite3.Row]]] = {}
    for row in rows:
        key = (row["show_slug"], row["win_date"])
        entry = index.setdefault(key, {"by_video": {}, "by_url": {}})
        if row["provider"] == "youtube" and row["external_id"]:
            entry["by_video"].setdefault(row["external_id"], row)
        parsed = parse_video_link(row["url"])
        url_key = (
            parsed.canonical_url
            if parsed and parsed.provider == "youtube"
            else row["url"]
        )
        entry["by_url"].setdefault(url_key, row)
    return index


def _channel_metadata(
    connection: sqlite3.Connection, shows: list[str]
) -> tuple[dict[str, set[str]], dict[str, str]]:
    placeholders = ",".join("?" for _ in shows)
    active: dict[str, set[str]] = {show: set() for show in shows}
    titles: dict[str, str] = {}
    for row in connection.execute(
        f"""
        SELECT show_slug, channel_id, channel_title, is_active
        FROM youtube_channels
        WHERE show_slug IN ({placeholders})
        """,
        shows,
    ):
        titles[row["channel_id"]] = row["channel_title"]
        if row["is_active"] == 1:
            active.setdefault(row["show_slug"], set()).add(row["channel_id"])
    return active, titles


def _video_metadata(connection: sqlite3.Connection) -> dict[str, dict[str, str]]:
    return {
        row["video_id"]: {
            "channel_id": row["channel_id"],
            "availability_status": row["availability_status"],
            "title": row["title"],
        }
        for row in connection.execute(
            """
            SELECT video_id, channel_id, title, availability_status
            FROM youtube_videos
            """
        )
    }


def _classify_link(
    *,
    ref: EpisodeRef,
    link_url: str,
    parsed: ParsedLink | None,
    candidates: dict[str, dict[str, sqlite3.Row]] | None,
    official_channels: dict[str, set[str]],
    channel_titles: dict[str, str],
    videos: dict[str, dict[str, str]],
) -> ExtractedLink:
    link = ExtractedLink(
        link_url=link_url,
        provider=parsed.provider if parsed else "unknown",
        external_id=parsed.external_id if parsed else "",
        canonical_url=parsed.canonical_url if parsed else link_url,
        classification="malformed_link",
    )
    if parsed is None:
        return link
    if parsed.provider == "youtube":
        candidate = None
        if candidates is not None:
            candidate = candidates["by_video"].get(parsed.external_id) or candidates[
                "by_url"
            ].get(parsed.canonical_url)
        video = videos.get(parsed.external_id)
        if candidate is not None:
            link.classification = f"existing_{candidate['review_status']}"
            link.existing_review_status = candidate["review_status"]
            link.existing_candidate_id = candidate["id"]
            if video is not None:
                link.video_title = video["title"]
                link.publisher_name = channel_titles.get(
                    video["channel_id"], candidate["publisher_name"]
                )
                link.publisher_external_id = (
                    candidate["publisher_external_id"] or video["channel_id"]
                )
                link.local_video_status = video["availability_status"]
            else:
                link.video_title = candidate["title"]
                link.publisher_name = candidate["publisher_name"]
                link.publisher_external_id = candidate["publisher_external_id"]
            return link
        if video is not None and video["channel_id"] in official_channels.get(
            ref.show_slug, set()
        ):
            link.publisher_name = channel_titles.get(video["channel_id"], "")
            link.publisher_external_id = video["channel_id"]
            link.video_title = video["title"]
            link.local_video_status = video["availability_status"]
            if video["availability_status"] == "active":
                link.classification = "new_official"
            else:
                link.classification = "known_unavailable"
            return link
        link.classification = "new_unverified"
        if video is not None:
            link.video_title = video["title"]
            link.local_video_status = video["availability_status"]
        return link
    candidate = None
    if candidates is not None:
        candidate = candidates["by_url"].get(link.link_url)
    if candidate is not None:
        link.classification = f"existing_{candidate['review_status']}"
        link.existing_review_status = candidate["review_status"]
        link.existing_candidate_id = candidate["id"]
        link.video_title = candidate["title"]
        link.publisher_name = candidate["publisher_name"]
        link.publisher_external_id = candidate["publisher_external_id"]
        return link
    link.classification = "unsupported_link"
    return link


CLASSIFICATION_TOTAL_KEYS = {
    "existing_approved": "existing_approved",
    "existing_pending": "existing_pending",
    "existing_rejected": "existing_rejected",
    "new_official": "new_official",
    "new_unverified": "new_unverified",
    "known_unavailable": "known_unavailable",
    "unsupported_link": "unsupported_links",
    "malformed_link": "malformed_links",
}


def _empty_totals() -> dict[str, int]:
    return {
        "archive_pages_scanned": 0,
        "episode_pages_discovered": 0,
        "episode_pages_cached": 0,
        "episode_pages_fetched": 0,
        "episode_pages_parsed": 0,
        "exact_local_win_matches": 0,
        "episodes_without_local_wins": 0,
        "local_wins_without_episode_pages": 0,
        "missing_winner_sections": 0,
        "winner_na_sections": 0,
        "winner_sections_without_links": 0,
        "parse_failures": 0,
        "total_extracted_links": 0,
        "existing_approved": 0,
        "existing_pending": 0,
        "existing_rejected": 0,
        "new_official": 0,
        "new_unverified": 0,
        "known_unavailable": 0,
        "naver_links": 0,
        "unsupported_links": 0,
        "malformed_links": 0,
    }


def _tsv_cell(value: Any) -> str:
    return str(value).replace("\t", " ").replace("\r", " ").replace("\n", " ")


def _episode_url(page_path: str) -> str:
    return f"https://www.reddit.com/r/kpop/wiki/{page_path}"


def run_reddit_audit(
    connection: sqlite3.Connection,
    config: Config,
    *,
    show: str | None,
    max_pages: int,
    refresh_indexes: bool,
    output_path: Path | None,
    stdout: TextIO,
    session: requests.Session | None = None,
    sleep: Callable[[float], None] = time.sleep,
    now: str | None = None,
) -> AuditOutcome:
    from .registry import SUPPORTED_SHOWS

    client = RedditClient(
        config,
        session=session,
        clock=_fixed_clock(datetime.fromisoformat(now.replace("Z", "+00:00")))
        if now
        else None,
        sleep=sleep,
    )
    timestamp = now or datetime.now(UTC).isoformat().replace("+00:00", "Z")
    shows = [show] if show else sorted(SUPPORTED_SHOWS)
    state = _load_state(config)

    print(
        f"reddit audit: shows={len(shows)} max-pages={max_pages} "
        f"refresh-indexes={'yes' if refresh_indexes else 'no'}",
        file=stdout,
    )
    discovery = _discover_episodes(
        client,
        config,
        shows,
        refresh_indexes=refresh_indexes,
        state=state,
        timestamp=timestamp,
    )
    state["updated_at"] = timestamp
    _store_state(config, state)

    episode_list = [ref for show in shows for ref in discovery.episodes[show]]
    contents: dict[str, str] = {}
    cached_by_show = {show: 0 for show in shows}
    fetched_by_show = {show: 0 for show in shows}
    cached = 0
    fetched = 0
    pending: list[EpisodeRef] = []
    for ref in episode_list:
        content = _read_cached_page(config, ref.page_path)
        if content is None:
            pending.append(ref)
        else:
            contents[ref.page_path.casefold()] = content
            cached += 1
            cached_by_show[ref.show_slug] += 1
    budget = max_pages
    for ref in pending:
        if budget <= 0:
            break
        content = client.wiki_page(ref.page_path)
        _store_page(config, ref.page_path, content)
        contents[ref.page_path.casefold()] = content
        fetched += 1
        fetched_by_show[ref.show_slug] += 1
        budget -= 1
    still_pending = pending[fetched:]
    more_remaining = bool(still_pending)

    wins = _local_wins(connection, shows)
    candidate_index = _candidate_index(connection, shows)
    official_channels, channel_titles = _channel_metadata(connection, shows)
    videos = _video_metadata(connection)

    episode_outcomes: list[EpisodeOutcome] = []
    show_totals: dict[str, dict[str, int]] = {show: _empty_totals() for show in shows}
    totals = _empty_totals()
    totals["archive_pages_scanned"] = discovery.archive_pages_scanned
    totals["episode_pages_discovered"] = len(episode_list)
    totals["episode_pages_cached"] = cached
    totals["episode_pages_fetched"] = fetched

    parsed_refs = [ref for ref in episode_list if ref.page_path.casefold() in contents]
    totals["episode_pages_parsed"] = len(parsed_refs)
    fetched_keys = {ref.sort_key for ref in pending[:fetched]}
    for ref in parsed_refs:
        show_total = show_totals[ref.show_slug]
        source = "fetched" if ref.sort_key in fetched_keys else "cache"
        win_row = wins.get((ref.show_slug, ref.win_date))
        outcome = EpisodeOutcome(
            ref=ref,
            source=source,
            outcome="no_local_win",
            has_local_win=win_row is not None,
            local_artist=win_row["artist_name"] if win_row else "",
            local_song=win_row["song_title"] if win_row else "",
        )
        if win_row is not None:
            outcome.outcome = "matched"
        try:
            found, winner_text = extract_winner_section(
                contents[ref.page_path.casefold()]
            )
        except Exception as exc:
            outcome.outcome = "parse_failure"
            outcome.error = str(exc)
            episode_outcomes.append(outcome)
            continue
        outcome.winner_text = winner_text
        if not found:
            outcome.outcome = "missing_winner_section"
        elif is_na_winner(winner_text):
            outcome.outcome = "winner_na"
        else:
            candidates = candidate_index.get((ref.show_slug, ref.win_date))
            seen_ids: set[str] = set()
            for link_url in extract_section_links(winner_text):
                parsed = parse_video_link(link_url)
                identity = (
                    parsed.external_id
                    if parsed and parsed.provider == "youtube"
                    else (parsed.canonical_url if parsed else link_url)
                )
                if identity in seen_ids:
                    continue
                seen_ids.add(identity)
                link = _classify_link(
                    ref=ref,
                    link_url=link_url,
                    parsed=parsed,
                    candidates=candidates,
                    official_channels=official_channels,
                    channel_titles=channel_titles,
                    videos=videos,
                )
                outcome.links.append(link)
            if not outcome.links:
                outcome.outcome = "winner_without_link"
        episode_outcomes.append(outcome)

    discovered_by_show = {
        show: {ref.win_date for ref in discovery.episodes[show]} for show in shows
    }
    coverage: dict[str, dict[str, Any]] = {}
    for show in shows:
        dates = discovered_by_show[show]
        coverage[show] = {
            "archive_path": discovery.archive_paths[show],
            "coverage_start": min(dates) if dates else None,
            "coverage_end": max(dates) if dates else None,
            "episodes_discovered": len(dates),
        }
    for show in shows:
        show_total = show_totals[show]
        show_total["episode_pages_discovered"] = len(discovery.episodes[show])
        show_total["episode_pages_cached"] = cached_by_show[show]
        show_total["episode_pages_fetched"] = fetched_by_show[show]
        show_total["episode_pages_parsed"] = (
            cached_by_show[show] + fetched_by_show[show]
        )
        start = coverage[show]["coverage_start"]
        end = coverage[show]["coverage_end"]
        for (show_slug, win_date), row in wins.items():
            if show_slug != show:
                continue
            if start and end and start <= win_date <= end:
                if win_date not in discovered_by_show[show]:
                    show_total["local_wins_without_episode_pages"] += 1
    for outcome in episode_outcomes:
        show_total = show_totals[outcome.ref.show_slug]
        if outcome.has_local_win:
            show_total["exact_local_win_matches"] += 1
        else:
            show_total["episodes_without_local_wins"] += 1
        if outcome.outcome == "missing_winner_section":
            show_total["missing_winner_sections"] += 1
        elif outcome.outcome == "winner_na":
            show_total["winner_na_sections"] += 1
        elif outcome.outcome == "winner_without_link":
            show_total["winner_sections_without_links"] += 1
        elif outcome.outcome == "parse_failure":
            show_total["parse_failures"] += 1
        for link in outcome.links:
            show_total["total_extracted_links"] += 1
            if link.provider == "naver":
                show_total["naver_links"] += 1
            total_key = CLASSIFICATION_TOTAL_KEYS.get(link.classification)
            if total_key is not None:
                show_total[total_key] += 1

    for key in totals:
        if key in {
            "archive_pages_scanned",
            "episode_pages_discovered",
            "episode_pages_cached",
            "episode_pages_fetched",
            "episode_pages_parsed",
        }:
            continue
        totals[key] = sum(show_totals[show][key] for show in shows)

    report: dict[str, Any] = {
        "version": 1,
        "generated_at": timestamp,
        "collection_complete": not more_remaining,
        "run_settings": {
            "show_filter": show,
            "max_pages": max_pages,
            "refresh_indexes": refresh_indexes,
        },
        "source": {
            "entry_point": REDDIT_ENTRY_POINT,
            "api_base_url": config.reddit_api_base_url,
            "token_url": config.reddit_token_url,
        },
        "archives": [{"show_slug": show, **coverage[show]} for show in shows],
        "totals": totals,
        "shows": {
            show: {
                **coverage[show],
                "counts": show_totals[show],
            }
            for show in shows
        },
        "pending_episode_pages": [_episode_url(ref.page_path) for ref in still_pending],
        "episodes": [
            {
                "show_slug": outcome.ref.show_slug,
                "win_date": outcome.ref.win_date,
                "episode_path": outcome.ref.page_path,
                "episode_url": _episode_url(outcome.ref.page_path),
                "source": outcome.source,
                "outcome": outcome.outcome,
                "has_local_win": outcome.has_local_win,
                "local_win": (
                    {
                        "artist_name": outcome.local_artist,
                        "song_title": outcome.local_song,
                    }
                    if outcome.has_local_win
                    else None
                ),
                "winner_text": outcome.winner_text,
                "error": outcome.error,
                "links": [
                    {
                        "link_url": link.link_url,
                        "provider": link.provider,
                        "external_id": link.external_id,
                        "canonical_url": link.canonical_url,
                        "classification": link.classification,
                        "video_title": link.video_title,
                        "publisher_name": link.publisher_name,
                        "publisher_external_id": link.publisher_external_id,
                        "existing_review_status": link.existing_review_status,
                        "existing_candidate_id": link.existing_candidate_id,
                        "local_video_status": link.local_video_status,
                    }
                    for link in outcome.links
                ],
            }
            for outcome in episode_outcomes
        ],
    }

    report_path = output_path or config.default_reddit_audit_path
    tsv_path = report_path.with_suffix(".tsv")
    _write_report(report_path, tsv_path, report)

    for show in shows:
        counts = show_totals[show]
        print(
            f"{show}: discovered={counts['episode_pages_discovered']} "
            f"parsed={counts['episode_pages_parsed']} "
            f"matched={counts['exact_local_win_matches']} "
            f"no-local-win={counts['episodes_without_local_wins']} "
            f"gaps={counts['local_wins_without_episode_pages']}",
            file=stdout,
        )
    print(
        "links: total={total} approved={approved} pending={pending} "
        "rejected={rejected} new-official={official} new-unverified={unverified} "
        "known-unavailable={unavailable} naver={naver} "
        "unsupported-or-malformed={bad}".format(
            total=totals["total_extracted_links"],
            approved=totals["existing_approved"],
            pending=totals["existing_pending"],
            rejected=totals["existing_rejected"],
            official=totals["new_official"],
            unverified=totals["new_unverified"],
            unavailable=totals["known_unavailable"],
            naver=totals["naver_links"],
            bad=totals["unsupported_links"] + totals["malformed_links"],
        ),
        file=stdout,
    )
    print(f"report: {report_path}", file=stdout)
    print(f"more-remaining={'yes' if more_remaining else 'no'}", file=stdout)

    return AuditOutcome(
        report_path=report_path,
        tsv_path=tsv_path,
        more_remaining=more_remaining,
        collection_complete=not more_remaining,
        totals=totals,
    )


TSV_COLUMNS = (
    "show_slug",
    "win_date",
    "artist_name",
    "song_title",
    "winner_text",
    "episode_url",
    "link_url",
    "provider",
    "external_id",
    "classification",
    "video_title",
    "publisher_name",
    "publisher_external_id",
    "existing_review_status",
)


def _write_report(report_path: Path, tsv_path: Path, report: dict[str, Any]) -> None:
    write_atomic(
        report_path,
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )
    lines = ["\t".join(TSV_COLUMNS)]
    for episode in report["episodes"]:
        local = episode.get("local_win") or {}
        for link in episode["links"]:
            cells = (
                episode["show_slug"],
                episode["win_date"],
                local.get("artist_name", ""),
                local.get("song_title", ""),
                episode["winner_text"],
                episode["episode_url"],
                link["link_url"],
                link["provider"],
                link["external_id"],
                link["classification"],
                link["video_title"],
                link["publisher_name"],
                link["publisher_external_id"],
                link["existing_review_status"],
            )
            lines.append("\t".join(_tsv_cell(cell) for cell in cells))
    write_atomic(tsv_path, "\n".join(lines) + "\n")
