from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any, Callable
from zoneinfo import ZoneInfo

import requests

from .config import Config

USER_AGENT = "KpopWinsOperator/0.1 (+https://github.com/badmagick329/musicshowwins)"


class YouTubeError(RuntimeError):
    pass


class APIKeyMissing(YouTubeError):
    pass


class QuotaExceeded(YouTubeError):
    pass


class APICallLimit(YouTubeError):
    pass


@dataclass(frozen=True)
class ResolvedChannel:
    channel_id: str
    title: str
    uploads_playlist_id: str


@dataclass(frozen=True)
class PlaylistPage:
    video_ids: tuple[str, ...]
    published_at: dict[str, str]
    next_page_token: str | None


@dataclass(frozen=True)
class Video:
    video_id: str
    channel_id: str
    title: str
    description: str
    published_at: str
    duration: str
    privacy_status: str
    embeddable: bool
    live_broadcast_state: str


class YouTubeClient:
    def __init__(
        self,
        config: Config,
        connection: sqlite3.Connection,
        *,
        session: requests.Session | None = None,
        clock: Callable[[], datetime] | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if not config.youtube_api_key:
            raise APIKeyMissing("YOUTUBE_API_KEY is required for YouTube commands.")
        self._key = config.youtube_api_key
        self._base_url = config.youtube_api_base_url
        self._limit = config.youtube_max_api_calls_per_run
        self._connection = connection
        self._session = session or requests.Session()
        self._clock = clock or (lambda: datetime.now(UTC))
        self._sleep = sleep
        self.calls_used = 0

    def _record_call(self, method: str) -> None:
        instant = self._clock()
        if instant.tzinfo is None:
            instant = instant.replace(tzinfo=UTC)
        pacific_date = (
            instant.astimezone(ZoneInfo("America/Los_Angeles")).date().isoformat()
        )
        self._connection.execute(
            """
            INSERT INTO youtube_api_usage (pacific_date, api_method, call_count)
            VALUES (?, ?, 1)
            ON CONFLICT (pacific_date, api_method) DO UPDATE
            SET call_count = call_count + 1
            """,
            (pacific_date, method),
        )
        self._connection.commit()

    def _retry_delay(self, response: requests.Response, attempt: int) -> float:
        value = response.headers.get("Retry-After")
        if value:
            try:
                return min(max(float(value), 0), 30)
            except ValueError:
                try:
                    target = parsedate_to_datetime(value)
                    now = self._clock()
                    if now.tzinfo is None:
                        now = now.replace(tzinfo=UTC)
                    return min(max((target - now).total_seconds(), 0), 30)
                except (TypeError, ValueError, OverflowError):
                    pass
        return min(2**attempt, 8)

    @staticmethod
    def _quota_error(payload: Any) -> bool:
        if not isinstance(payload, dict):
            return False
        errors = payload.get("error", {}).get("errors", [])
        return any(
            isinstance(error, dict) and error.get("reason") == "quotaExceeded"
            for error in errors
        )

    def _get(
        self, resource: str, method: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        for attempt in range(4):
            if self.calls_used >= self._limit:
                raise APICallLimit(
                    f"YouTube API call limit reached ({self._limit} attempted calls)."
                )
            self.calls_used += 1
            try:
                response = self._session.get(
                    f"{self._base_url}/{resource}",
                    params={**params, "key": self._key},
                    headers={"User-Agent": USER_AGENT},
                    timeout=(5, 30),
                )
            except requests.RequestException as exc:
                self._record_call(method)
                if attempt == 3:
                    raise YouTubeError(f"YouTube API {method} request failed.") from exc
                self._sleep(min(2**attempt, 8))
                continue
            self._record_call(method)
            try:
                payload = response.json()
            except ValueError as exc:
                if response.status_code in {429, 500, 502, 503, 504} and attempt < 3:
                    self._sleep(self._retry_delay(response, attempt))
                    continue
                raise YouTubeError(
                    f"YouTube API {method} returned invalid JSON."
                ) from exc
            if response.status_code == 403 and self._quota_error(payload):
                raise QuotaExceeded("YouTube API quota is exhausted for today.")
            if response.status_code == 429 or 500 <= response.status_code <= 599:
                if attempt < 3:
                    self._sleep(self._retry_delay(response, attempt))
                    continue
            if response.status_code >= 400:
                raise YouTubeError(
                    f"YouTube API {method} failed with HTTP {response.status_code}."
                )
            if not isinstance(payload, dict):
                raise YouTubeError(
                    f"YouTube API {method} returned an invalid response."
                )
            return payload
        raise YouTubeError(f"YouTube API {method} request failed.")

    def resolve_handle(self, handle: str) -> ResolvedChannel:
        payload = self._get(
            "channels",
            "channels.list",
            {
                "part": "id,snippet,contentDetails",
                "forHandle": handle,
                "fields": (
                    "items(id,snippet/title,contentDetails/relatedPlaylists/uploads)"
                ),
            },
        )
        items = payload.get("items")
        if (
            not isinstance(items, list)
            or len(items) != 1
            or not isinstance(items[0], dict)
        ):
            raise YouTubeError(
                f"YouTube handle {handle} did not resolve to one channel."
            )
        item = items[0]
        try:
            channel_id = item["id"]
            title = item["snippet"]["title"]
            uploads = item["contentDetails"]["relatedPlaylists"]["uploads"]
        except (KeyError, TypeError) as exc:
            raise YouTubeError(
                f"YouTube channel response for {handle} is incomplete."
            ) from exc
        if not all(
            isinstance(value, str) and value for value in (channel_id, title, uploads)
        ):
            raise YouTubeError(f"YouTube channel response for {handle} is incomplete.")
        return ResolvedChannel(channel_id, title, uploads)

    def playlist_page(self, playlist_id: str, page_token: str | None) -> PlaylistPage:
        params: dict[str, Any] = {
            "part": "contentDetails,snippet",
            "playlistId": playlist_id,
            "maxResults": 50,
            "fields": (
                "nextPageToken,items(contentDetails(videoId,videoPublishedAt),"
                "snippet/publishedAt)"
            ),
        }
        if page_token:
            params["pageToken"] = page_token
        payload = self._get("playlistItems", "playlistItems.list", params)
        items = payload.get("items")
        if not isinstance(items, list):
            raise YouTubeError("YouTube playlist response is incomplete.")
        ids: list[str] = []
        dates: dict[str, str] = {}
        for item in items:
            try:
                video_id = item["contentDetails"]["videoId"]
                published = item["contentDetails"].get("videoPublishedAt")
                if published is None:
                    published = item["snippet"]["publishedAt"]
            except (KeyError, TypeError) as exc:
                raise YouTubeError("YouTube playlist response is incomplete.") from exc
            if not isinstance(video_id, str) or not isinstance(published, str):
                raise YouTubeError("YouTube playlist response is incomplete.")
            ids.append(video_id)
            dates[video_id] = published
        token = payload.get("nextPageToken")
        if token is not None and not isinstance(token, str):
            raise YouTubeError("YouTube playlist response has an invalid page token.")
        return PlaylistPage(tuple(ids), dates, token)

    def videos(self, video_ids: list[str]) -> list[Video]:
        if len(video_ids) > 50:
            raise ValueError("videos.list accepts at most 50 identifiers.")
        if not video_ids:
            return []
        payload = self._get(
            "videos",
            "videos.list",
            {
                "part": "snippet,contentDetails,status",
                "id": ",".join(video_ids),
                "maxResults": 50,
                "fields": (
                    "items(id,snippet(channelId,title,description,publishedAt,"
                    "liveBroadcastContent),contentDetails/duration,"
                    "status(privacyStatus,embeddable))"
                ),
            },
        )
        items = payload.get("items")
        if not isinstance(items, list):
            raise YouTubeError("YouTube videos response is incomplete.")
        videos: list[Video] = []
        for item in items:
            try:
                snippet = item["snippet"]
                status = item["status"]
                values = {
                    "video_id": item["id"],
                    "channel_id": snippet["channelId"],
                    "title": snippet["title"],
                    "description": snippet.get("description", ""),
                    "published_at": snippet["publishedAt"],
                    "duration": item["contentDetails"].get("duration", ""),
                    "privacy_status": status.get("privacyStatus", ""),
                    "embeddable": status.get("embeddable", True),
                    "live_broadcast_state": snippet.get("liveBroadcastContent", "none"),
                }
            except (KeyError, TypeError) as exc:
                raise YouTubeError("YouTube videos response is incomplete.") from exc
            text_fields = (
                "video_id",
                "channel_id",
                "title",
                "description",
                "published_at",
                "duration",
                "privacy_status",
                "live_broadcast_state",
            )
            if (
                any(not isinstance(values[field], str) for field in text_fields)
                or not values["video_id"]
                or not values["channel_id"]
                or not values["title"]
                or not values["published_at"]
                or not isinstance(values["embeddable"], bool)
            ):
                raise YouTubeError("YouTube videos response is incomplete.")
            videos.append(Video(**values))
        return videos
