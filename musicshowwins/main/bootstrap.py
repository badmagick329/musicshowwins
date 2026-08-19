"""Deterministic transformation of the tracked legacy bootstrap snapshot."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from main.models import normalize_key

MANIFEST_PATH = Path(__file__).resolve().parent / "data" / "bootstrap_cleanup.json"
RAW_COUNTS = {"shows": 6, "artists": 296, "songs": 901, "wins": 2965}
CLEAN_COUNTS = {"shows": 6, "artists": 292, "songs": 885, "wins": 2905}


class CleanupError(ValueError):
    """The tracked bootstrap and cleanup manifest do not agree."""


def load_cleanup_manifest(path: Path = MANIFEST_PATH) -> dict[str, Any]:
    try:
        with path.open(encoding="utf-8") as file:
            manifest = json.load(file)
    except (OSError, json.JSONDecodeError) as exc:
        raise CleanupError(f"Unable to read cleanup manifest: {path}: {exc}") from exc
    if not isinstance(manifest, dict) or manifest.get("version") != 1:
        raise CleanupError("Unsupported bootstrap cleanup manifest version")
    return manifest


def _artist_renames(manifest: dict[str, Any]) -> dict[str, str]:
    rules = manifest.get("artist_renames")
    if not isinstance(rules, list):
        raise CleanupError("Cleanup manifest artist_renames must be a list")
    result: dict[str, str] = {}
    for rule in rules:
        if not isinstance(rule, dict) or not isinstance(rule.get("from"), str):
            raise CleanupError(f"Invalid artist rename rule: {rule!r}")
        source = rule["from"]
        target = rule.get("to")
        if not isinstance(target, str) or not target.strip() or source in result:
            raise CleanupError(f"Invalid or duplicate artist rename rule: {rule!r}")
        result[source] = target
    return result


def _song_renames(manifest: dict[str, Any]) -> dict[tuple[str, str], str]:
    rules = manifest.get("song_renames")
    if not isinstance(rules, list):
        raise CleanupError("Cleanup manifest song_renames must be a list")
    result: dict[tuple[str, str], str] = {}
    for rule in rules:
        if not isinstance(rule, dict):
            raise CleanupError(f"Invalid song rename rule: {rule!r}")
        artist, source, target = (
            rule.get("artist"),
            rule.get("from"),
            rule.get("to"),
        )
        if not all(
            isinstance(value, str) and value.strip()
            for value in (artist, source, target)
        ):
            raise CleanupError(f"Invalid song rename rule: {rule!r}")
        key = (artist, source)
        if key in result:
            raise CleanupError(f"Duplicate song rename rule: {rule!r}")
        result[key] = target
    return result


def _credit_moves(manifest: dict[str, Any]) -> dict[tuple[str, str], str]:
    """Return exact song-scoped credited-artist moves.

    These are deliberately not aliases: a solo artist must not be made an
    alias for a collaboration merely because one song was credited that way.
    """

    rules = manifest.get("credit_moves", [])
    if not isinstance(rules, list):
        raise CleanupError("Cleanup manifest credit_moves must be a list")
    result: dict[tuple[str, str], str] = {}
    for rule in rules:
        if not isinstance(rule, dict):
            raise CleanupError(f"Invalid credit move rule: {rule!r}")
        source_artist, song, target_artist = (
            rule.get("from_artist"),
            rule.get("song"),
            rule.get("to_artist"),
        )
        if not all(
            isinstance(value, str) and value.strip()
            for value in (source_artist, song, target_artist)
        ):
            raise CleanupError(f"Invalid credit move rule: {rule!r}")
        key = (source_artist, song)
        if key in result:
            raise CleanupError(f"Duplicate credit move rule: {rule!r}")
        result[key] = target_artist
    return result


def _date_corrections(manifest: dict[str, Any]) -> dict[tuple[str, str, str, str], str]:
    rules = manifest.get("date_corrections", [])
    if not isinstance(rules, list):
        raise CleanupError("Cleanup manifest date_corrections must be a list")
    result: dict[tuple[str, str, str, str], str] = {}
    for rule in rules:
        if not isinstance(rule, dict):
            raise CleanupError(f"Invalid date correction rule: {rule!r}")
        show, source_date, artist, title, target_date = (
            rule.get("show"),
            rule.get("from"),
            rule.get("artist"),
            rule.get("song"),
            rule.get("to"),
        )
        if not all(
            isinstance(value, str) and value.strip()
            for value in (show, source_date, artist, title, target_date)
        ):
            raise CleanupError(f"Invalid date correction rule: {rule!r}")
        key = (show, source_date, artist, title)
        if key in result:
            raise CleanupError(f"Duplicate date correction rule: {rule!r}")
        result[key] = target_date
    return result


def _rename_row(
    row: dict[str, Any],
    artist_rules: dict[str, str],
    song_rules: dict[tuple[str, str], str],
    credit_moves: dict[tuple[str, str], str] | None = None,
) -> dict[str, Any]:
    source_artist = row["artist"]
    source_title = row["title"]
    artist = artist_rules.get(source_artist, source_artist)
    title = song_rules.get((source_artist, source_title), source_title)
    if credit_moves:
        artist = credit_moves.get((artist, title), artist)
    return {
        **row,
        "artist": artist,
        "title": title,
    }


def _counter(rows: list[dict[str, Any]]) -> Counter[tuple[str, str]]:
    return Counter(
        (row.get("artist"), row.get("song", row.get("title"))) for row in rows
    )


def _retained_decision_row(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Return the retained row, or None for a deliberately ambiguous decision."""

    retained = [row for row in rows if row.get("action") == "keep"]
    return retained[0] if len(retained) == 1 else None


def _legacy_discrepancy_candidate(
    row: dict[str, Any], retained: dict[str, Any] | None
) -> dict[str, Any]:
    return {
        "show": row["show"],
        "date": row["date"],
        "artist": row["artist"],
        "song": row["title"],
        "retained": (
            {"artist": retained["artist"], "song": retained["song"]}
            if retained is not None
            else None
        ),
    }


def _validate_source_counts(payload: dict[str, Any]) -> None:
    for key, expected in RAW_COUNTS.items():
        rows = payload.get(key)
        if not isinstance(rows, list) or len(rows) != expected:
            actual = len(rows) if isinstance(rows, list) else "invalid"
            raise CleanupError(f"Expected {expected} raw {key}; got {actual}")


def apply_cleanup(
    payload: dict[str, Any], manifest: dict[str, Any] | None = None
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Apply only exact rules from the tracked manifest to a raw snapshot."""

    if payload.get("version") != 1:
        raise CleanupError("Unsupported bootstrap data version")
    _validate_source_counts(payload)
    manifest = manifest or load_cleanup_manifest()
    if manifest.get("version") != 1:
        raise CleanupError("Unsupported bootstrap cleanup manifest version")
    artist_rules = _artist_renames(manifest)
    song_rules = _song_renames(manifest)
    credit_moves = _credit_moves(manifest)
    date_corrections = _date_corrections(manifest)

    source_artists = {row.get("name") for row in payload["artists"]}
    if any(source not in source_artists for source in artist_rules):
        missing = sorted(set(artist_rules) - source_artists)
        raise CleanupError(f"Artist rename source missing from bootstrap: {missing}")
    source_songs = {(row.get("artist"), row.get("title")) for row in payload["songs"]}
    if any(source not in source_songs for source in song_rules):
        missing = sorted(set(song_rules) - source_songs)
        raise CleanupError(f"Song rename source missing from bootstrap: {missing}")
    for source_artist, source_title in credit_moves:
        if (source_artist, source_title) not in source_songs:
            raise CleanupError(
                "Credit move source missing from bootstrap: "
                f"{source_artist} / {source_title}"
            )
    for (show, source_date, artist, title), _target_date in date_corrections.items():
        if not any(
            row.get("show") == show
            and row.get("date") == source_date
            and row.get("artist") == artist
            and row.get("title") == title
            for row in payload["wins"]
        ):
            raise CleanupError(
                "Date correction source missing from bootstrap: "
                f"{show} / {source_date} / {artist} / {title}"
            )

    undated = manifest.get("undated_issues")
    if not isinstance(undated, list) or len(undated) != 33:
        raise CleanupError("The Music Core 2016 undated backlog must contain 33 rows")
    raw_undated_wins = [
        row
        for row in payload["wins"]
        if row.get("show") == "music-core" and row.get("date") == "2016-01-01"
    ]
    expected_undated = Counter(
        (
            row["source_artist"],
            row.get("source_song", row["song"]),
        )
        for row in undated
    )
    actual_undated = Counter((row["artist"], row["title"]) for row in raw_undated_wins)
    if actual_undated != expected_undated:
        raise CleanupError("Music Core 2016 undated manifest does not match raw wins")

    decisions = manifest.get("date_decisions")
    if not isinstance(decisions, list):
        raise CleanupError("Cleanup manifest date_decisions must be a list")
    decision_map: dict[tuple[str, str], dict[str, Any]] = {}
    for decision in decisions:
        if not isinstance(decision, dict):
            raise CleanupError(f"Invalid date decision: {decision!r}")
        key = (decision.get("show"), decision.get("date"))
        rows = decision.get("rows")
        if (
            key in decision_map
            or not all(isinstance(value, str) for value in key)
            or not isinstance(rows, list)
        ):
            raise CleanupError(f"Invalid or duplicate date decision: {decision!r}")
        actions = [row.get("action") for row in rows if isinstance(row, dict)]
        keep_count = actions.count("keep")
        if (
            keep_count > 1
            or (keep_count == 0 and any(action != "quarantine" for action in actions))
            or any(
                action not in {"keep", "discard", "quarantine"} for action in actions
            )
        ):
            raise CleanupError(f"Date decision must have one keep action: {decision!r}")
        decision_map[key] = decision

    corrected_wins: list[dict[str, Any]] = []
    for row in payload["wins"]:
        corrected_date = date_corrections.get(
            (row["show"], row["date"], row["artist"], row["title"]), row["date"]
        )
        corrected_wins.append({**row, "date": corrected_date})

    wins_by_date: defaultdict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in corrected_wins:
        wins_by_date[(row["show"], row["date"])].append(row)

    cleaned_wins: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []
    for key, rows in wins_by_date.items():
        if key == ("music-core", "2016-01-01"):
            continue
        decision = decision_map.get(key)
        if len(rows) > 1 and decision is None:
            transformed = [
                _rename_row(row, artist_rules, song_rules, credit_moves) for row in rows
            ]
            if len({(row["artist"], row["title"]) for row in transformed}) != 1:
                raise CleanupError(
                    f"Duplicate show/date has no manifest decision: {key}"
                )
            # An exact date correction can bring a legacy row onto an already
            # restored identical row. Keep one copy deterministically.
            rows = rows[:1]
        if len(rows) == 1 and decision is not None:
            raise CleanupError(f"Manifest decision is unused for unique date: {key}")
        action_map: dict[tuple[str, str], dict[str, Any]] = {}
        if decision is not None:
            decision_rows = decision["rows"]
            if _counter(decision_rows) != Counter(
                (row["artist"], row["title"]) for row in rows
            ):
                raise CleanupError(
                    f"Manifest rows do not exactly match source rows: {key}"
                )
            for action_row in decision_rows:
                row_key = (action_row["artist"], action_row["song"])
                if row_key in action_map:
                    raise CleanupError(
                        f"Duplicate manifest row decision: {key} {row_key}"
                    )
                action_map[row_key] = action_row
        retained_row = _retained_decision_row(decision["rows"]) if decision else None
        for row in rows:
            action_row = action_map.get((row["artist"], row["title"]))
            if action_row and action_row["action"] != "keep":
                if action_row["action"] == "quarantine":
                    issues.append(
                        {
                            "issue_type": "legacy_discrepancy",
                            "candidate": _legacy_discrepancy_candidate(
                                row, retained_row
                            ),
                            "notes": action_row.get(
                                "reason", "Legacy row differs from current Wikipedia."
                            ),
                        }
                    )
                continue
            cleaned_wins.append(
                _rename_row(row, artist_rules, song_rules, credit_moves)
            )

    for row in undated:
        issues.append(
            {
                "issue_type": "legacy_undated",
                "candidate": {
                    "show": "music-core",
                    "year": 2016,
                    "artist": row["artist"],
                    "song": row["song"],
                    "expected_wins": row["expected_wins"],
                },
                "notes": (
                    "Restored from the aggregate-only 2016 Music Core history; "
                    "exact dates require manual research."
                ),
            }
        )

    cleaned_artists: list[dict[str, Any]] = []
    seen_artists: set[str] = set()
    for row in payload["artists"]:
        name = artist_rules.get(row["name"], row["name"])
        identity = normalize_key(name)
        if identity in seen_artists:
            continue
        seen_artists.add(identity)
        cleaned_artists.append({**row, "name": name})
    for name in credit_moves.values():
        identity = normalize_key(name)
        if identity not in seen_artists:
            seen_artists.add(identity)
            cleaned_artists.append({"name": name})

    cleaned_songs: list[dict[str, Any]] = []
    seen_songs: set[tuple[str, str]] = set()
    for row in payload["songs"]:
        cleaned = _rename_row(
            {"artist": row["artist"], "title": row["title"]},
            artist_rules,
            song_rules,
            credit_moves,
        )
        key = (cleaned["artist"], normalize_key(cleaned["title"]))
        if key in seen_songs:
            continue
        seen_songs.add(key)
        cleaned_songs.append(cleaned)

    cleaned_payload = {
        "version": payload["version"],
        "shows": payload["shows"],
        "artists": cleaned_artists,
        "songs": cleaned_songs,
        "aliases": payload["aliases"],
        "wins": cleaned_wins,
    }
    for key, expected in CLEAN_COUNTS.items():
        actual = len(cleaned_payload[key])
        if actual != expected:
            raise CleanupError(f"Expected {expected} cleaned {key}; got {actual}")
    win_keys = [(row["show"], row["date"]) for row in cleaned_wins]
    if len(win_keys) != len(set(win_keys)):
        raise CleanupError("Cleanup manifest leaves duplicate show/date wins")
    if len(issues) != 45:
        raise CleanupError(f"Expected 45 cleanup issues; got {len(issues)}")
    return cleaned_payload, issues
