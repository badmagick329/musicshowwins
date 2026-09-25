from __future__ import annotations

import sqlite3

import pytest

from kpopwins_operator import config as config_module
from kpopwins_operator.config import load_config
from kpopwins_operator.database import (
    MIGRATION_1_TO_2,
    MIGRATION_2_TO_3,
    MIGRATION_3_TO_4,
    MIGRATION_4_TO_5,
    SCHEMA_V1,
    SCHEMA_VERSION,
    initialize_database,
    open_database,
)
from kpopwins_operator.registry import SUPPORTED_SHOWS, RegistryError, load_registry


def test_version_four_upgrade_preserves_existing_review_history(config):
    config.home.mkdir(parents=True)
    with sqlite3.connect(config.database_path) as old:
        old.executescript(
            SCHEMA_V1 + MIGRATION_1_TO_2 + MIGRATION_2_TO_3 + MIGRATION_3_TO_4
        )
        old.execute("PRAGMA user_version=4")
        old.execute(
            "INSERT INTO wins VALUES ('music-bank', '2026-01-02', "
            "1, 'Alpha', 'First', 1, 'now')"
        )
        old.execute("""INSERT INTO reference_candidates (
            show_slug, win_date, reference_type, provider, url, review_status,
            created_at, updated_at
        ) VALUES ('music-bank', '2026-01-02', 'video', 'youtube',
                  'https://youtube.com/watch?v=v1', 'approved', 'now', 'now')""")
        old.execute("""INSERT INTO candidate_review_events (
            candidate_id, previous_status, decision, reviewer, reason,
            reviewed_at, artist_name, song_title
        ) VALUES (1, 'pending', 'approved', 'agent', 'Verified episode',
                  'now', 'Alpha', 'First')""")
    initialize_database(config)
    with open_database(config) as upgraded:
        assert (
            upgraded.execute(
                "SELECT review_status FROM reference_candidates"
            ).fetchone()[0]
            == "approved"
        )
        assert (
            upgraded.execute("SELECT reason FROM candidate_review_events").fetchone()[0]
            == "Verified episode"
        )
        assert (
            upgraded.execute("SELECT COUNT(*) FROM review_batches").fetchone()[0] == 0
        )


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
    assert {entry.handle for entry in entries if entry.ingest_uploads} == {
        "@KBSKpop",
        "@MBCkpop",
        "@SBSKPOP",
        "@Mnet",
        "@ALLTHEKPOP",
        "@THEKPOP",
    }


def test_registry_reads_reference_only_channels(tmp_path):
    path = tmp_path / "channels.toml"
    rows = [
        f'[[channels]]\nshow_slug = "{show}"\nhandle = "@{show}"\nkeywords = ["show"]\n'
        for show in sorted(SUPPORTED_SHOWS)
    ]
    rows.append(
        '[[channels]]\nshow_slug = "music-bank"\nhandle = "@broadcaster"\n'
        'keywords = ["music bank"]\ningest_uploads = false\n'
    )
    path.write_text("\n".join(rows), encoding="utf-8")
    entries = {entry.handle: entry for entry in load_registry(path)}
    assert entries["@music-bank"].ingest_uploads is True
    assert entries["@broadcaster"].ingest_uploads is False

    path.write_text(
        "\n".join(rows).replace("ingest_uploads = false", 'ingest_uploads = "no"'),
        encoding="utf-8",
    )
    with pytest.raises(RegistryError, match="ingest_uploads"):
        load_registry(path)


def test_version_five_upgrade_keeps_channels_ingesting(config):
    config.home.mkdir(parents=True)
    with sqlite3.connect(config.database_path) as old:
        old.executescript(
            SCHEMA_V1
            + MIGRATION_1_TO_2
            + MIGRATION_2_TO_3
            + MIGRATION_3_TO_4
            + MIGRATION_4_TO_5
        )
        old.execute("PRAGMA user_version=5")
        old.execute("""INSERT INTO youtube_channels (
            show_slug, configured_handle, channel_id, channel_title,
            uploads_playlist_id, verified_at
        ) VALUES ('music-bank', '@KBSKpop', 'UC1', 'KBS Kpop', 'UU1', 'now')""")
    initialize_database(config)
    with open_database(config) as upgraded:
        row = upgraded.execute("SELECT ingest_uploads FROM youtube_channels").fetchone()
        assert row[0] == 1


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

    assert initialize_database(config) == SCHEMA_VERSION
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

    assert initialize_database(config) == SCHEMA_VERSION
    with open_database(config) as migrated:
        row = migrated.execute(
            "SELECT title, channel_title FROM youtube_videos WHERE video_id='v1'"
        ).fetchone()
        assert tuple(row) == ("Existing", "")
        assert migrated.execute(
            "SELECT name FROM sqlite_master WHERE name='reddit_youtube_lookup_state'"
        ).fetchone()
