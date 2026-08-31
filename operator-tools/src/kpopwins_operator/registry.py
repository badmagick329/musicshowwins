from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

SUPPORTED_SHOWS = {
    "inkigayo",
    "m-countdown",
    "music-bank",
    "music-core",
    "show-champion",
    "the-show",
}


class RegistryError(ValueError):
    pass


@dataclass(frozen=True)
class ChannelEntry:
    show_slug: str
    handle: str
    keywords: tuple[str, ...]
    allow_duplicate_channel: bool = False


def load_registry(path: Path) -> list[ChannelEntry]:
    try:
        document = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise RegistryError(f"Could not load channel registry: {exc}") from exc
    rows = document.get("channels")
    if not isinstance(rows, list):
        raise RegistryError("Channel registry must contain [[channels]] entries.")
    entries: list[ChannelEntry] = []
    identities: set[tuple[str, str]] = set()
    handles: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            raise RegistryError("Each channel registry entry must be a table.")
        show = str(row.get("show_slug", "")).strip()
        handle = str(row.get("handle", "")).strip()
        raw_keywords = row.get("keywords")
        allowed = {"show_slug", "handle", "keywords", "allow_duplicate_channel"}
        if set(row) - allowed or show not in SUPPORTED_SHOWS:
            raise RegistryError(
                f"Invalid channel registry entry for {show or '<blank>'}."
            )
        if (
            not handle.startswith("@")
            or len(handle) < 2
            or any(ch.isspace() for ch in handle)
        ):
            raise RegistryError(f"Invalid YouTube handle for {show}.")
        if not isinstance(raw_keywords, list) or not raw_keywords:
            raise RegistryError(f"Channel keywords are required for {show}.")
        keywords = tuple(str(keyword).strip() for keyword in raw_keywords)
        if any(not keyword for keyword in keywords):
            raise RegistryError(f"Channel keywords must not be blank for {show}.")
        identity = (show, handle.casefold())
        if identity in identities or handle.casefold() in handles:
            raise RegistryError("Channel registry contains a duplicate handle.")
        if "allow_duplicate_channel" in row and not isinstance(
            row["allow_duplicate_channel"], bool
        ):
            raise RegistryError("allow_duplicate_channel must be true or false.")
        identities.add(identity)
        handles.add(handle.casefold())
        entries.append(
            ChannelEntry(
                show_slug=show,
                handle=handle,
                keywords=keywords,
                allow_duplicate_channel=row.get("allow_duplicate_channel", False)
                is True,
            )
        )
    if {entry.show_slug for entry in entries} != SUPPORTED_SHOWS:
        raise RegistryError(
            "Channel registry must configure every supported show at least once."
        )
    return entries
