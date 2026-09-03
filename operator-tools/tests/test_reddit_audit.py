from __future__ import annotations

import io
import json
import sqlite3

import pytest

from kpopwins_operator.cli import main
from kpopwins_operator.config import Config, load_config
from kpopwins_operator.database import initialize_database, open_database
from kpopwins_operator.reddit import (
    REDDIT_SHOW_ARCHIVES,
    RedditError,
    _resolve_archive_path,
    archive_link_kind,
    episode_date,
    extract_section_links,
    extract_wiki_links,
    extract_winner_section,
    is_na_winner,
    normalize_wiki_target,
    parse_video_link,
    run_reddit_audit,
)
from tests.test_reddit_client import Session, reddit_config

MAIN_INDEX = """**Music show archives**

* [Inkigayo](/r/kpop/wiki/music-shows/inkigayo)
* [M Countdown](https://www.reddit.com/r/kpop/wiki/music-shows/m-countdown/)
* [Music Bank](https://old.reddit.com/r/kpop/wiki/music-shows/music-bank)
* [Music Core](/r/kpop/wiki/music-shows/show-music-core)
* [Show Champion](/r/kpop/wiki/music-shows/show-champion)
* [The Show](/r/kpop/wiki/music-shows/the-show)
* [Weekly thread](https://www.reddit.com/r/kpop/comments/abc123/weekly/)
"""

INKIGAYO_ARCHIVE = """# Inkigayo episodes

* [June 23](/r/kpop/wiki/music-shows/inkigayo/20240623)
* [June 30](https://www.reddit.com/r/kpop/wiki/music-shows/inkigayo/20240630/)
* [June round-up](/r/kpop/wiki/music-shows/inkigayo/2024)
* [Old thread](https://www.reddit.com/r/kpop/comments/xyz789/thread/)
"""

INKIGAYO_JUNE = """# June 2024

* [June 16](/r/kpop/wiki/music-shows/inkigayo/20240616)
"""

INKIGAYO_20240616 = """### 2024-06-16

## WINNER

### N/A
"""

INKIGAYO_20240623 = """### 2024-06-23

## WINNER

* [Win](https://www.youtube.com/watch?v=abc123XYZ_1&t=30s)
* [Mirror](https://youtu.be/abc123XYZ_1)
* [Naver](https://tv.naver.com/v/1234567)
* [Tweet](https://twitter.com/kpop/status/123)
* [Broken](www.youtube.com/watch?v=broken)

## PERFORMANCES

* [Stage](https://www.youtube.com/watch?v=notWinner99)
"""

INKIGAYO_20240630 = """### 2024-06-30

## WINNER

Congratulations to tonight's winner!
"""

MCOUNTDOWN_ARCHIVE = """# M Countdown episodes

* [June 27](/r/kpop/wiki/music-shows/m-countdown/20240627)
* [June 20](/r/kpop/wiki/music-shows/m-countdown/20240620)
"""

MCOUNTDOWN_20240620 = """## WINNER

* [Gone](https://www.youtube.com/watch?v=goneVid99)
"""

MCOUNTDOWN_20240627 = """## WINNER

* [Stage cam](https://www.youtube.com/shorts/officialVid1)
"""

MUSICBANK_ARCHIVE = """# Music Bank episodes

* [July 4](/r/kpop/wiki/music-shows/music-bank/20240704)
"""

MUSICBANK_20240704 = """# Music Bank episode

Notes without a winner heading.
"""

MUSICCORE_ARCHIVE = """# Show! Music Core episodes

* [August 3](/r/kpop/wiki/music-shows/show-music-core/20240803)
* [August 10](/r/kpop/wiki/music-shows/show-music-core/20240810)
"""

MUSICCORE_20240803 = """## WINNER

* [One](https://www.youtube.com/watch?v=approvedAA11)
* [Two](https://youtu.be/pendingBB22)
"""

MUSICCORE_20240810 = """## WINNER

* [Gone away](https://www.youtube.com/watch?v=rejectedCC33)
"""

SHOWCHAMPION_ARCHIVE = """# Show Champion episodes

* [July 10](/r/kpop/wiki/music-shows/show-champion/20240710)
* [July 17](/r/kpop/wiki/music-shows/show-champion/20240717)
* [July 24](/r/kpop/wiki/music-shows/show-champion/20240724)
* [20150218](/r/kpop/wiki/music-shows/show-champion/2015021)
* [Broken date](/r/kpop/wiki/music-shows/show-champion/20151332)
"""

SHOWCHAMPION_20240710 = """## WINNER

* [Unverified](https://www.youtube.com/watch?v=unverifiedVid55)
"""

SHOWCHAMPION_20240724 = """## WINNER

The winner was announced during the broadcast.
"""

THESHOW_ARCHIVE = """# The Show episodes

* [June 11](/r/kpop/wiki/music-shows/the-show/20240611)
"""

THESHOW_20240611 = """## WINNER

### [WINNER - REALLY REALLY](https://twitter.com/winner/status/1) + [Encore Fancam](https://www.youtube.com/watch?v=nestedVid1)

----

## ADDITIONAL

* [Extra stage](https://www.youtube.com/watch?v=additionalVid3)
"""

ARCHIVE_PAGES = {
    "music-shows/inkigayo": INKIGAYO_ARCHIVE,
    "music-shows/m-countdown": MCOUNTDOWN_ARCHIVE,
    "music-shows/music-bank": MUSICBANK_ARCHIVE,
    "music-shows/show-music-core": MUSICCORE_ARCHIVE,
    "music-shows/show-champion": SHOWCHAMPION_ARCHIVE,
    "music-shows/the-show": THESHOW_ARCHIVE,
}

EPISODE_PAGES = {
    "music-shows/inkigayo/2024": INKIGAYO_JUNE,
    "music-shows/inkigayo/20240616": INKIGAYO_20240616,
    "music-shows/inkigayo/20240623": INKIGAYO_20240623,
    "music-shows/inkigayo/20240630": INKIGAYO_20240630,
    "music-shows/m-countdown/20240620": MCOUNTDOWN_20240620,
    "music-shows/m-countdown/20240627": MCOUNTDOWN_20240627,
    "music-shows/music-bank/20240704": MUSICBANK_20240704,
    "music-shows/show-music-core/20240803": MUSICCORE_20240803,
    "music-shows/show-music-core/20240810": MUSICCORE_20240810,
    "music-shows/show-champion/20240710": SHOWCHAMPION_20240710,
    "music-shows/show-champion/20240724": SHOWCHAMPION_20240724,
    "music-shows/the-show/20240611": THESHOW_20240611,
}


def audit_session():
    pages = {
        "https://oauth.reddit.test/r/kpop/wiki/music-shows": MAIN_INDEX,
        **{
            f"https://oauth.reddit.test/r/kpop/wiki/{path}": content
            for path, content in {**ARCHIVE_PAGES, **EPISODE_PAGES}.items()
        },
    }
    return Session(pages=pages)


def seed_wins(connection):
    rows = [
        ("inkigayo", "2024-06-17", "Gap Artist", "Gap Song"),
        ("inkigayo", "2024-06-23", "Artist Alpha", "Song One"),
        ("inkigayo", "2024-06-30", "Artist Beta", "Song Two"),
        ("m-countdown", "2024-06-20", "Artist Gamma", "Song Three"),
        ("m-countdown", "2024-06-27", "Riize", "Boom Boom Bass"),
        ("music-bank", "2024-07-04", "Artist Delta", "Song Four"),
        ("music-core", "2024-08-03", "Artist Epsilon", "Song Five"),
        ("music-core", "2024-08-10", "Artist Zeta", "Song Six"),
        ("show-champion", "2024-07-10", "Artist Eta", "Song Seven"),
        ("show-champion", "2024-07-24", "Artist Iota", "Song Nine"),
        ("the-show", "2024-06-11", "Artist Theta", "Song Eight"),
    ]
    for index, (show, win_date, artist, song) in enumerate(rows, start=1):
        connection.execute(
            """
            INSERT INTO wins (
                show_slug, win_date, api_win_id, artist_name, song_title,
                is_current, last_seen_at
            ) VALUES (?, ?, ?, ?, ?, 1, '2026-08-31T12:00:00Z')
            """,
            (show, win_date, index, artist, song),
        )
    connection.execute(
        """
        INSERT INTO youtube_channels (
            show_slug, configured_handle, channel_id, channel_title,
            uploads_playlist_id, verified_at, is_active
        ) VALUES ('m-countdown', '@MnetKPOP', 'UCOfficialMnet', 'Mnet K-POP',
                  'UUOfficialMnet', '2026-08-31T00:00:00Z', 1)
        """
    )
    connection.execute(
        """
        INSERT INTO youtube_channels (
            show_slug, configured_handle, channel_id, channel_title,
            uploads_playlist_id, verified_at, is_active
        ) VALUES ('show-champion', '@OtherShow', 'UCSomeOther', 'Other Channel',
                  'UUOther', '2026-08-31T00:00:00Z', 0)
        """
    )
    for video_id, channel, status, title in (
        ("officialVid1", "UCOfficialMnet", "active", "Official Stage"),
        ("goneVid99", "UCOfficialMnet", "unavailable", "Removed Stage"),
        ("unverifiedVid55", "UCSomeOther", "active", "Somebody's Upload"),
    ):
        connection.execute(
            """
            INSERT INTO youtube_videos (
                video_id, channel_id, title, published_at, first_seen_at,
                last_seen_at, availability_status
            ) VALUES (?, ?, ?, '2024-06-27T10:00:00Z',
                      '2026-08-31T00:00:00Z', '2026-08-31T00:00:00Z', ?)
            """,
            (video_id, channel, title, status),
        )
    candidates = [
        (
            "music-core",
            "2024-08-03",
            "approvedAA11",
            "https://www.youtube.com/watch?v=approvedAA11",
            "approved",
        ),
        ("music-core", "2024-08-03", "", "https://youtu.be/pendingBB22", "pending"),
        (
            "music-core",
            "2024-08-10",
            "rejectedCC33",
            "https://www.youtube.com/watch?v=rejectedCC33",
            "rejected",
        ),
    ]
    for show, win_date, external_id, url, review_status in candidates:
        connection.execute(
            """
            INSERT INTO reference_candidates (
                show_slug, win_date, reference_type, provider, external_id, url,
                title, publisher_name, publisher_external_id, is_official,
                status, metadata, review_status, created_at, updated_at
            ) VALUES (?, ?, 'video', 'youtube', ?, ?, 'Stored title',
                      'Stored publisher', 'UCStored', 1, 'active', '{}', ?,
                      '2026-08-31T00:00:00Z', '2026-08-31T00:00:00Z')
            """,
            (show, win_date, external_id, url, review_status),
        )
    connection.commit()


def snapshot_database(connection: sqlite3.Connection) -> dict[str, list]:
    tables = [
        row["name"]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%'"
        )
    ]
    return {
        table: list(connection.execute(f"SELECT * FROM {table}")) for table in tables
    }


def test_wiki_link_normalization_and_deduplication():
    markdown = (
        "[A](/r/kpop/wiki/music-shows/inkigayo)\n"
        "[B](https://www.reddit.com/r/kpop/wiki/music-shows/inkigayo/)\n"
        "[C](https://old.reddit.com/r/kpop/wiki/music-shows/m-countdown)\n"
        "[Thread](https://www.reddit.com/r/kpop/comments/abc/thread/)\n"
        "[Other site](https://example.com/r/kpop/wiki/music-shows/inkigayo)\n"
    )
    assert extract_wiki_links(markdown) == [
        "music-shows/inkigayo",
        "music-shows/m-countdown",
    ]
    assert normalize_wiki_target("/r/kpop/wiki/music-shows") == "music-shows"
    assert normalize_wiki_target("/r/kpop/wiki/") is None
    assert normalize_wiki_target("music-shows") is None


def test_episode_date_extraction():
    assert episode_date("music-shows/inkigayo/20240628") == "2024-06-28"
    assert episode_date("music-shows/inkigayo/2024") is None
    assert episode_date("music-shows/inkigayo/20241332") is None
    assert episode_date("music-shows/inkigayo/index") is None


def test_archive_link_kind_classification():
    assert archive_link_kind("music-shows/show-champion/20240710") == (
        "episode",
        "2024-07-10",
    )
    assert archive_link_kind("music-shows/show-champion/2024") == ("index", None)
    assert archive_link_kind("music-shows/show-champion/openconcert") == (
        "index",
        None,
    )
    assert archive_link_kind("music-shows/show-champion/2015021") == (
        "malformed",
        None,
    )
    assert archive_link_kind("music-shows/show-champion/20151332") == (
        "malformed",
        None,
    )
    assert archive_link_kind("music-shows/show-champion/12345") == ("malformed", None)
    assert archive_link_kind("music-shows/show-champion/201502181") == (
        "malformed",
        None,
    )


def test_winner_section_boundaries_and_na():
    found, text = extract_winner_section(INKIGAYO_20240623)
    assert found
    assert "abc123XYZ_1" in text
    assert "notWinner99" not in text
    assert extract_winner_section("# no heading here")[0] is False
    assert extract_winner_section("## Winner\n\nThe show was canceled.")[1] == (
        "The show was canceled."
    )
    assert is_na_winner("*N/A*")
    assert is_na_winner("n/a.")
    assert not is_na_winner("N/A performance")


def test_winner_section_keeps_nested_headings_until_parent_level():
    found, text = extract_winner_section(THESHOW_20240611)
    assert found
    assert "nestedVid1" in text
    assert "additionalVid3" not in text
    assert extract_section_links(text) == [
        "https://twitter.com/winner/status/1",
        "https://www.youtube.com/watch?v=nestedVid1",
    ]

    markdown = (
        "# Show\n\n"
        "## WINNER\n\n"
        "### [A](https://a.example/1)\n\n"
        "### N/A\n\n"
        "## ETC\n\n"
        "### [B](https://b.example/2)\n"
    )
    found, text = extract_winner_section(markdown)
    assert found
    assert "https://a.example/1" in text
    assert "### N/A" in text
    assert "b.example" not in text


def test_na_winner_recognizes_nested_no_winner_headings():
    assert is_na_winner("### N/A")
    assert is_na_winner("### No winner.")
    assert is_na_winner("###  no winner ")
    assert is_na_winner("### N/A.")
    assert is_na_winner("N/A")
    assert is_na_winner("*N/A*")
    assert is_na_winner("n/a.")
    assert not is_na_winner("### No winner announced yet!")
    assert not is_na_winner("### [WINNER - REALLY REALLY](https://x.example/a)")
    assert not is_na_winner("----")


def test_youtube_url_variants_and_canonicalization():
    variants = [
        "https://www.youtube.com/watch?v=abc123XYZ_1&t=30s",
        "https://youtu.be/abc123XYZ_1",
        "https://m.youtube.com/shorts/abc123XYZ_1",
        "https://music.youtube.com/watch?v=abc123XYZ_1",
    ]
    for variant in variants:
        parsed = parse_video_link(variant)
        assert parsed.provider == "youtube"
        assert parsed.external_id == "abc123XYZ_1"
        assert parsed.canonical_url == "https://www.youtube.com/watch?v=abc123XYZ_1"
    assert parse_video_link("https://www.youtube.com/watch?app=desktop") is None
    assert parse_video_link("https://www.youtube.com/shorts/") is None
    assert parse_video_link("https://youtu.be/") is None
    assert parse_video_link("www.youtube.com/watch?v=broken") is None
    naver = parse_video_link("https://tv.naver.com/v/1234567")
    assert (naver.provider, naver.external_id) == ("naver", "1234567")
    assert parse_video_link("https://naver.tv/7654321").external_id == "7654321"
    other = parse_video_link("https://twitter.com/kpop/status/123")
    assert other.provider == "other"


def test_section_link_extraction_includes_markdown_and_bare_urls():
    links = extract_section_links(
        "* [One](https://a.example/x)\n"
        "https://b.example/y\n"
        "<https://c.example/z>\n"
        "https://a.example/x,\n"
    )
    assert links == [
        "https://a.example/x",
        "https://b.example/y",
        "https://c.example/z",
    ]


def test_full_audit_classifies_links_and_writes_reports(connection, config):
    seed_wins(connection)
    session = audit_session()
    output = io.StringIO()

    outcome = run_reddit_audit(
        connection,
        reddit_config(config),
        show=None,
        max_pages=100,
        refresh_indexes=False,
        output_path=None,
        stdout=output,
        session=session,
        now="2026-09-01T12:00:00Z",
    )

    assert outcome.more_remaining is False
    assert outcome.collection_complete is True
    totals = outcome.totals
    assert totals["archive_pages_scanned"] == 8
    assert totals["episode_pages_discovered"] == 12
    assert totals["episode_pages_cached"] == 0
    assert totals["episode_pages_fetched"] == 11
    assert totals["episode_pages_not_found"] == 1
    assert totals["episode_pages_parsed"] == 11
    assert totals["malformed_episode_links"] == 2
    assert totals["exact_local_win_matches"] == 10
    assert totals["episodes_without_local_wins"] == 1
    assert totals["local_wins_without_episode_pages"] == 1
    assert totals["missing_winner_sections"] == 1
    assert totals["winner_na_sections"] == 1
    assert totals["winner_sections_without_links"] == 2
    assert totals["total_extracted_links"] == 12
    assert totals["existing_approved"] == 1
    assert totals["existing_pending"] == 1
    assert totals["existing_rejected"] == 1
    assert totals["new_official"] == 1
    assert totals["new_unverified"] == 3
    assert totals["known_unavailable"] == 1
    assert totals["naver_links"] == 1
    assert totals["unsupported_links"] == 3
    assert totals["malformed_links"] == 1
    assert output.getvalue().endswith("more-remaining=no\n")

    report = json.loads(outcome.report_path.read_text(encoding="utf-8"))
    assert report["collection_complete"] is True
    assert report["generated_at"] == "2026-09-01T12:00:00Z"
    assert report["source"]["entry_point"] == (
        "https://www.reddit.com/r/kpop/wiki/music-shows/"
    )
    inkigayo = next(
        archive for archive in report["archives"] if archive["show_slug"] == "inkigayo"
    )
    assert inkigayo["coverage_start"] == "2024-06-16"
    assert inkigayo["coverage_end"] == "2024-06-30"

    episode_0623 = next(
        episode for episode in report["episodes"] if episode["win_date"] == "2024-06-23"
    )
    assert episode_0623["outcome"] == "matched"
    assert episode_0623["local_win"] == {
        "artist_name": "Artist Alpha",
        "song_title": "Song One",
    }
    links = {link["link_url"]: link for link in episode_0623["links"]}
    assert len(links) == 4
    youtube = links["https://www.youtube.com/watch?v=abc123XYZ_1&t=30s"]
    assert youtube["classification"] == "new_unverified"
    assert youtube["canonical_url"] == "https://www.youtube.com/watch?v=abc123XYZ_1"
    assert youtube["provider"] == "youtube"
    naver = links["https://tv.naver.com/v/1234567"]
    assert naver["classification"] == "unsupported_link"
    assert naver["provider"] == "naver"
    assert (
        links["https://twitter.com/kpop/status/123"]["classification"]
        == "unsupported_link"
    )
    assert links["www.youtube.com/watch?v=broken"]["classification"] == "malformed_link"

    official = next(
        link
        for episode in report["episodes"]
        if episode["win_date"] == "2024-06-27"
        for link in episode["links"]
    )
    assert official["classification"] == "new_official"
    assert official["video_title"] == "Official Stage"
    assert official["publisher_name"] == "Mnet K-POP"
    assert official["publisher_external_id"] == "UCOfficialMnet"
    assert official["local_video_status"] == "active"

    unavailable = next(
        link
        for episode in report["episodes"]
        if episode["win_date"] == "2024-06-20"
        for link in episode["links"]
    )
    assert unavailable["classification"] == "known_unavailable"
    assert unavailable["local_video_status"] == "unavailable"

    unverified = next(
        link
        for episode in report["episodes"]
        if episode["win_date"] == "2024-07-10"
        for link in episode["links"]
    )
    assert unverified["classification"] == "new_unverified"
    assert unverified["video_title"] == "Somebody's Upload"
    assert unverified["publisher_name"] == ""

    core_0803 = next(
        episode for episode in report["episodes"] if episode["win_date"] == "2024-08-03"
    )
    assert {
        link["external_id"]: link["classification"] for link in core_0803["links"]
    } == {"approvedAA11": "existing_approved", "pendingBB22": "existing_pending"}
    core_0810 = next(
        episode for episode in report["episodes"] if episode["win_date"] == "2024-08-10"
    )
    assert core_0810["links"][0]["classification"] == "existing_rejected"

    missing = next(
        episode for episode in report["episodes"] if episode["win_date"] == "2024-07-04"
    )
    assert missing["outcome"] == "missing_winner_section"
    assert missing["has_local_win"] is True

    assert (
        report["shows"]["inkigayo"]["counts"]["local_wins_without_episode_pages"] == 1
    )

    tsv = outcome.tsv_path.read_text(encoding="utf-8").splitlines()
    assert tsv[0].split("\t") == [
        "show_slug",
        "win_date",
        "artist_name",
        "song_title",
        "winner_text",
        "episode_url",
        "link_url",
        "provider",
        "external_id",
        "classification",
        "video_title",
        "publisher_name",
        "publisher_external_id",
        "existing_review_status",
    ]
    assert len(tsv) == 13
    assert not list(config.reports_dir.glob("*.tmp"))


def test_active_video_overrides_stale_unavailable_lookup_state(connection, config):
    seed_wins(connection)
    connection.execute(
        """
        INSERT INTO reddit_youtube_lookup_state (
            video_id, lookup_status, checked_at
        ) VALUES ('officialVid1', 'unavailable', '2026-08-30T12:00:00Z')
        """
    )
    connection.commit()

    outcome = run_reddit_audit(
        connection,
        reddit_config(config),
        show="m-countdown",
        max_pages=100,
        refresh_indexes=False,
        output_path=None,
        stdout=io.StringIO(),
        session=audit_session(),
        now="2026-09-01T12:00:00Z",
    )

    report = json.loads(outcome.report_path.read_text(encoding="utf-8"))
    active = next(
        link
        for episode in report["episodes"]
        if episode["win_date"] == "2024-06-27"
        for link in episode["links"]
    )
    assert active["classification"] == "new_official"
    assert active["local_video_status"] == "active"
    assert outcome.totals["known_unavailable"] == 1


def test_music_core_archive_resolves_through_live_index_path(connection, config):
    seed_wins(connection)
    assert REDDIT_SHOW_ARCHIVES["music-core"] == "music-shows/show-music-core"
    resolved = _resolve_archive_path(
        REDDIT_SHOW_ARCHIVES["music-core"], extract_wiki_links(MAIN_INDEX)
    )
    assert resolved == "music-shows/show-music-core"

    outcome = run_reddit_audit(
        connection,
        reddit_config(config),
        show="music-core",
        max_pages=100,
        refresh_indexes=False,
        output_path=None,
        stdout=io.StringIO(),
        session=audit_session(),
        now="2026-09-01T12:00:00Z",
    )
    assert outcome.totals["episode_pages_discovered"] == 2
    assert outcome.totals["exact_local_win_matches"] == 2

    report = json.loads(outcome.report_path.read_text(encoding="utf-8"))
    assert report["archives"][0]["archive_path"] == "music-shows/show-music-core"
    assert {episode["episode_path"] for episode in report["episodes"]} == {
        "music-shows/show-music-core/20240803",
        "music-shows/show-music-core/20240810",
    }
    core_0803 = next(
        episode for episode in report["episodes"] if episode["win_date"] == "2024-08-03"
    )
    assert {
        link["external_id"]: link["classification"] for link in core_0803["links"]
    } == {
        "approvedAA11": "existing_approved",
        "pendingBB22": "existing_pending",
    }
    cached_page = (
        config.reddit_dir / "pages" / "music-shows" / "show-music-core" / "20240803.md"
    )
    assert cached_page.is_file()


def test_nested_winner_links_are_parsed_and_later_sections_excluded(connection, config):
    seed_wins(connection)
    output = io.StringIO()
    outcome = run_reddit_audit(
        connection,
        reddit_config(config),
        show="the-show",
        max_pages=100,
        refresh_indexes=False,
        output_path=None,
        stdout=output,
        session=audit_session(),
        now="2026-09-01T12:00:00Z",
    )
    assert outcome.totals["episode_pages_discovered"] == 1
    assert outcome.totals["exact_local_win_matches"] == 1
    assert outcome.totals["total_extracted_links"] == 2
    assert outcome.totals["new_unverified"] == 1
    assert outcome.totals["unsupported_links"] == 1

    report = json.loads(outcome.report_path.read_text(encoding="utf-8"))
    episode = report["episodes"][0]
    assert episode["outcome"] == "matched"
    assert "nestedVid1" in episode["winner_text"]
    assert [link["link_url"] for link in episode["links"]] == [
        "https://twitter.com/winner/status/1",
        "https://www.youtube.com/watch?v=nestedVid1",
    ]
    assert episode["links"][1]["canonical_url"] == (
        "https://www.youtube.com/watch?v=nestedVid1"
    )
    assert episode["links"][1]["classification"] == "new_unverified"
    assert all("additionalVid3" not in link["link_url"] for link in episode["links"])


def test_episode_404_is_recorded_reported_and_run_completes(connection, config):
    seed_wins(connection)
    outcome = run_reddit_audit(
        connection,
        reddit_config(config),
        show="show-champion",
        max_pages=100,
        refresh_indexes=False,
        output_path=None,
        stdout=io.StringIO(),
        session=audit_session(),
        now="2026-09-01T12:00:00Z",
    )
    assert outcome.more_remaining is False
    assert outcome.collection_complete is True
    assert outcome.totals["episode_pages_discovered"] == 3
    assert outcome.totals["episode_pages_fetched"] == 2
    assert outcome.totals["episode_pages_not_found"] == 1
    assert outcome.totals["episode_pages_parsed"] == 2
    assert outcome.totals["exact_local_win_matches"] == 2
    assert outcome.totals["episode_pages_discovered"] == (
        outcome.totals["episode_pages_parsed"]
        + outcome.totals["episode_pages_not_found"]
    )

    report = json.loads(outcome.report_path.read_text(encoding="utf-8"))
    assert report["episode_pages_not_found"] == [
        {
            "show_slug": "show-champion",
            "win_date": "2024-07-17",
            "episode_path": "music-shows/show-champion/20240717",
            "episode_url": (
                "https://www.reddit.com/r/kpop/wiki/music-shows/show-champion/20240717"
            ),
        }
    ]
    assert report["shows"]["show-champion"]["counts"]["episode_pages_not_found"] == 1
    state = json.loads((config.reddit_dir / "state.json").read_text(encoding="utf-8"))
    assert state["missing_episode_pages"] == ["music-shows/show-champion/20240717"]


def test_repeat_run_skips_known_missing_page(connection, config):
    seed_wins(connection)
    run_reddit_audit(
        connection,
        reddit_config(config),
        show="show-champion",
        max_pages=100,
        refresh_indexes=False,
        output_path=None,
        stdout=io.StringIO(),
        session=audit_session(),
        now="2026-09-01T12:00:00Z",
    )
    second_session = audit_session()
    second = run_reddit_audit(
        connection,
        reddit_config(config),
        show="show-champion",
        max_pages=100,
        refresh_indexes=False,
        output_path=None,
        stdout=io.StringIO(),
        session=second_session,
        now="2026-09-01T13:00:00Z",
    )
    assert second.more_remaining is False
    assert second.totals["episode_pages_not_found"] == 1
    assert second.totals["episode_pages_cached"] == 2
    assert second.totals["episode_pages_parsed"] == 2
    assert all("20240717" not in url for url, _ in second_session.gets)
    assert second_session.gets == []

    report = json.loads(second.report_path.read_text(encoding="utf-8"))
    assert [
        (page["show_slug"], page["win_date"], page["episode_path"])
        for page in report["episode_pages_not_found"]
    ] == [("show-champion", "2024-07-17", "music-shows/show-champion/20240717")]
    assert report["shows"]["show-champion"]["counts"]["episode_pages_not_found"] == 1
    assert report["totals"]["episode_pages_discovered"] == (
        report["totals"]["episode_pages_parsed"]
        + report["totals"]["episode_pages_not_found"]
        + len(report["pending_episode_pages"])
    )


def test_refresh_indexes_retries_known_missing_page(connection, config):
    seed_wins(connection)
    run_reddit_audit(
        connection,
        reddit_config(config),
        show="show-champion",
        max_pages=100,
        refresh_indexes=False,
        output_path=None,
        stdout=io.StringIO(),
        session=audit_session(),
        now="2026-09-01T12:00:00Z",
    )
    refreshed_session = audit_session()
    refreshed = run_reddit_audit(
        connection,
        reddit_config(config),
        show="show-champion",
        max_pages=100,
        refresh_indexes=True,
        output_path=None,
        stdout=io.StringIO(),
        session=refreshed_session,
        now="2026-09-01T14:00:00Z",
    )
    assert any("20240717" in url for url, _ in refreshed_session.gets)
    assert refreshed.totals["episode_pages_not_found"] == 1
    assert refreshed.more_remaining is False
    state = json.loads((config.reddit_dir / "state.json").read_text(encoding="utf-8"))
    assert state["missing_episode_pages"] == ["music-shows/show-champion/20240717"]


def test_missing_page_consumes_page_budget_and_allows_completion(connection, config):
    seed_wins(connection)
    first = run_reddit_audit(
        connection,
        reddit_config(config),
        show="show-champion",
        max_pages=1,
        refresh_indexes=False,
        output_path=None,
        stdout=io.StringIO(),
        session=audit_session(),
        now="2026-09-01T12:00:00Z",
    )
    assert first.totals["episode_pages_fetched"] == 1
    assert first.totals["episode_pages_not_found"] == 0
    assert first.more_remaining is True
    assert first.collection_complete is False
    assert first.totals["episode_pages_discovered"] == (
        first.totals["episode_pages_parsed"]
        + first.totals["episode_pages_not_found"]
        + 2
    )

    second_session = audit_session()
    second = run_reddit_audit(
        connection,
        reddit_config(config),
        show="show-champion",
        max_pages=2,
        refresh_indexes=False,
        output_path=None,
        stdout=io.StringIO(),
        session=second_session,
        now="2026-09-01T13:00:00Z",
    )
    assert second.totals["episode_pages_not_found"] == 1
    assert second.totals["episode_pages_fetched"] == 1
    assert second.more_remaining is False
    assert second.collection_complete is True
    assert len(second_session.gets) == 2
    assert second.totals["episode_pages_discovered"] == (
        second.totals["episode_pages_parsed"] + second.totals["episode_pages_not_found"]
    )


def test_missing_archive_index_fails_with_path_and_status(connection, config):
    seed_wins(connection)
    with pytest.raises(RedditError, match=r"music-shows.*404"):
        run_reddit_audit(
            connection,
            reddit_config(config),
            show="show-champion",
            max_pages=100,
            refresh_indexes=False,
            output_path=None,
            stdout=io.StringIO(),
            session=Session(),
            now="2026-09-01T12:00:00Z",
        )
    partial = audit_session()
    del partial.pages["https://oauth.reddit.test/r/kpop/wiki/music-shows/show-champion"]
    with pytest.raises(RedditError, match=r"show-champion.*404"):
        run_reddit_audit(
            connection,
            reddit_config(config),
            show="show-champion",
            max_pages=100,
            refresh_indexes=False,
            output_path=None,
            stdout=io.StringIO(),
            session=partial,
            now="2026-09-01T12:00:00Z",
        )


def test_malformed_numeric_archive_links_are_recorded_not_requested(connection, config):
    seed_wins(connection)
    session = audit_session()
    outcome = run_reddit_audit(
        connection,
        reddit_config(config),
        show="show-champion",
        max_pages=100,
        refresh_indexes=False,
        output_path=None,
        stdout=io.StringIO(),
        session=session,
        now="2026-09-01T12:00:00Z",
    )
    assert outcome.more_remaining is False
    assert outcome.totals["malformed_episode_links"] == 2
    assert outcome.totals["episode_pages_discovered"] == 3
    assert outcome.totals["episode_pages_fetched"] == 2
    assert outcome.totals["episode_pages_not_found"] == 1
    assert all(
        "2015021" not in url and "20151332" not in url for url, _ in session.gets
    )
    assert all(len(url.rsplit("/", 1)[-1]) != 7 for url, _ in session.gets)

    report = json.loads(outcome.report_path.read_text(encoding="utf-8"))
    assert report["malformed_episode_links"] == [
        {
            "show_slug": "show-champion",
            "archive_path": "music-shows/show-champion",
            "target_path": "music-shows/show-champion/2015021",
        },
        {
            "show_slug": "show-champion",
            "archive_path": "music-shows/show-champion",
            "target_path": "music-shows/show-champion/20151332",
        },
    ]
    assert report["shows"]["show-champion"]["counts"]["malformed_episode_links"] == 2
    state = json.loads((config.reddit_dir / "state.json").read_text(encoding="utf-8"))
    assert "music-shows/show-champion/2015021" not in state.get(
        "missing_episode_pages", []
    )
    assert "music-shows/show-champion/20151332" not in state.get(
        "missing_episode_pages", []
    )


def test_cached_pages_are_reused_and_runs_resume(connection, config):
    seed_wins(connection)
    first = run_reddit_audit(
        connection,
        reddit_config(config),
        show=None,
        max_pages=2,
        refresh_indexes=False,
        output_path=None,
        stdout=io.StringIO(),
        session=audit_session(),
        now="2026-09-01T12:00:00Z",
    )
    assert first.more_remaining is True
    assert first.totals["episode_pages_fetched"] == 2
    assert first.totals["episode_pages_cached"] == 0
    assert first.collection_complete is False

    second_session = audit_session()
    second = run_reddit_audit(
        connection,
        reddit_config(config),
        show=None,
        max_pages=100,
        refresh_indexes=False,
        output_path=None,
        stdout=io.StringIO(),
        session=second_session,
        now="2026-09-01T13:00:00Z",
    )
    assert second.more_remaining is False
    assert second.totals["episode_pages_cached"] == 2
    assert second.totals["episode_pages_fetched"] == 9
    assert second.totals["episode_pages_not_found"] == 1
    episode_fetches = [
        url
        for url, _ in second_session.gets
        if len(url.rsplit("/", 1)[-1]) == 8 and url.rsplit("/", 1)[-1].isdigit()
    ]
    assert len(episode_fetches) == 10
    assert len(second_session.gets) == 10


def test_show_filter_limits_scope_and_output_override(connection, config, tmp_path):
    seed_wins(connection)
    session = audit_session()
    output_path = tmp_path / "custom-audit.json"
    outcome = run_reddit_audit(
        connection,
        reddit_config(config),
        show="m-countdown",
        max_pages=100,
        refresh_indexes=False,
        output_path=output_path,
        stdout=io.StringIO(),
        session=session,
        now="2026-09-01T12:00:00Z",
    )
    assert outcome.more_remaining is False
    assert outcome.totals["episode_pages_discovered"] == 2
    assert outcome.totals["exact_local_win_matches"] == 2
    assert all("inkigayo" not in url for url, _ in session.gets)
    assert outcome.report_path == output_path
    assert output_path.is_file()
    assert outcome.tsv_path == tmp_path / "custom-audit.tsv"
    assert outcome.tsv_path.is_file()


def test_refresh_indexes_refetch_archive_pages(connection, config):
    seed_wins(connection)
    run_reddit_audit(
        connection,
        reddit_config(config),
        show="the-show",
        max_pages=100,
        refresh_indexes=False,
        output_path=None,
        stdout=io.StringIO(),
        session=audit_session(),
        now="2026-09-01T12:00:00Z",
    )
    cached_session = audit_session()
    cached = run_reddit_audit(
        connection,
        reddit_config(config),
        show="the-show",
        max_pages=100,
        refresh_indexes=False,
        output_path=None,
        stdout=io.StringIO(),
        session=cached_session,
        now="2026-09-01T13:00:00Z",
    )
    assert cached.totals["archive_pages_scanned"] == 2
    assert cached_session.gets == []

    refreshed_session = audit_session()
    refreshed = run_reddit_audit(
        connection,
        reddit_config(config),
        show="the-show",
        max_pages=100,
        refresh_indexes=True,
        output_path=None,
        stdout=io.StringIO(),
        session=refreshed_session,
        now="2026-09-01T14:00:00Z",
    )
    assert refreshed.totals["archive_pages_scanned"] == 2
    assert len(refreshed_session.gets) == 2


def test_audit_never_modifies_application_tables(connection, config):
    seed_wins(connection)
    before = snapshot_database(connection)
    run_reddit_audit(
        connection,
        reddit_config(config),
        show=None,
        max_pages=100,
        refresh_indexes=False,
        output_path=None,
        stdout=io.StringIO(),
        session=audit_session(),
        now="2026-09-01T12:00:00Z",
    )
    assert snapshot_database(connection) == before


def test_cli_audit_runs_and_writes_requested_outputs(config, tmp_path):
    home = tmp_path / "operator-home"
    environ = {
        "KPOPWINS_OPERATOR_HOME": str(home),
        "REDDIT_CLIENT_ID": "cid",
        "REDDIT_CLIENT_SECRET": "secret",
        "REDDIT_USER_AGENT": "UA",
        "REDDIT_TOKEN_URL": "https://reddit.example/api/v1/access_token",
        "REDDIT_API_BASE_URL": "https://oauth.reddit.test",
    }
    initialize_database(load_config(environ))
    with open_database(load_config(environ)) as connection:
        connection.execute(
            """
            INSERT INTO wins (
                show_slug, win_date, api_win_id, artist_name, song_title,
                is_current, last_seen_at
            ) VALUES ('m-countdown', '2024-06-27', 1, 'Riize',
                      'Boom Boom Bass', 1, '2026-08-31T12:00:00Z')
            """
        )
        connection.commit()

    output = io.StringIO()
    errors = io.StringIO()
    exit_code = main(
        [
            "reddit",
            "audit",
            "--show",
            "m-countdown",
            "--output",
            str(tmp_path / "r.json"),
        ],
        environ=environ,
        stdout=output,
        stderr=errors,
        session=audit_session(),
        now="2026-09-01T12:00:00Z",
    )
    assert exit_code == 0, errors.getvalue()
    assert "more-remaining=no" in output.getvalue()
    assert "discovered=2" in output.getvalue()
    assert "new-unverified=2" in output.getvalue()
    assert (tmp_path / "r.json").is_file()
    assert (tmp_path / "r.tsv").is_file()


def test_cli_audit_fails_with_clear_message_when_credentials_missing(tmp_path):
    home = tmp_path / "operator-home"
    initialize_database(Config(home=home, api_base_url="https://api.example.test"))
    output = io.StringIO()
    errors = io.StringIO()
    exit_code = main(
        ["reddit", "audit"],
        environ={"KPOPWINS_OPERATOR_HOME": str(home)},
        stdout=output,
        stderr=errors,
        session=audit_session(),
    )
    assert exit_code == 1
    assert "REDDIT_CLIENT_ID" in errors.getvalue()
    assert "REDDIT_CLIENT_SECRET" in errors.getvalue()
    assert "REDDIT_USER_AGENT" in errors.getvalue()
