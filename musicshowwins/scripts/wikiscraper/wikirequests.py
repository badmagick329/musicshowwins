import json
import logging
import time
from datetime import datetime
from pathlib import Path

import requests

from main.models import URLApprovalStatus
from scripts.wikiscraper.consts import CACHE_DIR, WIKI_AGENT


class WikiRequests:
    RESP_FILE = CACHE_DIR / "responses.json"
    DELAY = 0.2
    headers = {
        "User-Agent": WIKI_AGENT,
    }

    def __init__(self):
        log = logging.getLogger(__name__)
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        )
        self.logger = log
        self.last_fetch = datetime.fromtimestamp(0)
        self.saved_responses = self._load(self.RESP_FILE)

    def _load(self, file: Path) -> dict:
        CACHE_DIR.mkdir(exist_ok=True)
        if file.exists():
            with open(file, "r", encoding="utf-8") as f:
                return json.load(f)
        return dict()

    def _save(self, data: dict, file: Path) -> None:
        with open(file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    def get(self, url: str) -> str | Exception | None:
        """
        Wrapper around requests.get that caches results and delays
        requests if necessary
        """
        if url in self.saved_responses:
            self.logger.info(f"Using saved data for {url}")
            return self.saved_responses[url]
        if not self.url_is_approved(url):
            return None
        try:
            time_since = datetime.now() - self.last_fetch
            if time_since.total_seconds() < self.DELAY:
                time.sleep(self.DELAY - time_since.total_seconds())
            response = requests.get(
                url, headers=self.headers, allow_redirects=False
            )
            self.last_fetch = datetime.now()
            if response.status_code != 200:
                return ValueError(
                    f"Error {response.status_code} while fetching {url}"
                )
            self.logger.info(f"Fetched {url}")
            if f"({datetime.today().year})" not in url:
                self.saved_responses[url] = response.text
                self._save(self.saved_responses, self.RESP_FILE)
            return response.text
        except Exception as e:
            self.logger.error(f"Error while fetching {url}: {e}")
            return e

    def url_is_approved(self, url: str) -> bool:
        """
        Check if a url is in the approved list of urls. This is needed for when
        the year changes and the new urls aren't up yet. The new urls can point
        to old pages which can corrupt the db
        """
        saved_url, _ = URLApprovalStatus.objects.get_or_create(url=url)
        return saved_url.approved
