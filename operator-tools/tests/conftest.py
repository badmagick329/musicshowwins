from __future__ import annotations

from datetime import date, timedelta

import pytest

from kpopwins_operator.config import Config
from kpopwins_operator.database import initialize_database, open_database


@pytest.fixture
def config(tmp_path):
    return Config(
        home=tmp_path / "operator-home",
        api_base_url="https://api.example.test/api/v1",
    )


@pytest.fixture
def connection(config):
    initialize_database(config)
    database = open_database(config)
    yield database
    database.close()


def add_win(
    connection,
    *,
    show_slug="music-bank",
    win_date="2026-01-02",
    api_win_id=1,
    artist_name="Alpha",
    song_title="First",
    is_current=True,
):
    connection.execute(
        """
        INSERT INTO wins (
            show_slug, win_date, api_win_id, artist_name, song_title,
            is_current, last_seen_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            show_slug,
            win_date,
            api_win_id,
            artist_name,
            song_title,
            int(is_current),
            "2026-08-31T12:00:00Z",
        ),
    )


@pytest.fixture
def wins(connection):
    start = date(2026, 1, 1)
    for index in range(7):
        add_win(
            connection,
            show_slug=f"show-{index % 2}",
            win_date=(start + timedelta(days=index)).isoformat(),
            api_win_id=index + 1,
            artist_name=f"Artist {index}",
            song_title=f"Song {index}",
            is_current=index != 6,
        )
    connection.commit()
    return connection
