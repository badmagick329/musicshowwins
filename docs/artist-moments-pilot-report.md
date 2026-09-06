# Artist moments pilot matching and review report

Catalogue checked: the active local development database on 2026-09-06. Seed content uses portable show/date/artist/song identities; the IDs below are environment-specific review aids.

| Artist | Event | Resolved IDs | Result |
|---|---|---|---|
| Cortis | M Countdown, 2026-04-30, RedRed | win 2999, artist 295, song 907 | Matched |
| Aespa | Inkigayo, 2021-01-17, Black Mamba | win 706, artist 90, song 339 | Matched |
| BTS | The Show, 2015-05-05, I Need U | win 1294, artist 48, song 365 | Matched |
| Ive | Show Champion, 2021-12-08, Eleven | win 1908, artist 91, song 192 | Matched |
| Red Velvet | Music Bank, 2015-03-27, Ice Cream Cake | win 2035, artist 35, song 41 | Matched |
| T-ara | The Show, 2017-06-20, What's My Name? | win 1381, artist 189, song 492 | Matched |

From the repository root, validate without writes:

`python manage.py import_win_moments musicshowwins/main/data/artist_moments_pilot.json --dry-run`

Add `--publish` for the explicit publication step. Use repeated `--artist NAME` options to select a subset.

## Checks

- Backend: 156 tests passed; Ruff and migration drift checks passed.
- Frontend: typecheck, ESLint, 130 tests and production build passed.
- Import dry run against the local catalogue: six entries resolved, six creates predicted.

## Browser review

- Desktop, 1280×720: the artist-page action reached `#win-2999`; the matching 30 April 2026 row and its existing video control were visible.
- Mobile, 390×844: the responsive action reached `#win-mobile-2999`; the matching record and its video control were visible.
- Mobile song page: heading order was Summary, Wins by show, Notable moments, Win history.
- Article links render publisher and article title, so same-publisher sources remain distinguishable.

Local review pages: `http://localhost:3000/artists/295` and `http://localhost:3000/songs/907`.
