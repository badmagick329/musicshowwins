from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from .registry import ChannelEntry
from .youtube import ResolvedChannel, YouTubeClient, YouTubeError


@dataclass(frozen=True)
class VerifiedChannel:
    entry: ChannelEntry
    resolved: ResolvedChannel


def verify_channels(
    entries: list[ChannelEntry],
    client: YouTubeClient,
    *,
    handle: str | None = None,
) -> list[VerifiedChannel]:
    selected = entries
    if handle:
        selected = [
            entry for entry in entries if entry.handle.casefold() == handle.casefold()
        ]
        if not selected:
            raise ValueError(f"Handle {handle} is not in the channel registry.")
    verified = [
        VerifiedChannel(entry, client.resolve_handle(entry.handle))
        for entry in selected
    ]
    by_channel: dict[str, list[VerifiedChannel]] = {}
    for result in verified:
        by_channel.setdefault(result.resolved.channel_id, []).append(result)
    for channel_id, duplicates in by_channel.items():
        if len(duplicates) > 1 and not all(
            result.entry.allow_duplicate_channel for result in duplicates
        ):
            handles = ", ".join(result.entry.handle for result in duplicates)
            raise YouTubeError(
                f"Handles {handles} resolve to duplicate channel ID {channel_id}."
            )
    return verified


def apply_verified_channels(
    connection: sqlite3.Connection,
    verified: list[VerifiedChannel],
    *,
    verified_at: str,
    full_registry: bool,
) -> None:
    with connection:
        if full_registry:
            connection.execute("UPDATE youtube_channels SET is_active = 0")
        for result in verified:
            connection.execute(
                """
                INSERT INTO youtube_channels (
                    show_slug, configured_handle, channel_id, channel_title,
                    uploads_playlist_id, verified_at, is_active
                ) VALUES (?, ?, ?, ?, ?, ?, 1)
                ON CONFLICT (show_slug, configured_handle) DO UPDATE SET
                    channel_id = excluded.channel_id,
                    channel_title = excluded.channel_title,
                    uploads_playlist_id = excluded.uploads_playlist_id,
                    verified_at = excluded.verified_at,
                    is_active = 1
                """,
                (
                    result.entry.show_slug,
                    result.entry.handle,
                    result.resolved.channel_id,
                    result.resolved.title,
                    result.resolved.uploads_playlist_id,
                    verified_at,
                ),
            )
            connection.execute(
                """
                INSERT INTO youtube_ingestion_state (channel_id)
                VALUES (?) ON CONFLICT (channel_id) DO NOTHING
                """,
                (result.resolved.channel_id,),
            )
