import logging
import os
import sys
from pathlib import Path

from django.core.exceptions import ValidationError
from wikiscraper.wikiscraper import WikiScraper

from main.models import Artist, ArtistFix, MusicShow, Song, Win

# DJANGO_DIR = Path(__file__).resolve().parent.parent
# if str(DJANGO_DIR) not in sys.path:
#     sys.path.append(str(DJANGO_DIR))
#
# os.environ["DJANGO_SETTINGS_MODULE"] = "musicshowwins.settings"
# import django
#
# django.setup()


LOG_LEVEL = logging.INFO

log = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setFormatter(
    logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
)
log.addHandler(handler)
log.setLevel(LOG_LEVEL)


def enter_data():
    s = WikiScraper(LOG_LEVEL)
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
            error_dump(e, d, data, i)
        print(f"{i+1}/{len(data)}", end="\r")


def error_dump(e: ValidationError, d: dict, data: list, i: int):
    log.critical(e)
    log.critical(f"{d['Show']}, {d['Artist']}, {d['Song']}, {d['Date']}")
    if i > 0:
        log.critical(
            f"Previous\n{data[i-1]['Show']}, {data[i-1]['Artist']}, "
            f"{data[i-1]['Song']}, {data[i-1]['Date']}"
        )
    if i < len(data) - 1:
        next_ = data[i + 1 : i + 6]
        log.critical("Next\n")
        for n in next_:
            log.critical(
                f"{n['Show']}, {n['Artist']}, {n['Song']}, {n['Date']}"
            )
    raise e


def apply_fixes():
    log.info("Applying fixes")
    for a in ArtistFix.objects.all():
        log.debug(f"Searching for {a.old}")
        artists = Artist.objects.filter(name__iexact=a.old)
        if not artists:
            continue
        log.debug(f"Found {len(artists)}")
        to_remove = list()
        for artist in artists:
            saved_artist = Artist.objects.filter(name__iexact=a.new)
            if not saved_artist:
                log.debug(f"Changing {artist.name} to {a.new}")
                artist.name = a.new
                artist.save()
                continue
            saved_artist = saved_artist[0]
            log.debug(
                f"Artist exists: {saved_artist.name}. "
                f"Taking songs from {artist.name} and removing {artist.name}"
            )
            saved_artist.take_songs_from(artist)
            to_remove.append(artist)
        for artist in to_remove:
            artist.delete()
    # TODO:
    # Implement SongFix


def main():
    enter_data()
    apply_fixes()


if __name__ == "__main__":
    main()
