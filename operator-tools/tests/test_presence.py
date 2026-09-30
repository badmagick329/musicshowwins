from __future__ import annotations

import pytest

from kpopwins_operator.presence import _win_key, winner_performed

LINEUP = """## LINEUP

### Comeback Stages

Artist | Song | Unofficial | Official Fancam |
:--|:--|:--|:--|
{rows}

----

## WINNER

### [{winner} - Song](https://www.youtube.com/watch?v=abc)
"""

OTHERS = ["ITZY (있지)", "ATEEZ (에이티즈)", "ONEUS (원어스)", "CLC (씨엘씨)"]


def page(performers, winner):
    rows = "\n".join(
        f"{name} | [Song](https://x.test) | -- | -- |" for name in performers
    )
    return LINEUP.format(rows=rows, winner=winner)


@pytest.mark.parametrize(
    ("performers", "winner", "catalogue", "expected"),
    [
        ([*OTHERS, "Red Velvet (레드벨벳)"], "Red Velvet", "Red Velvet", True),
        ([*OTHERS, "KARD (카드)"], "Red Velvet", "Red Velvet", False),
        # Reddit's own naming bridges catalogue aliases.
        ([*OTHERS, "TXT (투모로우바이투게더)"], "TXT", "Tomorrow X Together", True),
        # Collaboration credits match on any credited artist.
        ([*OTHERS, "PSY (싸이)"], "PSY", "Psy feat. Suga", True),
        # Short lineups are special or incomplete episodes.
        (OTHERS[:3], "Red Velvet", "Red Velvet", None),
    ],
)
def test_winner_performed(performers, winner, catalogue, expected):
    assert winner_performed(page(performers, winner), catalogue) is expected


def test_winner_named_only_in_winner_section_is_absent():
    markdown = page([*OTHERS, "KARD (카드)"], "SUHO")
    assert winner_performed(markdown, "Suho") is False


def test_missing_winner_section_is_unknown():
    markdown = page([*OTHERS, "KARD (카드)"], "X").split("## WINNER")[0]
    assert winner_performed(markdown, "Suho") is None


def test_postponed_episode_documents_the_win_it_aired():
    assert _win_key("music-bank", "2025-04-04") == ("music-bank", "2025-03-28")
    assert _win_key("music-bank", "2025-04-11") == ("music-bank", "2025-04-11")
