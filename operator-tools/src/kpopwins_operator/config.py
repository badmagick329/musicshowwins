from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping
from urllib.parse import urlsplit

DEFAULT_API_BASE_URL = "http://127.0.0.1:8000/api/v1"
DEFAULT_YOUTUBE_API_BASE_URL = "https://www.googleapis.com/youtube/v3"
DEFAULT_YOUTUBE_MAX_API_CALLS_PER_RUN = 500
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


class ConfigurationError(ValueError):
    pass


@dataclass(frozen=True)
class Config:
    home: Path
    api_base_url: str
    youtube_api_key: str | None = None
    youtube_api_base_url: str = DEFAULT_YOUTUBE_API_BASE_URL
    youtube_max_api_calls_per_run: int = DEFAULT_YOUTUBE_MAX_API_CALLS_PER_RUN

    @property
    def database_path(self) -> Path:
        return self.home / "operator.sqlite3"

    @property
    def manifests_dir(self) -> Path:
        return self.home / "manifests"

    @property
    def default_manifest_path(self) -> Path:
        return self.manifests_dir / "win-references-v1.json"

    @property
    def channel_registry_path(self) -> Path:
        return REPOSITORY_ROOT / "operator-tools" / "official-youtube-channels.toml"


def _read_env_file(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    values: dict[str, str] = {}
    for line_number, raw_line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ConfigurationError(f"Invalid .env entry on line {line_number}.")
        name, value = line.split("=", 1)
        name = name.strip()
        if not name:
            raise ConfigurationError(f"Invalid .env entry on line {line_number}.")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        values[name] = value
    return values


def _http_url(value: str, variable: str) -> str:
    parsed = urlsplit(value)
    try:
        port = parsed.port
    except ValueError as exc:
        raise ConfigurationError(f"{variable} must be an HTTP API URL.") from exc
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or port is not None
        and not 1 <= port <= 65535
    ):
        raise ConfigurationError(f"{variable} must be an HTTP API URL.")
    return value.rstrip("/")


def load_config(environ: Mapping[str, str] | None = None) -> Config:
    process_values = dict(os.environ if environ is None else environ)
    configured_home = process_values.get("KPOPWINS_OPERATOR_HOME")
    home = (
        Path(configured_home).expanduser()
        if configured_home
        else REPOSITORY_ROOT / ".ignore" / "operator-tools"
    ).resolve()
    values = {**_read_env_file(home / ".env"), **process_values}
    api_base_url = _http_url(
        values.get("KPOPWINS_API_BASE_URL", DEFAULT_API_BASE_URL).strip(),
        "KPOPWINS_API_BASE_URL",
    )
    youtube_api_base_url = _http_url(
        values.get("YOUTUBE_API_BASE_URL", DEFAULT_YOUTUBE_API_BASE_URL).strip(),
        "YOUTUBE_API_BASE_URL",
    )
    try:
        youtube_max_calls = int(
            values.get(
                "YOUTUBE_MAX_API_CALLS_PER_RUN",
                str(DEFAULT_YOUTUBE_MAX_API_CALLS_PER_RUN),
            )
        )
    except ValueError as exc:
        raise ConfigurationError(
            "YOUTUBE_MAX_API_CALLS_PER_RUN must be a positive integer."
        ) from exc
    if youtube_max_calls < 1:
        raise ConfigurationError(
            "YOUTUBE_MAX_API_CALLS_PER_RUN must be a positive integer."
        )
    youtube_api_key = values.get("YOUTUBE_API_KEY", "").strip() or None
    return Config(
        home=home,
        api_base_url=api_base_url,
        youtube_api_key=youtube_api_key,
        youtube_api_base_url=youtube_api_base_url,
        youtube_max_api_calls_per_run=youtube_max_calls,
    )
