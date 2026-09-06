#!/bin/sh
set -eu

if [ "${1:-}" = "gunicorn" ]; then
    python manage.py migrate --noinput
    python manage.py import_win_moments \
        musicshowwins/main/data/artist_moments_pilot.json \
        --publish
fi

exec "$@"
