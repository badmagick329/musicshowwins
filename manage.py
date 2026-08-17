#!/usr/bin/env python
"""Run Django management commands from the repository root."""

import os
import sys
from pathlib import Path

DJANGO_PROJECT_DIR = Path(__file__).resolve().parent / "musicshowwins"
if str(DJANGO_PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(DJANGO_PROJECT_DIR))


def main() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "musicshowwins.settings")
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
