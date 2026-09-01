from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime

import pytest
import requests

from kpopwins_operator.config import Config, ConfigurationError, load_config
from kpopwins_operator.reddit import (
    RedditClient,
    RedditCredentialsMissing,
    RedditError,
)


class Response:
    def __init__(self, payload, status=200, headers=None):
        self.payload = payload
        self.status_code = status
        self.headers = headers or {}

    def json(self):
        if isinstance(self.payload, Exception):
            raise self.payload
        return deepcopy(self.payload)


class Session:
    def __init__(self, post_responses=None, get_responses=None, pages=None):
        self.post_responses = list(post_responses or [])
        self.get_responses = list(get_responses or [])
        self.pages = dict(pages or {})
        self.posts = []
        self.gets = []

    def post(self, url, **kwargs):
        self.posts.append((url, kwargs))
        if self.post_responses:
            return self.post_responses.pop(0)
        return Response(
            {"access_token": "token-1", "token_type": "bearer", "expires_in": 3600}
        )

    def get(self, url, **kwargs):
        self.gets.append((url, kwargs))
        if self.get_responses:
            return self.get_responses.pop(0)
        page = self.pages.get(url)
        if page is None:
            return Response({"message": "Not Found"}, 404)
        return Response({"kind": "wikipage", "data": {"content_md": page}})


def reddit_config(config, **changes):
    values = {
        "home": config.home,
        "api_base_url": config.api_base_url,
        "reddit_client_id": "client-id",
        "reddit_client_secret": "client-secret",
        "reddit_user_agent": "KpopWinsOperator/0.1 (audit)",
        "reddit_token_url": "https://reddit.example/api/v1/access_token",
        "reddit_api_base_url": "https://oauth.reddit.test",
    }
    values.update(changes)
    return Config(**values)


def test_missing_credentials_are_reported_by_name(config):
    with pytest.raises(RedditCredentialsMissing) as first:
        RedditClient(reddit_config(config, reddit_client_id=None))
    assert "REDDIT_CLIENT_ID" in str(first.value)
    with pytest.raises(RedditCredentialsMissing) as second:
        RedditClient(reddit_config(config, reddit_client_secret=None))
    assert "REDDIT_CLIENT_SECRET" in str(second.value)
    with pytest.raises(RedditCredentialsMissing) as third:
        RedditClient(reddit_config(config, reddit_user_agent=""))
    assert "REDDIT_USER_AGENT" in str(third.value)


def test_load_config_reads_reddit_values_with_defaults(tmp_path):
    config = load_config(
        {
            "KPOPWINS_OPERATOR_HOME": str(tmp_path),
            "REDDIT_CLIENT_ID": " id ",
            "REDDIT_CLIENT_SECRET": "secret",
            "REDDIT_USER_AGENT": "agent",
        }
    )
    assert config.reddit_client_id == "id"
    assert config.reddit_client_secret == "secret"
    assert config.reddit_user_agent == "agent"
    assert config.reddit_token_url == "https://www.reddit.com/api/v1/access_token"
    assert config.reddit_api_base_url == "https://oauth.reddit.com"
    assert config.default_reddit_audit_path.name == "reddit-audit.json"
    with pytest.raises(ConfigurationError, match="REDDIT_TOKEN_URL"):
        load_config(
            {
                "KPOPWINS_OPERATOR_HOME": str(tmp_path),
                "REDDIT_TOKEN_URL": "not-a-url",
            }
        )


def test_token_request_uses_client_credentials_and_bearer(config):
    session = Session(pages={"https://oauth.reddit.test/r/kpop/wiki/music-shows": ""})
    client = RedditClient(reddit_config(config), session=session)

    content = client.wiki_page("music-shows")

    assert content == ""
    url, options = session.posts[0]
    assert url == "https://reddit.example/api/v1/access_token"
    assert options["data"] == {"grant_type": "client_credentials"}
    assert options["auth"] == ("client-id", "client-secret")
    assert options["timeout"] == (5, 30)
    get_url, get_options = session.gets[0]
    assert get_url == "https://oauth.reddit.test/r/kpop/wiki/music-shows"
    assert get_options["headers"]["Authorization"] == "Bearer token-1"
    assert get_options["headers"]["User-Agent"] == "KpopWinsOperator/0.1 (audit)"
    assert get_options["timeout"] == (5, 30)


def test_token_is_reused_until_expiry_then_renewed(config):
    pages = {
        "https://oauth.reddit.test/r/kpop/wiki/music-shows": "",
        "https://oauth.reddit.test/r/kpop/wiki/music-shows/inkigayo": "",
    }
    session = Session(pages=pages)
    start = datetime(2026, 1, 1, 12, tzinfo=UTC)
    clock = [start]
    client = RedditClient(
        reddit_config(config), session=session, clock=lambda: clock[0]
    )

    client.wiki_page("music-shows")
    client.wiki_page("music-shows/inkigayo")
    assert len(session.posts) == 1

    clock[0] = datetime(2026, 1, 1, 12, 30, tzinfo=UTC)
    client.wiki_page("music-shows/inkigayo")
    assert len(session.posts) == 1

    clock[0] = datetime(2026, 1, 1, 12, 56, tzinfo=UTC)
    client.wiki_page("music-shows/inkigayo")
    assert len(session.posts) == 2


def test_transient_failures_retry_with_retry_after(config):
    sleeps = []
    session = Session(
        post_responses=[Response({}, 429, {"Retry-After": "3"})],
        get_responses=[
            Response({}, 503),
            Response({"message": "Not Found"}, 404),
        ],
    )
    client = RedditClient(reddit_config(config), session=session, sleep=sleeps.append)

    with pytest.raises(RedditError, match="404"):
        client.wiki_page("music-shows")

    assert sleeps == [3, 1]
    assert len(session.posts) == 2
    assert len(session.gets) == 2


def test_timeout_and_malformed_responses_raise_clean_errors(config):
    class BrokenSession(Session):
        def post(self, url, **kwargs):
            self.posts.append((url, kwargs))
            raise requests.ConnectionError("boom")

    sleeps = []
    client = RedditClient(
        reddit_config(config),
        session=BrokenSession(),
        sleep=sleeps.append,
    )
    with pytest.raises(RedditError, match="token request failed") as error:
        client.wiki_page("music-shows")
    assert sleeps == [1, 2, 4]
    assert "boom" not in str(error.value)

    client = RedditClient(
        reddit_config(config),
        session=Session(post_responses=[Response(ValueError("bad json"), 200)]),
    )
    with pytest.raises(RedditError, match="not valid JSON"):
        client.wiki_page("music-shows")

    client = RedditClient(
        reddit_config(config),
        session=Session(post_responses=[Response({"nope": 1})]),
    )
    with pytest.raises(RedditError, match="incomplete"):
        client.wiki_page("music-shows")

    client = RedditClient(
        reddit_config(config),
        session=Session(
            pages={
                "https://oauth.reddit.test/r/kpop/wiki/music-shows": {
                    "unexpected": True
                }
            }
        ),
    )
    with pytest.raises(RedditError, match="no content"):
        client.wiki_page("music-shows")


def test_error_messages_never_contain_credentials(config):
    class ExplodingSession(Session):
        def post(self, url, **kwargs):
            self.posts.append((url, kwargs))
            raise requests.ConnectionError("client-secret leaked?")

    client = RedditClient(
        reddit_config(config), session=ExplodingSession(), sleep=lambda _seconds: None
    )
    with pytest.raises(RedditError) as error:
        client.wiki_page("music-shows")
    assert "client-secret" not in str(error.value)
    assert "token-1" not in str(error.value)
