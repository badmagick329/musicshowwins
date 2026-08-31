from __future__ import annotations

from io import BytesIO, StringIO, TextIOWrapper

from kpopwins_operator.cli import main
from kpopwins_operator.database import insert_candidate

from .conftest import add_win


def test_candidate_list_reconfigures_windows_charmap_stream_to_utf8(config, connection):
    add_win(connection)
    insert_candidate(
        connection,
        {
            "show_slug": "music-bank",
            "win_date": "2026-01-02",
            "reference_type": "video",
            "provider": "youtube",
            "external_id": "unicode-video",
            "url": "https://www.youtube.com/watch?v=unicode-video",
            "title": "아이브 1위 앵콜",
            "publisher_name": "한국 방송",
        },
        timestamp="2026-08-31T12:00:00Z",
    )
    connection.commit()
    raw_output = BytesIO()
    windows_output = TextIOWrapper(raw_output, encoding="cp1252", errors="strict")

    result = main(
        ["candidates", "list", "--provider", "youtube", "--status", "pending"],
        environ={"KPOPWINS_OPERATOR_HOME": str(config.home)},
        stdout=windows_output,
        stderr=StringIO(),
    )
    windows_output.flush()

    assert result == 0
    assert windows_output.encoding == "utf-8"
    rendered = raw_output.getvalue().decode("utf-8")
    assert "아이브 1위 앵콜" in rendered
    assert "한국 방송" in rendered
