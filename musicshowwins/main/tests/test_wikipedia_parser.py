import pytest

from main.wikipedia import (
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

    rows = parse_wikipedia_html(html, 2025)

    assert [(row.date.isoformat(), row.artist, row.song) for row in rows] == [
        ("2025-01-05", "Alpha & Beta feat. Gamma", "Song A"),
        ("2025-01-05", "Alpha & Beta feat. Gamma", "Song B"),
    ]


def test_parser_removes_surrounding_song_quotes_only():
    html = """
    <table><tr><th>Date</th><th>Artist</th><th>Song</th></tr>
      <tr><td>January 5</td><td>Alpha &amp; Beta feat. Gamma</td>
          <td>&quot;Friday&quot;</td></tr>
      <tr><td>January 12</td><td>Alpha &amp; Beta feat. Gamma</td>
          <td>“Second Song”</td></tr>
    </table>
    """

    rows = parse_wikipedia_html(html, 2025)

    assert [(row.artist, row.song) for row in rows] == [
        ("Alpha & Beta feat. Gamma", "Friday"),
        ("Alpha & Beta feat. Gamma", "Second Song"),
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
            <tr><td rowspan="2">February 6<sup>[1]</sup></td>
                <td rowspan="2">Alpha &amp; Beta feat. Gamma</td><td>Song A</td></tr>
            <tr><td>Song B</td></tr></table>
            """,
            [
                ("2025-02-06", "Alpha & Beta feat. Gamma", "Song A"),
                ("2025-02-06", "Alpha & Beta feat. Gamma", "Song B"),
            ],
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
    rows = parse_wikipedia_html(html, 2025)
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

    rows = parse_wikipedia_html(html, 2014)

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

    rows = parse_wikipedia_html(html, 2014)

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
