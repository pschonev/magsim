from magsim.core.abilities import CopyAbilityProtocol
from magsim.core.state import ActiveRacerState
from magsim.core.types import RacerName
from magsim.engine.board import MoveDeltaTile
from magsim.engine.game_engine import GameEngine

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

    # 2. Racer Hazards (Baba Yaga Ability)
    # We check if ANY racer on this tile has the 'BabaYagaTrip' ability.
    racers = engine.get_racers_at_position(pos)
    for r in racers:
        if "BabaYagaTrip" in r.abilities:
            return f"{r.name} (Baba Yaga Power)"

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
        "CoachAura" in r.abilities
        for r in engine.get_racers_at_position(me.position)
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
        if isinstance(ability, CopyAbilityProtocol) and ability.copied_racer is not None:
            return ability.copied_racer
    
    return racer.name
