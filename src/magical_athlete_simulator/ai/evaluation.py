from magical_athlete_simulator.engine.board import MoveDeltaTile
from magical_athlete_simulator.engine.game_engine import GameEngine


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
    e.g. "Baba Yaga", "Trip Tile", "Backward Boost (-2)".
    """
    if pos >= engine.state.board.length:
        return None

    modifiers = engine.state.board.get_modifiers_at(pos)
    racers = engine.get_racers_at_position(pos)

    # Trip Sources
    if baba := next((r for r in racers if r.name == "BabaYaga"), None):
        return baba.repr  # "Baba Yaga (P2)"

    if trip := next((m for m in modifiers if m.name == "TripTile"), None):
        return trip.display_name

    # Backward Movement
    if back := next(
        (m for m in modifiers if isinstance(m, MoveDeltaTile) and m.delta < 0),
        None,
    ):
        return back.display_name

    return None


def get_current_modifiers(engine: GameEngine, racer_idx: int) -> int:
    """Returns the total static modifier (Gunk, Coach, etc.) for a main move."""
    if (me := engine.get_active_racer(racer_idx)) is None:
        return 0

    # 1. Gunk (-1 if opponent Gunk is active)
    mods = (
        -1
        if any(
            r.name == "Gunk" and r.active
            for r in engine.state.racers
            if r.idx != racer_idx
        )
        else 0
    )

    # 2. Coach (+1 if on Coach's tile)
    return (
        mods + 1
        if any(r.name == "Coach" for r in engine.get_racers_at_position(me.position))
        else mods
    )


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
