from __future__ import annotations

import sqlite3

import pytest

from kpopwins_operator import config as config_module
from kpopwins_operator.config import load_config
from kpopwins_operator.database import (
    MIGRATION_1_TO_2,
    SCHEMA_V1,
    initialize_database,
    open_database,
)
from kpopwins_operator.registry import SUPPORTED_SHOWS, RegistryError, load_registry


def test_env_file_loads_before_process_overrides(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    (home / ".env").write_text(
        "YOUTUBE_API_KEY=file-key\nYOUTUBE_MAX_API_CALLS_PER_RUN=42\n",
        encoding="utf-8",
    )
    config = load_config(
        {
            "KPOPWINS_OPERATOR_HOME": str(home),
            "YOUTUBE_API_KEY": "process-key",
        }
    )
    assert config.youtube_api_key == "process-key"
    assert config.youtube_max_api_calls_per_run == 42


def test_tracked_registry_has_the_six_supported_shows():
    path = (
        config_module.REPOSITORY_ROOT
        / "operator-tools"
        / "official-youtube-channels.toml"
    )
    entries = load_registry(path)
    assert {entry.show_slug for entry in entries} == SUPPORTED_SHOWS
    assert {entry.handle for entry in entries} == {
        "@KBSKpop",
        "@MBCkpop",
        "@SBSKPOP",
        "@Mnet",
        "@ALLTHEKPOP",
        "@THEKPOP",
    }


def test_registry_rejects_duplicate_handles(tmp_path):
    path = tmp_path / "channels.toml"
    rows = []
    for show in sorted(SUPPORTED_SHOWS):
        rows.append(
            "[[channels]]\n"
            f'show_slug = "{show}"\n'
            'handle = "@same"\nkeywords = ["show"]\n'
        )
    path.write_text("\n".join(rows), encoding="utf-8")
    with pytest.raises(RegistryError, match="duplicate handle"):
        load_registry(path)


def test_real_version_one_to_two_migration_preserves_rows(config):
    config.home.mkdir(parents=True)
    connection = sqlite3.connect(config.database_path)
    connection.executescript(SCHEMA_V1)
    connection.execute("PRAGMA user_version = 1")
    connection.execute(
        """
        INSERT INTO wins VALUES (
            'music-bank', '2026-01-02', 1, 'Alpha', 'First', 1,
            '2026-08-31T00:00:00Z'
        )
        """
    )
    connection.execute(
        """
        INSERT INTO reference_candidates (
            show_slug, win_date, reference_type, provider, external_id, url,
            review_status, created_at, updated_at
        ) VALUES (
            'music-bank', '2026-01-02', 'video', 'youtube', 'v1',
            'https://youtube.com/watch?v=v1', 'approved', 'x', 'x'
        )
        """
    )
    connection.commit()
    connection.close()

    assert initialize_database(config) == 3
    with open_database(config) as migrated:
        assert migrated.execute("SELECT COUNT(*) FROM wins").fetchone()[0] == 1
        assert (
            migrated.execute(
                "SELECT review_status FROM reference_candidates"
            ).fetchone()[0]
            == "approved"
        )
        assert migrated.execute(
            "SELECT name FROM sqlite_master WHERE name='youtube_videos'"
        ).fetchone()


def test_version_two_to_three_migration_preserves_videos_and_adds_lookup_state(config):
    config.home.mkdir(parents=True)
    connection = sqlite3.connect(config.database_path)
    connection.executescript(SCHEMA_V1)
    connection.executescript(MIGRATION_1_TO_2)
    connection.execute("PRAGMA user_version = 2")
    connection.execute(
        """
        INSERT INTO youtube_videos (
            video_id, channel_id, title, published_at, first_seen_at, last_seen_at
        ) VALUES ('v1', 'UC1', 'Existing', '2026-01-01T00:00:00Z', 'old', 'old')
        """
    )
    connection.commit()
    connection.close()

    assert initialize_database(config) == 3
    with open_database(config) as migrated:
        row = migrated.execute(
            "SELECT title, channel_title FROM youtube_videos WHERE video_id='v1'"
        ).fetchone()
        assert tuple(row) == ("Existing", "")
        assert migrated.execute(
            "SELECT name FROM sqlite_master WHERE name='reddit_youtube_lookup_state'"
        ).fetchone()
