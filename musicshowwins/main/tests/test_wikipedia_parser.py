from datetime import date, timedelta

import pytest

from main import wikipedia
from main.wikipedia import (
    MAX_SOURCE_ROWS,
    MAX_TABLE_COLUMNS,
    RevisionPage,
    WikipediaClient,
    WikipediaParseError,
    parse_wikipedia_html,
    source_title,
)


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self):
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if kwargs["params"]["action"] == "query":
            return FakeResponse(
                {
                    "query": {
                        "pages": [{"title": "Redirected", "revisions": [{"revid": 99}]}]
                    }
                }
            )
        return FakeResponse({"parse": {"text": "<table></table>"}})


def test_client_uses_revision_id_without_page_parameter():
    session = FakeSession()
    client = WikipediaClient(session=session)

    revision = client.latest_revision("Requested title")
    assert revision == RevisionPage("Redirected", "99")
    assert client.html_for_revision(revision) == "<table></table>"
    assert session.calls[0][1]["params"]["maxlag"] == "5"
    assert session.calls[0][1]["params"]["redirects"] == "1"
    parse_params = session.calls[1][1]["params"]
    assert parse_params["oldid"] == "99"
    assert "page" not in parse_params


def test_parser_expands_spans_and_keeps_exact_collaboration_credit():
    html = """
    <table class="wikitable">
      <tr><th>No.</th><th>Date</th><th>Artist</th><th>Song</th></tr>
      <tr><td>1</td><td rowspan="2">January 5<sup>[1]</sup></td>
          <td rowspan="2">Alpha &amp; Beta feat. Gamma<sup>[a]</sup></td>
          <td>Song A<sup>[2]</sup></td></tr>
      <tr><td>2</td><td>Song B</td></tr>
      <tr><td colspan="4">No broadcast</td></tr>
    </table>
    """

    with pytest.raises(WikipediaParseError, match="multiple wins for date"):
        parse_wikipedia_html(html, 2025)


def test_parser_skips_episode_special_placeholder_before_rowspan_winner():
    html = """
    <table class="wikitable">
      <tr><th>Date</th><th>Artist</th><th>Song</th><th>Score</th></tr>
      <tr><td rowspan="2">March 8</td>
          <td class="table-na" colspan="3">Music Core 400th Episode Special</td></tr>
      <tr><td>TVXQ</td><td>Spellbound</td><td>9,050</td></tr>
    </table>
    """

    rows = parse_wikipedia_html(html, 2014).wins

    assert [(row.date.isoformat(), row.artist, row.song) for row in rows] == [
        ("2014-03-08", "TVXQ", "Spellbound")
    ]


def test_parser_skips_no1_special_episode_listed_as_a_winner():
    html = """
    <table><tr><th>Date</th><th>Artist</th><th>Song</th></tr>
      <tr><td>August 9</td><td>Twice</td><td>Dance the Night Away</td></tr>
      <tr><td>August 16</td><td>M Countdown No.1 Special</td>
          <td>M Countdown No.1 Special</td></tr>
    </table>
    """

    rows = parse_wikipedia_html(html, 2018).wins

    assert [(row.date.isoformat(), row.artist) for row in rows] == [
        ("2018-08-09", "Twice")
    ]


def test_parser_rejects_different_winners_on_the_same_date_as_one_page_failure():
    html = """
    <table><tr><th>Date</th><th>Artist</th><th>Song</th></tr>
      <tr><td>January 5</td><td>First Artist</td><td>First Song</td></tr>
      <tr><td>January 5</td><td>Second Artist</td><td>Second Song</td></tr>
      <tr><td>January 12</td><td>Third Artist</td><td>Third Song</td></tr>
    </table>
    """

    with pytest.raises(WikipediaParseError, match="2025-01-05"):
        parse_wikipedia_html(html, 2025)


def test_parser_removes_surrounding_song_quotes_only():
    html = """
    <table><tr><th>Date</th><th>Artist</th><th>Song</th></tr>
      <tr><td>January 5</td><td>Alpha &amp; Beta feat. Gamma</td>
          <td>&quot;Friday&quot;</td></tr>
      <tr><td>January 12</td><td>Alpha &amp; Beta feat. Gamma</td>
          <td>“Second Song”</td></tr>
    </table>
    """

    rows = parse_wikipedia_html(html, 2025).wins

    assert [(row.artist, row.song) for row in rows] == [
        ("Alpha & Beta feat. Gamma", "Friday"),
        ("Alpha & Beta feat. Gamma", "Second Song"),
    ]


def test_parser_removes_only_the_known_korean_version_presentation_suffix():
    html = """
    <table><tr><th>Date</th><th>Artist</th><th>Song</th></tr>
      <tr><td>March 13</td><td>NCT WISH</td>
          <td><a>Wish</a> <span>(Korean ver.)</span></td></tr>
      <tr><td>March 14</td><td>NCT WISH</td>
          <td>&quot; Wish &quot; (Korean ver.)</td></tr>
      <tr><td>March 20</td><td>Alpha feat. Beta</td>
          <td>Another Song (Korean Ver.)</td></tr>
      <tr><td>March 27</td><td>Alpha feat. Beta</td>
          <td>Another Song (Remix)</td></tr>
    </table>
    """

    rows = parse_wikipedia_html(html, 2024).wins

    assert [(row.artist, row.song) for row in rows] == [
        ("NCT WISH", "Wish"),
        ("NCT WISH", "Wish"),
        ("Alpha feat. Beta", "Another Song (Korean Ver.)"),
        ("Alpha feat. Beta", "Another Song (Remix)"),
    ]


def test_parser_removes_named_presentation_artifacts_without_global_title_rules():
    html = """
    <table><tr><th>Date</th><th>Artist</th><th>Song</th></tr>
      <tr><td>January 5</td><td>WayV</td>
          <td>&quot;Frequency&quot; (Korean Ver.)</td></tr>
      <tr><td>January 12</td><td>Seventeen</td><td>&quot;God of Music</td></tr>
      <tr><td>January 19</td><td>Chen</td><td>&quot; Shall We?</td></tr>
      <tr><td>January 26</td><td>Aespa</td>
          <td>&quot; Up &quot; ( Karina solo)</td></tr>
    </table>
    """

    rows = parse_wikipedia_html(html, 2025).wins

    assert [(row.artist, row.song) for row in rows] == [
        ("WayV", "Frequency (Korean Ver.)"),
        ("Seventeen", "God of Music"),
        ("Chen", "Shall We?"),
        ("Aespa", "Up (Karina solo)"),
    ]


def test_parser_applies_the_explicit_that_that_credit_move_only():
    html = """
    <table><tr><th>Date</th><th>Artist</th><th>Song</th></tr>
      <tr><td>February 5</td><td>Psy</td><td>That That</td></tr>
      <tr><td>February 12</td><td>Psy</td><td>Daddy</td></tr>
    </table>
    """

    rows = parse_wikipedia_html(html, 2025).wins

    assert [(row.artist, row.song) for row in rows] == [
        ("Psy feat. Suga", "That That"),
        ("Psy", "Daddy"),
    ]


@pytest.mark.parametrize(
    ("show_slug", "html", "expected"),
    [
        (
            "music-bank",
            """
            <table><tr><th>Date</th><th>Artist</th><th>Song</th></tr>
            <tr><td>January 5</td><td>Alpha</td><td>Song A</td></tr></table>
            """,
            [("2025-01-05", "Alpha", "Song A")],
        ),
        (
            "music-core",
            """
            <table><tr><th>Date</th><th>Artist</th><th>Song</th></tr>
            <tr><td>February 6<sup>[1]</sup></td>
                <td>Alpha &amp; Beta feat. Gamma</td><td>Song A</td></tr></table>
            """,
            [("2025-02-06", "Alpha & Beta feat. Gamma", "Song A")],
        ),
        (
            "inkigayo",
            """
            <table><tr><th>Date</th><th>Artist</th><th>Song</th></tr>
            <tr><td>March 7</td><td>Alpha<sup>[a]</sup></td>
                <td>Song A<sup>[2]</sup></td></tr></table>
            """,
            [("2025-03-07", "Alpha", "Song A")],
        ),
        (
            "m-countdown",
            """
            <table><tr><th>Date</th><th>Artist</th><th>Song</th></tr>
            <tr><td>April 8</td><td>No broadcast</td><td>—</td></tr>
            <tr><td>April 15</td><td>Alpha</td><td>Song A</td></tr></table>
            """,
            [("2025-04-15", "Alpha", "Song A")],
        ),
        (
            "show-champion",
            """
            <table><tr><th>Date</th><th>Artist</th><th>Song</th></tr>
            <tr><td colspan="1">May 9</td><td>Alpha</td><td>Song A</td></tr></table>
            """,
            [("2025-05-09", "Alpha", "Song A")],
        ),
        (
            "the-show",
            """
            <table><tr><th>Date</th><th>Artist</th><th>Song</th></tr>
            <tr><td>2025-06-10</td><td>Alpha</td><td>Song A</td></tr></table>
            """,
            [("2025-06-10", "Alpha", "Song A")],
        ),
    ],
)
def test_parser_accepts_representative_layout_for_each_show(show_slug, html, expected):
    assert show_slug
    rows = parse_wikipedia_html(html, 2025).wins
    assert [(row.date.isoformat(), row.artist, row.song) for row in rows] == expected


def test_parser_rejects_malformed_rows_and_wrong_year():
    malformed = """
    <table><tr><th>Date</th><th>Artist</th><th>Song</th></tr>
    <tr><td>January 5</td><td>Alpha</td><td></td></tr></table>
    """
    with pytest.raises(WikipediaParseError):
        parse_wikipedia_html(malformed, 2025)

    wrong_year = """
    <table><tr><th>Date</th><th>Artist</th><th>Song</th></tr>
    <tr><td>January 5, 2024</td><td>Alpha</td><td>Song</td></tr></table>
    """
    with pytest.raises(WikipediaParseError):
        parse_wikipedia_html(wrong_year, 2025)


def test_shared_page_selects_requested_year_section():
    html = """
    <h2>2013</h2>
    <table><tr><th>Date</th><th>Artist</th><th>Song</th></tr>
      <tr><td>January 5</td><td>Wrong Artist</td><td>Wrong Song</td></tr></table>
    <h2>2014</h2>
    <table><tr><th>Date</th><th>Artist</th><th>Song</th></tr>
      <tr><td>February 6</td><td>Right Artist</td><td>Right Song</td></tr></table>
    """

    rows = parse_wikipedia_html(html, 2014).wins

    assert [(row.artist, row.song) for row in rows] == [("Right Artist", "Right Song")]


def test_shared_page_missing_requested_year_fails_instead_of_relabeling():
    html = """
    <h2>2013</h2>
    <table><tr><th>Date</th><th>Artist</th><th>Song</th></tr>
      <tr><td>January 5</td><td>Wrong Artist</td><td>Wrong Song</td></tr></table>
    """

    with pytest.raises(WikipediaParseError, match="scoped to 2014"):
        parse_wikipedia_html(html, 2014)


def test_multiple_requested_year_tables_are_merged_and_validated_together():
    html = """
    <h2>2014</h2>
    <table><tr><th>Date</th><th>Artist</th><th>Song</th></tr>
      <tr><td>January 5</td><td>First Artist</td><td>First Song</td></tr></table>
    <table><tr><th>Date</th><th>Artist</th><th>Song</th></tr>
      <tr><td>February 6</td><td>Second Artist</td><td>Second Song</td></tr></table>
    """

    rows = parse_wikipedia_html(html, 2014).wins

    assert len(rows) == 2
    assert {row.artist for row in rows} == {"First Artist", "Second Artist"}


def test_malformed_requested_year_table_is_not_ignored():
    html = """
    <h2>2014</h2>
    <table><tr><th>Date</th><th>Artist</th><th>Song</th></tr>
      <tr><td>January 5</td><td>Valid Artist</td><td>Valid Song</td></tr></table>
    <table><tr><th>Date</th><th>Artist</th><th>Song</th></tr>
      <tr><td>not-a-date</td><td>Broken Artist</td><td>Broken Song</td></tr></table>
    """

    with pytest.raises(WikipediaParseError, match="Invalid date"):
        parse_wikipedia_html(html, 2014)


@pytest.mark.parametrize(
    ("slug", "year", "expected"),
    [
        ("music-core", 2018, "List of Show! Music Core Chart winners (2018)"),
        ("music-core", 2019, "List of Show! Music Core Chart winners (2019)"),
        ("inkigayo", 2025, "List of Inkigayo Chart winners (2025)"),
        ("m-countdown", 2025, "List of M Countdown Chart winners (2025)"),
        ("show-champion", 2020, "Show Champion"),
        ("show-champion", 2021, "List of Show Champion Chart winners (2021)"),
        ("the-show", 2020, "The Show (South Korean TV program)"),
        ("the-show", 2021, "List of The Show Chart winners (2021)"),
        ("music-bank", 2025, "List of Music Bank Chart winners (2025)"),
    ],
)
def test_source_title_handles_dedicated_and_shared_pages(slug, year, expected):
    assert source_title(slug, year) == expected


@pytest.mark.parametrize(
    ("slug", "year", "expected"),
    [
        ("music-core", 2014, "Show! Music Core"),
        ("music-core", 2015, "List of Show! Music Core Chart winners (2015)"),
        ("music-core", 2026, "List of Show! Music Core Chart winners (2026)"),
        ("show-champion", 2014, "Show Champion"),
        ("show-champion", 2020, "Show Champion"),
        (
            "show-champion",
            2021,
            "List of Show Champion Chart winners (2021)",
        ),
        ("the-show", 2014, "The Show (South Korean TV program)"),
        ("the-show", 2020, "The Show (South Korean TV program)"),
        ("the-show", 2021, "List of The Show Chart winners (2021)"),
        ("inkigayo", 2026, "List of Inkigayo Chart winners (2026)"),
        ("m-countdown", 2026, "List of M Countdown Chart winners (2026)"),
        ("music-bank", 2026, "List of Music Bank Chart winners (2026)"),
    ],
)
def test_source_title_routes_supported_year_boundaries(slug, year, expected):
    assert source_title(slug, year) == expected


def test_parser_classifies_no_winner_rows_as_episode_statuses():
    html = """
    <table><tr><th>Date</th><th>Artist</th><th>Song</th></tr>
      <tr><td>January 5</td><td>Alpha</td><td>Song</td></tr>
      <tr><td>January 12</td><td colspan="2">No Broadcast or Winner</td></tr>
      <tr><td>January 19</td><td colspan="2">No show, winner not announced</td></tr>
      <tr><td>January 26</td>
          <td colspan="2">MAMA Special Broadcast, winners were not announced</td></tr>
      <tr><td>February 2</td><td colspan="2">Show Special, No Chart and Winner</td></tr>
      <tr><td>February 9</td><td colspan="2">No Chart</td></tr>
      <tr><td>February 9</td><td colspan="2">No Winner</td></tr>
      <tr><td colspan="3">
          No show, winners were not announced (September 9 – November 18)</td></tr>
      <tr><td>December 30, 2024</td><td colspan="2">No show</td></tr>
    </table>
    """

    page = parse_wikipedia_html(html, 2025)

    assert [(row.date.isoformat(), row.status) for row in page.episodes] == [
        ("2025-01-12", "not_aired"),
        ("2025-01-19", "not_aired"),
        ("2025-01-26", "special"),
        ("2025-02-02", "special"),
        ("2025-02-09", "no_winner"),
    ]
    assert page.episodes[0].label == "No Broadcast or Winner"


def test_parser_drops_an_episode_status_on_a_date_with_a_winner():
    html = """
    <table class="wikitable">
      <tr><th>Date</th><th>Artist</th><th>Song</th><th>Score</th></tr>
      <tr><td rowspan="2">March 8</td>
          <td class="table-na" colspan="3">Music Core 400th Episode Special</td></tr>
      <tr><td>TVXQ</td><td>Spellbound</td><td>9,050</td></tr>
    </table>
    """

    assert parse_wikipedia_html(html, 2014).episodes == []


@pytest.mark.parametrize("attribute", ["rowspan", "colspan"])
@pytest.mark.parametrize("value", ["1000000000", "9" * 10_000])
def test_parser_rejects_huge_spans_as_source_errors(attribute, value):
    html = (
        "<table><tr><th>Date</th><th>Artist</th><th>Song</th></tr>"
        f'<tr><td>January 5</td><td {attribute}="{value}">Alpha</td>'
        "<td>Song</td></tr></table>"
    )

    with pytest.raises(WikipediaParseError, match=f"{attribute}.*limit"):
        parse_wikipedia_html(html, 2025)


@pytest.mark.parametrize("attribute", ["rowspan", "colspan"])
@pytest.mark.parametrize("value", ["0", "-1", "1.5", "junk", "", "2;", "٢"])
def test_parser_rejects_malformed_spans_instead_of_guessing(attribute, value):
    html = f'<table><tr><td {attribute}="{value}">Ignored</td></tr></table>'

    with pytest.raises(WikipediaParseError, match=attribute):
        parse_wikipedia_html(html, 2025)


def test_parser_limits_actual_rows_even_when_they_are_empty():
    html = "<table>" + "<tr></tr>" * (MAX_SOURCE_ROWS + 1) + "</table>"

    with pytest.raises(WikipediaParseError, match="rows exceed page limit"):
        parse_wikipedia_html(html, 2025)


def test_parser_limits_columns_with_only_individually_valid_spans():
    html = (
        '<table><tr><td colspan="32">First</td>'
        '<td colspan="33">Second</td></tr></table>'
    )

    with pytest.raises(WikipediaParseError, match="columns exceed limit"):
        parse_wikipedia_html(html, 2025)


def test_parser_limits_columns_accumulated_by_active_rowspans():
    html = (
        '<table><tr><td rowspan="1000" colspan="32">First</td></tr>'
        '<tr><td rowspan="1000" colspan="32">Second</td></tr>'
        "<tr><td>Overflow</td></tr></table>"
    )

    with pytest.raises(WikipediaParseError, match="columns exceed limit"):
        parse_wikipedia_html(html, 2025)


def test_parser_limits_work_across_tables_before_reserving_more_active_spans():
    table = '<table><tr><td rowspan="1000" colspan="64">X</td></tr></table>'

    with pytest.raises(WikipediaParseError, match="work exceeds page limit"):
        parse_wikipedia_html(table * 8, 2025)


def test_parser_charges_actual_rows_carried_by_active_spans(monkeypatch):
    monkeypatch.setattr(wikipedia, "MAX_EXPANSION_WORK", 100)
    html = (
        '<table><tr><td rowspan="10" colspan="8">X</td></tr>'
        + "<tr></tr>" * 9
        + "</table>"
    )

    with pytest.raises(WikipediaParseError, match="work exceeds page limit"):
        parse_wikipedia_html(html, 2025)


def test_parser_limits_actual_rows_across_tables(monkeypatch):
    monkeypatch.setattr(wikipedia, "MAX_SOURCE_ROWS", 4)
    table = "<table><tr></tr><tr></tr><tr></tr></table>"

    with pytest.raises(WikipediaParseError, match="rows exceed page limit"):
        parse_wikipedia_html(table * 2, 2025)


def test_parser_limits_expanded_cells_across_tables(monkeypatch):
    monkeypatch.setattr(wikipedia, "MAX_EXPANDED_CELLS", 2 * MAX_TABLE_COLUMNS)
    table = f'<table><tr><td colspan="{MAX_TABLE_COLUMNS}">X</td></tr></table>'

    with pytest.raises(WikipediaParseError, match="cells exceed page limit"):
        parse_wikipedia_html(table * 3, 2025)


def test_parser_rejects_overlapping_spans():
    html = (
        '<table><tr><td>First</td><td rowspan="2">Active</td></tr>'
        '<tr><td colspan="2">Overlap</td></tr></table>'
    )

    with pytest.raises(WikipediaParseError, match="overlapping cell spans"):
        parse_wikipedia_html(html, 2025)


def test_parser_keeps_a_full_year_with_a_spanning_artist_and_grouped_header():
    body = []
    for week in range(52):
        day = date(2014, 1, 3) + timedelta(weeks=week)
        artist = '<td rowspan="52">Alpha &amp; Beta</td>' if week == 0 else ""
        body.append(
            f"<tr><td>{day.isoformat()}</td>{artist}<td>Song {week}</td>"
            "<td>9,000</td></tr>"
        )
    html = (
        '<h2>2014</h2><table><tr><th rowspan="2">Date</th>'
        '<th rowspan="2">Artist</th><th colspan="2">Song and score</th></tr>'
        "<tr><th>Song</th><th>Score</th></tr>" + "".join(body) + "</table>"
    )

    rows = parse_wikipedia_html(html, 2014).wins

    assert len(rows) == 52
    assert rows[-1].date == date(2014, 12, 26)
    assert rows[-1].artist == "Alpha & Beta"
    assert rows[-1].song == "Song 51"
