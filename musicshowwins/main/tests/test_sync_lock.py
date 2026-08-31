import pytest
from django.core.management.base import CommandError

from main.management.commands import sync_wikipedia


class FakeCursor:
    def __init__(self, connection):
        self.connection = connection

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, sql, params):
        self.connection.queries.append((sql, params))

    def fetchone(self):
        return [self.connection.acquired]


class FakeConnection:
    vendor = "postgresql"

    def __init__(self, acquired=True):
        self.acquired = acquired
        self.queries = []

    def cursor(self):
        return FakeCursor(self)


def test_sync_lock_is_acquired_and_released(monkeypatch):
    connection = FakeConnection()
    monkeypatch.setattr(sync_wikipedia, "connection", connection)

    with sync_wikipedia.wikipedia_sync_lock():
        assert len(connection.queries) == 1

    assert [query for query, _params in connection.queries] == [
        "SELECT pg_try_advisory_lock(%s)",
        "SELECT pg_advisory_unlock(%s)",
    ]


def test_sync_lock_refuses_a_concurrent_run(monkeypatch):
    connection = FakeConnection(acquired=False)
    monkeypatch.setattr(sync_wikipedia, "connection", connection)

    with pytest.raises(CommandError, match="already running"):
        with sync_wikipedia.wikipedia_sync_lock():
            raise AssertionError("unreachable")

    assert len(connection.queries) == 1


def test_sync_lock_releases_after_an_error(monkeypatch):
    connection = FakeConnection()
    monkeypatch.setattr(sync_wikipedia, "connection", connection)

    with pytest.raises(RuntimeError, match="import failed"):
        with sync_wikipedia.wikipedia_sync_lock():
            raise RuntimeError("import failed")

    assert connection.queries[-1][0] == "SELECT pg_advisory_unlock(%s)"
