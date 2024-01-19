from pathlib import Path

from django.conf import settings

WIKI_AGENT = settings.WIKI_AGENT
CACHE_DIR = Path(__file__).resolve().parent.parent / "cached"
CSV_DIR = Path(__file__).resolve().parent.parent / "data"
