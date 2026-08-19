from django.db import migrations
from django.utils import timezone


MBC_EVIDENCE = (
    "Music Core rankings were abolished in November 2015 and did not return "
    "until April 22, 2017; the aggregate-only 2016 rows are therefore not "
    "dated wins. Official MBC evidence: "
    "https://enews.imbc.com/News/RetrieveNewsInfo/162861 and "
    "https://enews.imbc.com/M/Detail/204086"
)


def _key(value):
    return " ".join((value or "").split()).casefold()


def _set_issue(issue, resolution, notes, now):
    issue.resolution = resolution
    issue.notes = notes
    issue.resolved_at = issue.resolved_at or now
    issue.save(update_fields=("resolution", "notes", "resolved_at"))


def _merge_songs(Song, Win, artist_name, source_titles, canonical_title):
    first_song = Song.objects.filter(artist__identity_key=_key(artist_name)).first()
    if first_song is None:
        return
    artist = first_song.artist
    songs = list(
        Song.objects.filter(artist=artist, title__in=source_titles).order_by("pk")
    )
    if not songs:
        return
    target = next(
        (song for song in songs if _key(song.title) == _key(canonical_title)),
        songs[0],
    )
    for source in songs:
        if source.pk == target.pk:
            continue
        for win in list(Win.objects.filter(song=source)):
            duplicate = (
                Win.objects.filter(show_id=win.show_id, date=win.date)
                .exclude(pk=win.pk)
                .first()
            )
            if duplicate is None:
                win.song_id = target.pk
                win.save(update_fields=("song",))
            else:
                win.delete()
        source.delete()
    target.title = canonical_title
    target.normalized_title = _key(canonical_title)
    target.save(update_fields=("title", "normalized_title"))


def resolve_historical_issues(apps, schema_editor):
    Artist = apps.get_model("main", "Artist")
    ImportIssue = apps.get_model("main", "ImportIssue")
    Song = apps.get_model("main", "Song")
    Win = apps.get_model("main", "Win")
    now = timezone.now()

    for issue in ImportIssue.objects.filter(issue_type="legacy_undated"):
        _set_issue(issue, "rejected", MBC_EVIDENCE, now)

    discrepancy_decisions = {
        ("blackpink", "ice cream"): (
            "rejected",
            "Rejected the BLACKPINK-only candidate; the public collaboration "
            "record is retained. Official evidence: "
            "https://ygfamily.com/en/artists/blackpink/discography/246",
        ),
        ("bibi", "bam yang gang"): (
            "rejected",
            "Rejected the Bibi candidate; CRAVITY / Love or Die is retained. "
            "Official evidence: https://www.youtube.com/watch?v=i9LtdEcMTLk",
        ),
        ("jennie & dominic fike", "love hangover"): (
            "rejected",
            "Rejected the candidate; IVE / Attitude is retained. Official evidence: "
            "https://mnetjp.com/news/detail/20250218151917/",
        ),
        ("xlov", "bizness"): (
            "rejected",
            "Rejected the candidate; Kang Daniel / Episode is retained. Official "
            "evidence: https://entertain.daum.net/tv/242903/video/456122599",
        ),
        ("zico", "spot! (feat. jennie)"): (
            "accepted",
            "Accepted canonical title SPOT! (feat. JENNIE). Official evidence: "
            "https://www.youtube.com/watch?v=xfqBQ2XhBCg",
        ),
        ("lee young-ji", "small girl (feat. doh kyung-soo)"): (
            "accepted",
            "Accepted canonical title Small girl (feat. D.O.). Official evidence: "
            "https://www.youtube.com/watch?v=11iZcYbq_is",
        ),
        ("jimin", "smeraldo garden marching band (feat. loco)"): (
            "accepted",
            "Accepted canonical title Smeraldo Garden Marching Band (feat. Loco). "
            "Official evidence: https://bts.ibighit.com/jpn/discography/jimin/detail/muse/",
        ),
    }
    for issue in ImportIssue.objects.filter(issue_type="legacy_discrepancy"):
        candidate = issue.candidate or {}
        decision = discrepancy_decisions.get(
            (_key(candidate.get("artist")), _key(candidate.get("song")))
        )
        if decision:
            _set_issue(issue, *decision, now)

    collaboration = Artist.objects.filter(
        identity_key=_key("Blackpink and Selena Gomez")
    ).first()
    if collaboration:
        canonical_collaboration = Artist.objects.filter(
            identity_key=_key("BLACKPINK and Selena Gomez")
        ).first()
        if canonical_collaboration and canonical_collaboration.pk != collaboration.pk:
            for song in list(Song.objects.filter(artist=collaboration)):
                duplicate = Song.objects.filter(
                    artist=canonical_collaboration,
                    normalized_title=song.normalized_title,
                ).first()
                if duplicate:
                    for win in list(Win.objects.filter(song=song)):
                        same_slot = Win.objects.filter(
                            show_id=win.show_id, date=win.date
                        ).exclude(pk=win.pk).first()
                        if same_slot:
                            win.delete()
                        else:
                            win.song_id = duplicate.pk
                            win.save(update_fields=("song",))
                    song.delete()
                else:
                    song.artist_id = canonical_collaboration.pk
                    song.save(update_fields=("artist",))
            collaboration.delete()
        else:
            collaboration.name = "BLACKPINK and Selena Gomez"
            collaboration.identity_key = _key(collaboration.name)
            collaboration.save(update_fields=("name", "identity_key"))

    _merge_songs(
        Song,
        Win,
        "Zico",
        ("Spot!", "Spot! (feat. Jennie)"),
        "SPOT! (feat. JENNIE)",
    )
    _merge_songs(
        Song,
        Win,
        "Lee Young-ji",
        ("Small Girl", "Small Girl (feat. Doh Kyung-soo)"),
        "Small girl (feat. D.O.)",
    )
    _merge_songs(
        Song,
        Win,
        "Jimin",
        ("Smeraldo Garden Marching Band", "Smeraldo Garden Marching Band (feat. Loco)"),
        "Smeraldo Garden Marching Band (feat. Loco)",
    )


class Migration(migrations.Migration):
    dependencies = [("main", "0002_sourceapproval")]
    operations = [migrations.RunPython(resolve_historical_issues, migrations.RunPython.noop)]
