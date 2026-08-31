from __future__ import annotations

import sqlite3
from io import StringIO

import pytest

from kpopwins_operator import config as config_module
from kpopwins_operator.cli import main
from kpopwins_operator.config import DEFAULT_API_BASE_URL, load_config
from kpopwins_operator.database import (
    SCHEMA_VERSION,
    initialize_database,
    insert_candidate,
    open_database,
)
from kpopwins_operator.validation import TEXT_LIMITS, CandidateValidationError

from .conftest import add_win


def test_configuration_defaults_without_creating_state(tmp_path, monkeypatch):
    monkeypatch.setattr(config_module, "REPOSITORY_ROOT", tmp_path)
    config = load_config({})

    assert config.home == (tmp_path / ".ignore" / "operator-tools").resolve()
    assert config.api_base_url == DEFAULT_API_BASE_URL
    assert not config.database_path.exists()


def test_configuration_overrides(tmp_path):
    config = load_config(
        {
            "KPOPWINS_OPERATOR_HOME": str(tmp_path / "custom"),
            "KPOPWINS_API_BASE_URL": "https://example.test/custom/",
        }
    )

    assert config.home == (tmp_path / "custom").resolve()
    assert config.api_base_url == "https://example.test/custom"


def test_first_and_repeated_initialization(config):
    assert not config.home.exists()

    assert initialize_database(config) == SCHEMA_VERSION
    assert initialize_database(config) == SCHEMA_VERSION

    assert config.database_path.is_file()
    assert config.manifests_dir.is_dir()
    with open_database(config) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION
        tables = {
            row["name"]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
    assert {"wins", "search_state", "reference_candidates"} <= tables


def test_init_cli_prints_resolved_home_and_version(config):
    output = StringIO()
    environment = {"KPOPWINS_OPERATOR_HOME": str(config.home)}

    assert main(["init"], environ=environment, stdout=output) == 0
    assert main(["init"], environ=environment, stdout=output) == 0

    assert f"Operator home: {config.home.resolve()}" in output.getvalue()
    assert "Schema version: 1" in output.getvalue()


def test_candidate_constraints_and_metadata_validation(connection):
    add_win(connection)
    base = {
        "show_slug": " music-bank ",
        "win_date": " 2026-01-02 ",
        "reference_type": " video ",
        "provider": " YouTube ",
        "external_id": " abc123 ",
        "url": " https://example.com/one ",
        "title": " Winner stage ",
        "publisher_name": " Publisher ",
        "publisher_external_id": " channel-id ",
        "metadata": {"duration": 120},
    }
    insert_candidate(connection, base)

    with pytest.raises(sqlite3.IntegrityError):
        insert_candidate(
            connection,
            {
                **base,
                "provider": "youtube",
                "url": "https://example.com/provider-collision",
            },
        )
    with pytest.raises(sqlite3.IntegrityError):
        insert_candidate(
            connection,
            {**base, "external_id": "different"},
        )
    insert_candidate(
        connection,
        {
            **base,
            "external_id": "",
            "url": "https://example.com/two",
        },
    )
    insert_candidate(
        connection,
        {
            **base,
            "external_id": "",
            "url": "https://example.com/three",
        },
    )
    with pytest.raises(ValueError, match="JSON object"):
        insert_candidate(
            connection,
            {**base, "url": "https://example.com/four", "metadata": []},
        )

    stored = connection.execute(
        "SELECT * FROM reference_candidates ORDER BY id LIMIT 1"
    ).fetchone()
    assert stored["show_slug"] == "music-bank"
    assert stored["win_date"] == "2026-01-02"
    assert stored["reference_type"] == "video"
    assert stored["provider"] == "youtube"
    assert stored["external_id"] == "abc123"
    assert stored["url"] == "https://example.com/one"
    assert stored["title"] == "Winner stage"
    assert stored["publisher_name"] == "Publisher"
    assert stored["publisher_external_id"] == "channel-id"
    assert stored["metadata"] == '{"duration":120}'


@pytest.mark.parametrize(("field", "limit"), TEXT_LIMITS.items())
def test_candidate_rejects_each_overlong_backend_field(connection, field, limit):
    add_win(connection)
    candidate = {
        "show_slug": "music-bank",
        "win_date": "2026-01-02",
        "reference_type": "video",
        "provider": "youtube",
        "external_id": "abc123",
        "url": "https://example.com/reference",
        field: "x" * (limit + 1),
    }
    if field == "url":
        candidate[field] = "https://example.com/" + "x" * limit

    with pytest.raises(CandidateValidationError, match=str(limit)):
        insert_candidate(connection, candidate)


@pytest.mark.parametrize("field", ["provider", "url"])
def test_candidate_rejects_blank_provider_and_url(connection, field):
    add_win(connection)
    candidate = {
        "show_slug": "music-bank",
        "win_date": "2026-01-02",
        "reference_type": "video",
        "provider": "youtube",
        "url": "https://example.com/reference",
        field: "   ",
    }

    with pytest.raises(CandidateValidationError, match="required"):
        insert_candidate(connection, candidate)


@pytest.mark.parametrize(
    "url",
    [
        "https://exa mple.com/reference",
        "https:///missing-host",
        "https://exa_mple.com/reference",
        "https://example.com:notaport/reference",
        "https://example.com:99999/reference",
        "https://[not-an-ip]/reference",
        "ftp://example.com/reference",
    ],
)
def test_candidate_rejects_malformed_urls(connection, url):
    add_win(connection)

    with pytest.raises(CandidateValidationError, match="HTTP or HTTPS"):
        insert_candidate(
            connection,
            {
                "show_slug": "music-bank",
                "win_date": "2026-01-02",
                "reference_type": "video",
                "provider": "youtube",
                "url": url,
            },
        )
