"""Mush with his own power wants to draw (faces 1 and 2) while early and unsatisfied.

Win rates (racer_stats.json): Scoocher 0.416 is clearly above the median, Streaker 0.096,
Spoilsport 0.078, Mr Dice Guy 0.124 and Cheatah 0.105 are clearly below it.
Each test says in its docstring whether it is expected to fail or pass before the fix.
"""

import pytest

from dice_wish_support import (
    build_engine,
    cheatah_support,
    pick_duplicate,
    rerolls,
    set_drawn_powers,
)
from magsim.core.types import D6Values, RacerName
from magsim.engine.game_engine import GameEngine
from magsim.racers.dicemonger import DicemongerRerollAction
from magsim.racers.magician import AbilityMagicalReroll

EARLY = 5
LAST_EARLY_TILE = 19
FIRST_CLOSE_TILE = 20
CLOSE_TO_FINISH = 22
DRAW_FACES = frozenset({1, 2})
PLAIN_SUPPORT = frozenset({4, 5, 6})

WANTS_A_DRAW = [
    pytest.param(EARLY, [], id="early-no-draw"),
    pytest.param(EARLY, ["MrDiceGuy"], id="early-one-draw"),
    pytest.param(EARLY, ["MrDiceGuy", "Streaker"], id="early-two-weak-draws"),
    pytest.param(LAST_EARLY_TILE, [], id="last-tile-before-the-finish-zone"),
]
NO_WISH = [
    pytest.param(EARLY, ["MrDiceGuy", "Scoocher"], id="two-draws-one-strong"),
    pytest.param(
        EARLY,
        ["MrDiceGuy", "Streaker", "Spoilsport"],
        id="three-weak-draws",
    ),
    pytest.param(FIRST_CLOSE_TILE, [], id="first-tile-of-the-finish-zone"),
    pytest.param(CLOSE_TO_FINISH, ["MrDiceGuy"], id="close-to-finish-one-draw"),
]


def mush(
    powers: list[RacerName],
    position: int,
    drawn: list[RacerName],
    vp_tile_at: int | None = None,
    other: RacerName = "Centaur",
) -> GameEngine:
    """Mush holding `powers` as granted abilities, with `drawn` recorded as his draw history."""
    engine = build_engine(
        "Mush",
        position=position,
        powers=powers,
        vp_tile_at=vp_tile_at,
        other=other,
    )
    set_drawn_powers(engine, drawn)
    return engine


# --- Mr Dice Guy -------------------------------------------------------------


@pytest.mark.parametrize(("position", "drawn"), WANTS_A_DRAW)
def test_mr_dice_guy_mush_wanting_a_draw_picks_the_low_duplicate(
    position: int,
    drawn: list[RacerName],
) -> None:
    """Fails today: he picks the highest duplicate, the 5."""
    engine = mush(["MrDiceGuy"], position, drawn)

    assert pick_duplicate(engine, [2, 5]) == 2


@pytest.mark.parametrize(("position", "drawn"), NO_WISH)
def test_mr_dice_guy_mush_without_a_wish_picks_by_landing(
    position: int,
    drawn: list[RacerName],
) -> None:
    """Passes today: satisfied or near the finish means normal behaviour."""
    engine = mush(["MrDiceGuy"], position, drawn)

    assert pick_duplicate(engine, [2, 5]) == 5


def test_mr_dice_guy_without_mush_never_wants_a_draw() -> None:
    """Passes today: only a racer with his own Mush power gets the bonus."""
    engine = build_engine("MrDiceGuy", position=EARLY)

    assert pick_duplicate(engine, [2, 5]) == 5


def test_a_draw_wish_yields_to_a_benefit_tile() -> None:
    """Passes today: the VP tile five ahead beats the wish for a 2."""
    engine = mush(["MrDiceGuy"], EARLY, [], vp_tile_at=EARLY + 5)

    assert pick_duplicate(engine, [2, 5]) == 5


# --- Cheatah -----------------------------------------------------------------


@pytest.mark.parametrize(("position", "drawn"), WANTS_A_DRAW)
def test_cheatah_mush_wanting_a_draw_only_sets_low_faces(
    position: int,
    drawn: list[RacerName],
) -> None:
    """Fails today: the support is {4, 5, 6}."""
    engine = mush(["Cheatah"], position, drawn)

    support = cheatah_support(engine)

    assert support
    assert support <= DRAW_FACES


@pytest.mark.parametrize(("position", "drawn"), NO_WISH)
def test_cheatah_mush_without_a_wish_keeps_the_normal_support(
    position: int,
    drawn: list[RacerName],
) -> None:
    """Passes today: satisfied or near the finish means normal behaviour."""
    engine = mush(["Cheatah"], position, drawn)

    assert cheatah_support(engine) == PLAIN_SUPPORT


def test_cheatah_without_mush_keeps_the_normal_support_early_in_the_race() -> None:
    """Passes today: regression guard, no Mush means no draw bonus."""
    engine = build_engine("Cheatah", position=EARLY)

    assert cheatah_support(engine) == PLAIN_SUPPORT


def test_mush_with_cheatah_and_icarus_wants_a_draw_but_never_a_six() -> None:
    """Fails today: the support is {4, 5, 6}, including the banned 6."""
    engine = mush(["Cheatah", "Icarus"], EARLY, [])

    support = cheatah_support(engine)

    assert support
    assert support <= DRAW_FACES
    assert 6 not in support


# --- Reroll decisions --------------------------------------------------------


@pytest.mark.parametrize("rolled", [1, 2])
@pytest.mark.parametrize(("position", "drawn"), WANTS_A_DRAW)
def test_mush_with_magician_keeps_a_drawing_roll(
    position: int,
    drawn: list[RacerName],
    rolled: D6Values,
) -> None:
    """Fails today: a 1 or 2 is below the reroll threshold."""
    engine = mush(["Magician"], position, drawn)

    assert not rerolls(engine, AbilityMagicalReroll, rolled=rolled)


@pytest.mark.parametrize("rolled", [1, 2])
@pytest.mark.parametrize(("position", "drawn"), NO_WISH)
def test_mush_with_magician_rerolls_a_low_roll_without_a_wish(
    position: int,
    drawn: list[RacerName],
    rolled: D6Values,
) -> None:
    """Passes today: satisfied or near the finish means normal behaviour."""
    engine = mush(["Magician"], position, drawn)

    assert rerolls(engine, AbilityMagicalReroll, rolled=rolled)


@pytest.mark.parametrize("rolled", [1, 2])
@pytest.mark.parametrize(("position", "drawn"), WANTS_A_DRAW)
def test_mush_wanting_a_draw_keeps_a_drawing_roll_against_dicemonger(
    position: int,
    drawn: list[RacerName],
    rolled: D6Values,
) -> None:
    """Fails today: a 1 or 2 is outside the default {4, 5, 6}."""
    engine = mush([], position, drawn, other="Dicemonger")

    assert not rerolls(engine, DicemongerRerollAction, rolled=rolled)


@pytest.mark.parametrize("rolled", [1, 2])
@pytest.mark.parametrize(("position", "drawn"), NO_WISH)
def test_mush_without_a_wish_rerolls_a_low_roll_against_dicemonger(
    position: int,
    drawn: list[RacerName],
    rolled: D6Values,
) -> None:
    """Passes today: satisfied or near the finish means normal behaviour."""
    engine = mush([], position, drawn, other="Dicemonger")

    assert rerolls(engine, DicemongerRerollAction, rolled=rolled)
