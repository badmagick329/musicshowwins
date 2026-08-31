from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping
from urllib.parse import urlsplit

DEFAULT_API_BASE_URL = "http://127.0.0.1:8000/api/v1"
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


class ConfigurationError(ValueError):
    pass


@dataclass(frozen=True)
class Config:
    home: Path
    api_base_url: str

    @property
    def database_path(self) -> Path:
        return self.home / "operator.sqlite3"

    @property
    def manifests_dir(self) -> Path:
        return self.home / "manifests"

    @property
    def default_manifest_path(self) -> Path:
        return self.manifests_dir / "win-references-v1.json"


def load_config(environ: Mapping[str, str] | None = None) -> Config:
    values = os.environ if environ is None else environ
    configured_home = values.get("KPOPWINS_OPERATOR_HOME")
    home = (
        Path(configured_home).expanduser()
        if configured_home
        else REPOSITORY_ROOT / ".ignore" / "operator-tools"
    ).resolve()
    api_base_url = values.get("KPOPWINS_API_BASE_URL", DEFAULT_API_BASE_URL).strip()
    parsed = urlsplit(api_base_url)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise ConfigurationError("KPOPWINS_API_BASE_URL must be an HTTP API URL.")
    return Config(home=home, api_base_url=api_base_url.rstrip("/"))
