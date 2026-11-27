"""Icarus rerolls everything but his fatal 6; a Mush who wants a draw does not skip his roll.

Win rates (racer_stats.json): Scoocher 0.416 is clearly above the median, Streaker 0.096,
Spoilsport 0.078 and Mr Dice Guy 0.124 are clearly below it.
Each test says in its docstring whether it is expected to fail or pass before the fix.
The skip tests drive each power's auto decision directly (Mole's isolation check lives in execute).
"""

from typing import cast

import pytest

from dice_wish_support import (
    BOARD_LENGTH,
    DECIDER_IDX,
    build_engine,
    find_ability,
    rerolls,
    set_drawn_powers,
)
from magsim.core.agent import (
    BooleanInteractive,
    DecisionContext,
    SelectionDecisionContext,
    SelectionInteractive,
)
from magsim.core.state import ActiveRacerState
from magsim.core.types import D6Values, RacerName
from magsim.engine.game_engine import GameEngine
from magsim.racers.dicemonger import DicemongerRerollAction
from magsim.racers.flip_flop import FlipFlopSwap
from magsim.racers.legs import LegsMoveAbility
from magsim.racers.magician import AbilityMagicalReroll
from magsim.racers.mole import MoleTunnel

type SkipKind = type[LegsMoveAbility] | type[MoleTunnel] | type[FlipFlopSwap]

BYSTANDER_IDX = 1
BYSTANDER_POSITION = BOARD_LENGTH - 6
EARLY = 5
LAST_EARLY_TILE = 19
FIRST_CLOSE_TILE = 20
CLOSE_TO_FINISH = 22

ICARUS_KEPT: list[D6Values] = [1, 2, 3, 4, 5]
DICEMONGER_FAILS_TODAY: list[D6Values] = [1, 2, 3]
MAGICIAN_FAILS_TODAY: list[D6Values] = [1, 2, 3, 4]
MAGICIAN_PASSES_TODAY: list[D6Values] = [5]

SKIP_POWERS: list[tuple[RacerName, SkipKind]] = [
    ("Legs", LegsMoveAbility),
    ("Mole", MoleTunnel),
    ("FlipFlop", FlipFlopSwap),
]
LANDING_FROM_EARLY: dict[RacerName, int] = {
    "Legs": EARLY + 5,
    "Mole": EARLY + 6,
    "FlipFlop": BYSTANDER_POSITION,
}

WANTS_A_DRAW = [
    pytest.param(EARLY, [], id="early-no-draw"),
    pytest.param(EARLY, ["MrDiceGuy"], id="early-one-draw"),
    pytest.param(EARLY, ["MrDiceGuy", "Streaker"], id="early-two-weak-draws"),
    pytest.param(LAST_EARLY_TILE, [], id="last-tile-before-the-finish-zone"),
]
NO_DRAW_WANTED = [
    pytest.param(EARLY, ["MrDiceGuy", "Scoocher"], id="two-draws-one-strong"),
    pytest.param(
        EARLY,
        ["MrDiceGuy", "Streaker", "Spoilsport"],
        id="three-weak-draws",
    ),
    pytest.param(FIRST_CLOSE_TILE, [], id="first-tile-of-the-finish-zone"),
    pytest.param(CLOSE_TO_FINISH, ["MrDiceGuy"], id="close-to-finish-one-draw"),
]


# --- Icarus: preferred dice --------------------------------------------------


@pytest.mark.parametrize("rolled", DICEMONGER_FAILS_TODAY)
def test_dicemonger_keeps_an_icarus_roll_of_one_to_three(rolled: D6Values) -> None:
    """Fails today: 1, 2 and 3 are outside the default preferred {4, 5, 6}."""
    engine = build_engine("Icarus", other="Dicemonger")

    assert not rerolls(engine, DicemongerRerollAction, rolled=rolled)


@pytest.mark.parametrize("rolled", [4, 5])
def test_dicemonger_keeps_an_icarus_roll_of_four_or_five(rolled: D6Values) -> None:
    """Passes today: 4 and 5 are already in the default preferred {4, 5, 6}."""
    engine = build_engine("Icarus", other="Dicemonger")

    assert not rerolls(engine, DicemongerRerollAction, rolled=rolled)


def test_dicemonger_rerolls_an_icarus_six() -> None:
    """Passes today (hard ban): guard that the fatal 6 is still rerolled."""
    engine = build_engine("Icarus", other="Dicemonger")

    assert rerolls(engine, DicemongerRerollAction, rolled=6)


@pytest.mark.parametrize("rolled", MAGICIAN_FAILS_TODAY)
def test_magician_keeps_an_icarus_roll_of_one_to_four(rolled: D6Values) -> None:
    """Fails today: below the greed threshold of 5 and no wish, so it is rerolled."""
    engine = build_engine("Icarus", powers=["Magician"])

    assert not rerolls(engine, AbilityMagicalReroll, rolled=rolled)


@pytest.mark.parametrize("rolled", MAGICIAN_PASSES_TODAY)
def test_magician_keeps_an_icarus_five(rolled: D6Values) -> None:
    """Passes today: a 5 meets the greed threshold."""
    engine = build_engine("Icarus", powers=["Magician"])

    assert not rerolls(engine, AbilityMagicalReroll, rolled=rolled)


def test_magician_rerolls_an_icarus_six() -> None:
    """Passes today (hard ban): guard that the fatal 6 is still rerolled."""
    engine = build_engine("Icarus", powers=["Magician"])

    assert rerolls(engine, AbilityMagicalReroll, rolled=6)


@pytest.mark.parametrize(
    ("rolled", "expected"),
    [(1, True), (2, True), (3, True), (4, False), (5, False), (6, False)],
)
def test_dicemonger_keeps_the_plain_rules_for_a_racer_without_a_wish(
    rolled: D6Values,
    expected: bool,
) -> None:
    """Passes today: regression guard, Centaur rerolls 1-3 and keeps 4-6."""
    engine = build_engine("Centaur", other="Dicemonger")

    assert rerolls(engine, DicemongerRerollAction, rolled=rolled) is expected


@pytest.mark.parametrize(
    ("rolled", "expected"),
    [(1, True), (2, True), (3, True), (4, True), (5, False), (6, False)],
)
def test_magician_keeps_the_plain_rules_for_a_racer_without_a_wish(
    rolled: D6Values,
    expected: bool,
) -> None:
    """Passes today: regression guard, Centaur with Magician rerolls 1-4 and keeps 5-6."""
    engine = build_engine("Centaur", powers=["Magician"])

    assert rerolls(engine, AbilityMagicalReroll, rolled=rolled) is expected


# --- Mush: skipping the main roll --------------------------------------------


def with_far_bystander(engine: GameEngine) -> GameEngine:
    """Park the bystander six tiles from the finish, ahead of the decider (a Flip Flop swap target)."""
    engine.get_racer(BYSTANDER_IDX).position = BYSTANDER_POSITION
    return engine


def mush_with(
    power: RacerName,
    position: int,
    drawn: list[RacerName],
    vp_tile_at: int | None = None,
) -> GameEngine:
    """Mush holding `power` as a granted ability, with `drawn` recorded as his draw history."""
    engine = build_engine("Mush", position=position, powers=[power], vp_tile_at=vp_tile_at)
    set_drawn_powers(engine, drawn)
    return with_far_bystander(engine)


def racer_with(power: RacerName, position: int) -> GameEngine:
    """The racer that owns `power` himself, so he has no Mush draw to protect."""
    return with_far_bystander(build_engine(power, position=position))


def skips_main_roll(engine: GameEngine, kind: SkipKind) -> bool:
    """Ask the racer's agent whether `kind` trades the main roll for its move."""
    ability = find_ability(engine, kind)
    agent = engine.get_agent(DECIDER_IDX)
    if isinstance(ability, FlipFlopSwap):
        selection = SelectionDecisionContext[
            SelectionInteractive[ActiveRacerState],
            ActiveRacerState,
        ](
            source=ability,
            event=None,
            game_state=engine.state,
            source_racer_idx=DECIDER_IDX,
            options=engine.get_active_racers(except_racer_idx=DECIDER_IDX),
        )
        return agent.make_selection_decision(engine, selection) is not None
    ctx = DecisionContext[BooleanInteractive](
        source=cast("BooleanInteractive", ability),
        event=None,
        game_state=engine.state,
        source_racer_idx=DECIDER_IDX,
    )
    return agent.make_boolean_decision(engine, ctx)


@pytest.mark.parametrize(("position", "drawn"), WANTS_A_DRAW)
@pytest.mark.parametrize(("power", "kind"), SKIP_POWERS)
def test_mush_wanting_a_draw_does_not_skip_his_roll(
    power: RacerName,
    kind: SkipKind,
    position: int,
    drawn: list[RacerName],
) -> None:
    """Fails today: each power skips for its flat move, forfeiting the chance to roll a 1 or 2."""
    engine = mush_with(power, position, drawn)

    assert not skips_main_roll(engine, kind)


@pytest.mark.parametrize(("position", "drawn"), NO_DRAW_WANTED)
@pytest.mark.parametrize(("power", "kind"), SKIP_POWERS)
def test_mush_without_a_draw_wish_still_skips_his_roll(
    power: RacerName,
    kind: SkipKind,
    position: int,
    drawn: list[RacerName],
) -> None:
    """Passes today: satisfied or near the finish means normal behaviour."""
    engine = mush_with(power, position, drawn)

    assert skips_main_roll(engine, kind)


@pytest.mark.parametrize("position", [EARLY, LAST_EARLY_TILE])
@pytest.mark.parametrize(("power", "kind"), SKIP_POWERS)
def test_a_racer_without_mush_skips_where_mush_would_decline(
    power: RacerName,
    kind: SkipKind,
    position: int,
) -> None:
    """Passes today: the same board situation makes the power's own racer skip (non-vacuity guard)."""
    engine = racer_with(power, position)

    assert skips_main_roll(engine, kind)


@pytest.mark.parametrize(("power", "kind"), SKIP_POWERS)
def test_a_draw_wish_yields_to_a_benefit_tile_at_the_landing(
    power: RacerName,
    kind: SkipKind,
) -> None:
    """Passes today: a VP tile where the skip lands keeps the existing logic, so he still skips."""
    engine = mush_with(power, EARLY, [], vp_tile_at=LANDING_FROM_EARLY[power])

    assert skips_main_roll(engine, kind)
