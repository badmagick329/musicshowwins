import os
import sys
from pathlib import Path

DJANGO_DIR = Path(__file__).resolve().parent.parent
if str(DJANGO_DIR) not in sys.path:
    sys.path.append(str(DJANGO_DIR))

os.environ["DJANGO_SETTINGS_MODULE"] = "musicshowwins.settings"
import django

django.setup()
from main.models import Win


def main():
    year = input("Enter year: ")
    if not year.isdigit():
        print("Invalid year")
        return
    year = int(year)
    Win.objects.filter(year=year).delete()
    assert Win.objects.filter(year=year).count() == 0
    print(f"Deleted wins from {year}")


if __name__ == "__main__":
    main()
