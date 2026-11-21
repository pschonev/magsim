from __future__ import annotations

from typing import TYPE_CHECKING

from magsim.engine.flow import rank_reward

if TYPE_CHECKING:
    from magsim.engine.game_engine import GameEngine

FINALISTS = 2


def start_second_race(engine: GameEngine) -> bool:
    """Restarts the game as race two once a finished race one carried the Season Finale."""
    state = engine.state
    if state.race_active or not state.finale_pending or state.race_number != 1:
        return False
    state.finale_pending = False

    finalists = sorted(
        (r for r in state.racers if r.finished),
        key=lambda r: r.finish_position or 0,
    )
    if len(finalists) != FINALISTS:
        return False

    for racer in state.racers:
        if racer in finalists:
            continue
        engine.clear_all_abilities(racer.idx)
        racer.modifiers.clear()
        racer.sidelined = True

    for racer in finalists:
        assert racer.finish_position is not None
        racer.victory_points -= rank_reward(state, racer.finish_position)
        racer.finish_position = None
        racer.position = state.board.second_turn
        racer.tripped = False
        racer.tripping_racers = []
        racer.main_move_consumed = False
        racer.roll_override = None
        racer.can_reroll = True
        racer.modifiers.clear()

    state.race_number = 2
    engine.setup_racers()

    first = finalists[0]
    state.queue.clear()
    state.history.clear()
    engine.loop_detector.reset_for_turn()
    state.next_turn_override = None
    state.current_racer_idx = first.idx
    state.race_active = True
    engine.log_info(
        f"=== SEASON FINALE: race two between {finalists[0].repr} and {finalists[1].repr} ===",
    )
    return True
