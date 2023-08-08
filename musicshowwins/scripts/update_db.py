import logging
import os
import sys
from pathlib import Path

DJANGO_DIR = Path(__file__).resolve().parent.parent
if str(DJANGO_DIR) not in sys.path:
    sys.path.append(str(DJANGO_DIR))
from wikiscraper import WikiScraper

os.environ["DJANGO_SETTINGS_MODULE"] = "musicshowwins.settings"
import django
from django.core.exceptions import ValidationError

django.setup()
from main.models import Artist, MusicShow, Song, Win


def main():
    s = WikiScraper(logging.INFO)
    data = s.all_wins()
    for i, d in enumerate(data):
        music_show, _ = MusicShow.objects.get_or_create(name=d["Show"])
        artist = Artist.objects.filter(name__iexact=d["Artist"])
        if artist:
            artist = artist[0]
        else:
            artist = Artist.objects.create(name=d["Artist"])
        song = Song.objects.filter(name__iexact=d["Song"], artist=artist)
        if song:
            song = song[0]
        else:
            song = Song.objects.create(name=d["Song"], artist=artist)
        try:
            win, _ = Win.objects.get_or_create(
                music_show=music_show, song=song, date=d["Date"]
            )
        except ValidationError as e:
            logging.critical(e)
            logging.critical(f"{d['Show']}, {d['Artist']}, {d['Song']}, {d['Date']}")
            if i > 0:
                logging.critical(
                    f"Previous\n{data[i-1]['Show']}, {data[i-1]['Artist']}, {data[i-1]['Song']}, {data[i-1]['Date']}"
                )
            if i < len(data) - 1:
                next_ = data[i + 1 : i + 6]
                logging.critical("Next\n")
                for n in next_:
                    logging.critical(
                        f"{n['Show']}, {n['Artist']}, {n['Song']}, {n['Date']}"
                    )
            raise e
        print(f"{i+1}/{len(data)}", end="\r")


if __name__ == "__main__":
    main()
