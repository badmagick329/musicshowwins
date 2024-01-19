import os
import sys
from pathlib import Path

DJANGO_DIR = Path(__file__).resolve().parent.parent.parent
if str(DJANGO_DIR) not in sys.path:
    sys.path.append(str(DJANGO_DIR))

os.environ["DJANGO_SETTINGS_MODULE"] = "musicshowwins.settings"
import django

django.setup()
