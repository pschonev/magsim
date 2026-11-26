"""Dice choices honour hard bans, board benefits and soft wishes (Cheatah, Mr Dice Guy, Magician, Dicemonger).

Each test says in its docstring whether it is expected to fail or pass before the fix.
"""

import pytest

from dice_wish_support import (
    build_engine,
    cheatah_support,
    pick_duplicate,
    rerolls,
)
from magsim.core.types import D6Values, RacerName
from magsim.racers.dicemonger import DicemongerRerollAction
from magsim.racers.magician import AbilityMagicalReroll

BANNING_POWERS: list[RacerName] = ["Icarus", "Sisyphus"]
PLAIN_SUPPORT = frozenset({4, 5, 6})
FACES_SKIPPER_DOES_NOT_WISH = frozenset({2, 3, 4})


# --- Level 1: hard ban -------------------------------------------------------


@pytest.mark.parametrize("power", BANNING_POWERS)
def test_cheatah_never_sets_a_banned_face(power: RacerName) -> None:
    """Fails today: Cheatah's equilibrium mix includes the 6."""
    engine = build_engine("Cheatah", powers=[power])

    support = cheatah_support(engine)

    assert support
    assert 6 not in support


@pytest.mark.parametrize("power", BANNING_POWERS)
def test_mr_dice_guy_skips_a_banned_duplicate(power: RacerName) -> None:
    """Fails today: he takes the highest safe duplicate, the 6."""
    engine = build_engine("MrDiceGuy", powers=[power])

    assert pick_duplicate(engine, [6, 3]) == 3


@pytest.mark.parametrize("power", BANNING_POWERS)
def test_mr_dice_guy_takes_the_banned_duplicate_when_nothing_else_exists(
    power: RacerName,
) -> None:
    """Passes today: with every option banned nothing is excluded."""
    engine = build_engine("MrDiceGuy", powers=[power])

    assert pick_duplicate(engine, [6]) == 6


def test_a_banned_duplicate_beats_a_benefit_tile() -> None:
    """Fails today: the VP tile six ahead lures him onto the banned 6."""
    engine = build_engine("MrDiceGuy", powers=["Icarus"], vp_tile_at=6)

    assert pick_duplicate(engine, [6, 3]) == 3


@pytest.mark.parametrize("power", BANNING_POWERS)
def test_magician_rerolls_a_banned_value(power: RacerName) -> None:
    """Fails today: a 6 is in his default {4, 5, 6} so he keeps it."""
    engine = build_engine("Magician", powers=[power])

    assert rerolls(engine, AbilityMagicalReroll, rolled=6)


def test_magician_rerolls_a_banned_value_even_onto_a_benefit_tile() -> None:
    """Fails today: the VP tile at the landing keeps the 6."""
    engine = build_engine("Magician", powers=["Icarus"], vp_tile_at=6)

    assert rerolls(engine, AbilityMagicalReroll, rolled=6)


@pytest.mark.parametrize(
    ("rolled", "expected"),
    [(6, True), (5, False)],
)
def test_dicemonger_reroll_is_offered_for_a_banned_value_only(
    rolled: D6Values,
    expected: bool,
) -> None:
    """Fails today for the 6 (kept as default-preferred); the 5 passes today."""
    engine = build_engine("Icarus", other="Dicemonger")

    assert rerolls(engine, DicemongerRerollAction, rolled=rolled) is expected


# --- Level 2: board situation ------------------------------------------------


def test_magician_keeps_a_one_when_a_vp_tile_is_one_ahead() -> None:
    """Passes today: a benefit at the landing beats the low-roll reroll."""
    engine = build_engine("Magician", vp_tile_at=1)

    assert not rerolls(engine, AbilityMagicalReroll, rolled=1)


def test_magician_rerolls_a_one_without_a_benefit_tile() -> None:
    """Passes today: a 1 is not in {4, 5, 6}."""
    engine = build_engine("Magician")

    assert rerolls(engine, AbilityMagicalReroll, rolled=1)


def test_mr_dice_guy_prefers_a_benefit_tile_over_a_soft_wish() -> None:
    """Passes today: the VP tile three ahead wins over Skipper's wish for 1."""
    engine = build_engine("MrDiceGuy", powers=["Skipper"], vp_tile_at=3)

    assert pick_duplicate(engine, [1, 3]) == 3


# --- Level 3: soft wishes ----------------------------------------------------


def test_mr_dice_guy_with_skipper_picks_the_wished_duplicate() -> None:
    """Fails today: he takes the highest duplicate, the 3."""
    engine = build_engine("MrDiceGuy", powers=["Skipper"])

    assert pick_duplicate(engine, [1, 3]) == 1


def test_cheatah_with_skipper_leans_on_the_wished_face() -> None:
    """Fails today: the support is {4, 5, 6} and never includes the 1."""
    engine = build_engine("Cheatah", powers=["Skipper"])

    support = cheatah_support(engine)

    assert 1 in support
    assert not FACES_SKIPPER_DOES_NOT_WISH & support


def test_cheatah_without_wishes_keeps_the_distance_based_support() -> None:
    """Passes today: regression guard for the unchanged default behaviour."""
    engine = build_engine("Cheatah")

    assert cheatah_support(engine) == PLAIN_SUPPORT


@pytest.mark.parametrize(
    ("rolled", "expected"),
    [(1, False), (3, True)],
)
def test_magician_with_skipper_keeps_a_wished_value(
    rolled: D6Values,
    expected: bool,
) -> None:
    """Fails today for the 1 (rerolled as low); the 3 passes today."""
    engine = build_engine("Magician", powers=["Skipper"])

    assert rerolls(engine, AbilityMagicalReroll, rolled=rolled) is expected


@pytest.mark.parametrize(
    ("rolled", "expected"),
    [(1, False), (3, True)],
)
def test_dicemonger_reroll_follows_skipper_wishes(
    rolled: D6Values,
    expected: bool,
) -> None:
    """Passes today: Dicemonger already intersects non-default preferred sets."""
    engine = build_engine("Skipper", other="Dicemonger")

    assert rerolls(engine, DicemongerRerollAction, rolled=rolled) is expected
