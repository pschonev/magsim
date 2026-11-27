"""Situational dice bans: Scrying Pool totals and Party Pooper's rejected 6.

Each test says in its docstring whether it is expected to fail or pass before the fix.
Modifier setups: Coach on the same tile gives +1, Gunk gives -1 (see get_current_modifiers).
"""

from collections.abc import Callable

import pytest

from dice_wish_support import (
    DECIDER_IDX,
    build_engine,
    cheatah_support,
    pick_duplicate,
    rerolls,
)
from magsim.core.events import Phase
from magsim.core.types import D6Values, RacerName
from magsim.engine.abilities import add_racer_modifier
from magsim.engine.game_engine import GameEngine
from magsim.engine.twist import ScryingPoolRule, scrying_pool
from magsim.racers.dicemonger import DicemongerRerollAction
from magsim.racers.magician import AbilityMagicalReroll

PLAIN_SUPPORT = frozenset({4, 5, 6})
BYSTANDER_IDX = 1

type Departure = Callable[[GameEngine], None]


def scrying_pool_engine(
    name: RacerName,
    *,
    other: RacerName = "Centaur",
    powers: tuple[RacerName, ...] = (),
) -> GameEngine:
    """Real engine after the real Scrying Pool twist hit every racer."""
    engine = build_engine(name, other=other, powers=powers)
    scrying_pool(engine, DECIDER_IDX, Phase.TWIST_QUEUE)
    assert any(
        isinstance(m, ScryingPoolRule) for m in engine.get_racer(DECIDER_IDX).modifiers
    )
    return engine


def eliminated(engine: GameEngine) -> None:
    engine.get_racer(BYSTANDER_IDX).eliminate()


def finished(engine: GameEngine) -> None:
    engine.get_racer(BYSTANDER_IDX).finish_position = 1


def lost_ability(engine: GameEngine) -> None:
    engine.clear_all_abilities(BYSTANDER_IDX)


DEPARTURES: list[Departure] = [eliminated, finished, lost_ability]


# --- Scrying Pool: Cheatah ---------------------------------------------------


@pytest.mark.parametrize(
    ("other", "banned"),
    [("Centaur", {6}), ("Coach", {5, 6})],
)
def test_cheatah_never_sets_a_face_that_reaches_the_pool_limit(
    other: RacerName,
    banned: set[int],
) -> None:
    """Fails today: Cheatah's mix includes the 6 (and the 5 with a +1 modifier)."""
    engine = scrying_pool_engine("Cheatah", other=other)

    support = cheatah_support(engine)

    assert support
    assert not banned & support


@pytest.mark.parametrize("other", ["Centaur", "Coach"])
def test_cheatah_without_the_pool_keeps_the_plain_support(other: RacerName) -> None:
    """Passes today: regression guard, no rule means nothing is banned."""
    engine = build_engine("Cheatah", other=other)

    assert cheatah_support(engine) == PLAIN_SUPPORT


def test_cheatah_ignores_a_pool_rule_that_only_hits_another_racer() -> None:
    """Passes today: the ban is per racer, only the modifier owner is affected."""
    engine = build_engine("Cheatah")
    add_racer_modifier(engine, BYSTANDER_IDX, ScryingPoolRule(owner_idx=None))

    assert cheatah_support(engine) == PLAIN_SUPPORT


def test_cheatah_may_still_set_a_six_when_a_slowing_modifier_keeps_the_total_safe() -> (
    None
):
    """Passes today: 6 with Gunk's -1 totals 5, so it must not be banned."""
    engine = scrying_pool_engine("Cheatah", other="Gunk")

    assert 6 in cheatah_support(engine)


# --- Scrying Pool: Mr Dice Guy -----------------------------------------------


@pytest.mark.parametrize(
    ("other", "duplicates", "expected"),
    [("Centaur", [6, 3], 3), ("Coach", [5, 3], 3)],
)
def test_mr_dice_guy_skips_a_duplicate_that_reaches_the_pool_limit(
    other: RacerName,
    duplicates: list[int],
    expected: int,
) -> None:
    """Fails today: he takes the highest duplicate (6, or 5 with a +1 modifier)."""
    engine = scrying_pool_engine("MrDiceGuy", other=other)

    assert pick_duplicate(engine, duplicates) == expected


@pytest.mark.parametrize(
    ("other", "duplicates", "expected"),
    [
        ("Centaur", [6], 6),
        ("Coach", [6, 5], 6),
        ("Gunk", [6, 3], 6),
    ],
)
def test_mr_dice_guy_keeps_todays_pick_when_the_pool_bans_nothing_usable(
    other: RacerName,
    duplicates: list[int],
    expected: int,
) -> None:
    """Passes today: everything banned falls back to all options; Gunk's -1 makes 6 total 5."""
    engine = scrying_pool_engine("MrDiceGuy", other=other)

    assert pick_duplicate(engine, duplicates) == expected


def test_mr_dice_guy_without_the_pool_takes_the_highest_duplicate() -> None:
    """Passes today: regression guard."""
    engine = build_engine("MrDiceGuy", other="Coach")

    assert pick_duplicate(engine, [5, 3]) == 5


# --- Scrying Pool: Magician --------------------------------------------------


@pytest.mark.parametrize(
    ("other", "rolled", "final"),
    [("Centaur", 6, 6), ("Coach", 5, 6)],
)
def test_magician_rerolls_a_roll_that_reaches_the_pool_limit(
    other: RacerName,
    rolled: D6Values,
    final: int,
) -> None:
    """Fails today: a 6 (or a 5 under +1) is kept as a high roll."""
    engine = scrying_pool_engine("Magician", other=other)

    assert rerolls(engine, AbilityMagicalReroll, rolled=rolled, final=final)


@pytest.mark.parametrize(
    ("other", "powers", "rolled", "final"),
    [
        ("Centaur", (), 5, 5),
        ("Gunk", (), 6, 5),
        ("Coach", ("Skipper",), 1, 2),
    ],
)
def test_magician_keeps_a_roll_whose_total_stays_below_the_pool_limit(
    other: RacerName,
    powers: tuple[RacerName, ...],
    rolled: D6Values,
    final: int,
) -> None:
    """Passes today: totals under 6 follow the usual rules (keep 5, keep 6 under -1, keep a wished 1)."""
    engine = scrying_pool_engine("Magician", other=other, powers=powers)

    assert not rerolls(engine, AbilityMagicalReroll, rolled=rolled, final=final)


def test_magician_without_the_pool_keeps_a_six() -> None:
    """Passes today: regression guard."""
    engine = build_engine("Magician")

    assert not rerolls(engine, AbilityMagicalReroll, rolled=6)


# --- Scrying Pool: Dicemonger ------------------------------------------------


@pytest.mark.parametrize(
    ("other", "rolled", "final"),
    [("Centaur", 6, 6), ("Coach", 5, 6)],
)
def test_dicemonger_reroll_is_offered_for_a_total_at_the_pool_limit(
    other: RacerName,
    rolled: D6Values,
    final: int,
) -> None:
    """Fails today: 6 (or 5 under +1) is in the default preferred {4, 5, 6}."""
    engine = scrying_pool_engine("Dicemonger", other=other)

    assert rerolls(engine, DicemongerRerollAction, rolled=rolled, final=final)


@pytest.mark.parametrize(
    ("other", "rolled", "final", "expected"),
    [
        ("Centaur", 5, 5, False),
        ("Centaur", 3, 3, True),
        ("Coach", 4, 5, False),
        ("Gunk", 6, 5, False),
    ],
)
def test_dicemonger_follows_todays_logic_below_the_pool_limit(
    other: RacerName,
    rolled: D6Values,
    final: int,
    expected: bool,
) -> None:
    """Passes today: totals under 6 follow the preferred set {4, 5, 6}."""
    engine = scrying_pool_engine("Dicemonger", other=other)

    result = rerolls(engine, DicemongerRerollAction, rolled=rolled, final=final)

    assert result is expected


def test_dicemonger_without_the_pool_keeps_a_six() -> None:
    """Passes today: regression guard."""
    engine = build_engine("Dicemonger")

    assert not rerolls(engine, DicemongerRerollAction, rolled=6)


# --- Party Pooper: present ---------------------------------------------------


def test_cheatah_never_sets_a_six_while_a_party_pooper_is_racing() -> None:
    """Fails today: Cheatah's mix includes the 6."""
    engine = build_engine("Cheatah", other="PartyPooper")

    support = cheatah_support(engine)

    assert support
    assert 6 not in support


def test_cheatah_never_sets_a_six_with_the_party_pooper_power_himself() -> None:
    """Fails today: his own power rerolls the 6 too."""
    engine = build_engine("Cheatah", powers=["PartyPooper"])

    support = cheatah_support(engine)

    assert support
    assert 6 not in support


def test_mr_dice_guy_skips_a_six_duplicate_while_a_party_pooper_is_racing() -> None:
    """Fails today: he takes the highest duplicate, the 6."""
    engine = build_engine("MrDiceGuy", other="PartyPooper")

    assert pick_duplicate(engine, [6, 3]) == 3


def test_mr_dice_guy_takes_a_lone_six_duplicate_while_a_party_pooper_is_racing() -> (
    None
):
    """Passes today: with every option banned nothing is excluded."""
    engine = build_engine("MrDiceGuy", other="PartyPooper")

    assert pick_duplicate(engine, [6]) == 6


@pytest.mark.parametrize(
    ("name", "kind"),
    [("Magician", AbilityMagicalReroll), ("Dicemonger", DicemongerRerollAction)],
)
def test_reroll_racers_reroll_a_six_while_a_party_pooper_is_racing(
    name: RacerName,
    kind: type[AbilityMagicalReroll] | type[DicemongerRerollAction],
) -> None:
    """Fails today: a 6 is in the preferred {4, 5, 6}."""
    engine = build_engine(name, other="PartyPooper")

    assert rerolls(engine, kind, rolled=6)


@pytest.mark.parametrize(
    ("name", "kind", "rolled", "expected"),
    [
        ("Magician", AbilityMagicalReroll, 5, False),
        ("Magician", AbilityMagicalReroll, 1, True),
        ("Dicemonger", DicemongerRerollAction, 5, False),
        ("Dicemonger", DicemongerRerollAction, 1, True),
    ],
)
def test_reroll_racers_keep_todays_rules_for_other_values_with_a_party_pooper(
    name: RacerName,
    kind: type[AbilityMagicalReroll] | type[DicemongerRerollAction],
    rolled: D6Values,
    expected: bool,
) -> None:
    """Passes today: only the 6 is affected."""
    engine = build_engine(name, other="PartyPooper")

    assert rerolls(engine, kind, rolled=rolled) is expected


# --- Party Pooper: gone ------------------------------------------------------


@pytest.mark.parametrize("depart", DEPARTURES)
def test_cheatah_may_set_a_six_again_once_the_party_pooper_is_gone(
    depart: Departure,
) -> None:
    """Passes today: guard that the ban is derived from live state."""
    engine = build_engine("Cheatah", other="PartyPooper")
    depart(engine)

    assert cheatah_support(engine) == PLAIN_SUPPORT


@pytest.mark.parametrize("depart", DEPARTURES)
def test_mr_dice_guy_takes_the_six_again_once_the_party_pooper_is_gone(
    depart: Departure,
) -> None:
    """Passes today: guard that the ban is derived from live state."""
    engine = build_engine("MrDiceGuy", other="PartyPooper")
    depart(engine)

    assert pick_duplicate(engine, [6, 3]) == 6


@pytest.mark.parametrize("depart", DEPARTURES)
@pytest.mark.parametrize(
    ("name", "kind"),
    [("Magician", AbilityMagicalReroll), ("Dicemonger", DicemongerRerollAction)],
)
def test_reroll_racers_keep_a_six_again_once_the_party_pooper_is_gone(
    name: RacerName,
    kind: type[AbilityMagicalReroll] | type[DicemongerRerollAction],
    depart: Departure,
) -> None:
    """Passes today: guard that the ban is derived from live state."""
    engine = build_engine(name, other="PartyPooper")
    depart(engine)

    assert not rerolls(engine, kind, rolled=6)
