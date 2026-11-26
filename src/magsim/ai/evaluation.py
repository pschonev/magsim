from functools import cache
from statistics import median

from magsim.core.abilities import CopyAbilityProtocol
from magsim.core.state import ActiveRacerState, is_active
from magsim.core.types import D6VAlueSet, RacerName
from magsim.engine.board import MoveDeltaTile
from magsim.engine.game_engine import GameEngine
from magsim.engine.twist import SCRYING_POOL_LIMIT, ScryingPoolRule
from magsim.racers import get_all_racer_stats
from magsim.racers.mush import MushGlobsterMashAbility
from magsim.racers.party_pooper import (
    REJECTED_VALUE,
    PartyPooperNoiseComplaintAbility,
)

ALL_FACES = (1, 2, 3, 4, 5, 6)
PARTY_POOPER_FACES = frozenset({REJECTED_VALUE})
DEFAULT_PREFERRED_DICE: D6VAlueSet = frozenset({4, 5, 6})
MUSH_DRAW_FACES = frozenset({1, 2})
MAX_DRAWS_WANTED = 3
MIN_DRAWS_WANTED = 2
CLOSE_TO_FINISH_TILES = 10


def scrying_pool_faces(engine: GameEngine, racer: ActiveRacerState) -> frozenset[int]:
    """Faces whose main-move total reaches the Scrying Pool limit, if the racer carries the rule."""
    if not any(isinstance(m, ScryingPoolRule) for m in racer.modifiers):
        return frozenset()
    mods = get_current_modifiers(engine, racer.idx)
    return frozenset(f for f in ALL_FACES if f + mods >= SCRYING_POOL_LIMIT)


def party_pooper_faces(engine: GameEngine) -> frozenset[int]:
    """The rejected face while any active racer holds Party Pooper's power."""
    for r in engine.state.racers:
        if is_active(r) and any(
            isinstance(a, PartyPooperNoiseComplaintAbility) for a in r.active_abilities
        ):
            return PARTY_POOPER_FACES
    return frozenset()


def banned_faces(engine: GameEngine, racer: ActiveRacerState) -> frozenset[int]:
    """Faces the racer must never see rolled or set: ability avoidance, Scrying Pool totals, Party Pooper."""
    avoided = frozenset().union(*(a.avoid_dice for a in racer.active_abilities))
    return (
        avoided | scrying_pool_faces(engine, racer) | party_pooper_faces(engine)
    )


def soft_wishes(racer: ActiveRacerState) -> frozenset[int] | None:
    """Intersection of the non-default preferred dice of the racer's abilities, if any."""
    wishes = [
        a.preferred_dice
        for a in racer.active_abilities
        if a.preferred_dice != DEFAULT_PREFERRED_DICE
    ]
    if not wishes:
        return None
    return frozenset.intersection(*wishes) or None


@cache
def median_win_rate() -> float:
    """Median win rate over all racers in the bundled stats."""
    return median(stat.winrate for stat in get_all_racer_stats().values())


def is_unsatisfied_with_draws(drawn: list[RacerName]) -> bool:
    """Mush wants more draws while he has few, or only weak ones."""
    if len(drawn) < MIN_DRAWS_WANTED:
        return True
    if len(drawn) >= MAX_DRAWS_WANTED:
        return False
    stats = get_all_racer_stats()
    return max(stats[name].winrate for name in drawn) < median_win_rate()


def draw_faces(engine: GameEngine, racer: ActiveRacerState) -> frozenset[int]:
    """Faces that trigger a Mush draw, when the racer has Mush's power and wants a draw."""
    mush = next(
        (a for a in racer.active_abilities if isinstance(a, MushGlobsterMashAbility)),
        None,
    )
    if mush is None:
        return frozenset()
    if racer.position >= engine.state.board.length - CLOSE_TO_FINISH_TILES:
        return frozenset()
    if not is_unsatisfied_with_draws(mush.copied_racers):
        return frozenset()
    return MUSH_DRAW_FACES


def wished_faces(engine: GameEngine, racer: ActiveRacerState) -> frozenset[int]:
    """Faces the racer would like to roll: draw faces narrowed by soft wishes, else soft wishes."""
    soft = soft_wishes(racer)
    draws = draw_faces(engine, racer)
    if not draws:
        return soft or frozenset()
    if soft is None:
        return draws
    return draws & soft or draws


def keeps_roll_for_draw(engine: GameEngine, racer: ActiveRacerState, landing: int) -> bool:
    """True when the racer wants a Mush draw and skipping the roll would not land on a benefit tile."""
    return bool(draw_faces(engine, racer)) and get_benefit_at(engine, landing) is None


def get_benefit_at(engine: GameEngine, pos: int) -> str | None:
    """
    Returns the display name of the feature making this position excellent.
    e.g. "Goal", "Victory Point Tile", "Forward Boost (+3)".
    """
    board_len = engine.state.board.length
    if pos >= board_len:
        return "Goal"

    modifiers = engine.state.board.get_modifiers_at(pos)

    # VP is best
    if vp := next((m for m in modifiers if m.name == "VictoryPointTile"), None):
        return vp.display_name

    # Forward Boost is excellent
    if boost := next(
        (m for m in modifiers if isinstance(m, MoveDeltaTile) and m.delta > 0),
        None,
    ):
        return boost.display_name

    return None


def get_hazard_at(engine: GameEngine, pos: int) -> str | None:
    """
    Returns the display name of the feature making this position hazardous.
    Checks for Board Modifiers AND Active Racers with dangerous abilities.
    """
    board_len = engine.state.board.length
    if pos >= board_len:
        return None

    # 1. Board Hazards (Trip Tiles, Backward Boosts)
    modifiers = engine.state.board.get_modifiers_at(pos)

    if trip := next((m for m in modifiers if m.name == "TripTile"), None):
        return trip.display_name

    if back := next(
        (m for m in modifiers if isinstance(m, MoveDeltaTile) and m.delta < 0),
        None,
    ):
        return back.display_name

    # 2. Racer Hazards
    for r in engine.get_active_racers():
        if "BabaYagaTrip" in r.abilities and r.position == pos:
            return f"{r.name} (Baba Yaga Power)"
        if "HotelMonopolize" in r.abilities and r.position == pos:
            return f"{r.name} (Hotel Power)"
        if "StunnerStopTraffic" in r.abilities and abs(r.position - pos) <= 1:
            return f"{r.name} (Stunner Power)"
        if "NullVoid" in r.abilities and r.position < pos:
            return f"{r.name} (Null Power)"

    return None


def get_current_modifiers(engine: GameEngine, racer_idx: int) -> int:
    """
    Returns the total static modifier for a main move.
    Checks for Gunk's global slow and Coach's local boost via ABILITIES.
    """
    if (me := engine.get_active_racer(racer_idx)) is None:
        return 0

    total_mod = 0

    # 1. Gunk Effect (Global -1)
    # Check if ANY active opponent has "GunkSlow"
    is_gunked = any(
        "GunkSlime" in r.abilities and r.active
        for r in engine.state.racers
        if r.idx != racer_idx
    )
    if is_gunked:
        total_mod -= 1

    # 2. Coach Effect (Local +1)
    # Check if ANY racer on my tile (including myself!) has "CoachAura"
    # (Coach buffs himself too, so this logic holds)
    is_coached = any(
        "CoachAura" in r.abilities for r in engine.get_racers_at_position(me.position)
    )
    if is_coached:
        total_mod += 1

    return total_mod


def is_turn_between(start_idx: int, end_idx: int, target_idx: int) -> bool:
    """
    Returns True if target_idx's turn occurs strictly after start_idx
    and strictly before end_idx in a clockwise turn order.
    """
    if start_idx == end_idx:
        return False  # No one is between identical start/end

    if start_idx < end_idx:
        # Normal Case: [Start ... Target ... End]
        return start_idx < target_idx < end_idx

    # Wrap Case: [Target ... End ... Start] OR [End ... Start ... Target]
    return target_idx > start_idx or target_idx < end_idx


def get_effective_racer_name(racer: ActiveRacerState) -> RacerName:
    """
    Returns the true identity of a racer.
    If the racer is Egg, Twin, or Copycat, this returns the name of the racer
    they are currently copying. Otherwise, returns their own name.
    """
    for ability in racer.active_abilities:
        if (
            isinstance(ability, CopyAbilityProtocol)
            and ability.copied_racer is not None
        ):
            return ability.copied_racer

    return racer.name
