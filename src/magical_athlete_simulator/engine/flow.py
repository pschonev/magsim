from __future__ import annotations

from typing import TYPE_CHECKING

from magical_athlete_simulator.core.events import Phase, RacerFinishedEvent
from magical_athlete_simulator.core.state import is_active

if TYPE_CHECKING:
    from magical_athlete_simulator.core.state import ActiveRacerState, RacerState
    from magical_athlete_simulator.engine.game_engine import GameEngine


def log_final_standings(engine: GameEngine):
    if not engine.verbose:
        return
    engine.log_info(f"{'':>15}=== FINAL STANDINGS ===")
    for racer in sorted(
        engine.state.racers,
        key=lambda r: r.finish_position if r.finish_position else 999,
    ):
        if racer.finish_position == 1:
            status = f"Rank {racer.finish_position} 🏆"
        elif racer.finish_position == 2:
            status = f"Rank {racer.finish_position} 🥈"
        elif racer.eliminated:
            status = "💀 Eliminated"
        else:
            status = ""
        engine.log_info(
            f"{'':>1}{racer.idx}•{racer.name:<8} Pos: {racer.position if racer.position else '':<4} VP: {racer.victory_points:<4} {status}",
        )


def check_finish(engine: GameEngine, racer: RacerState) -> bool:
    """
    Checks if a racer has physically crossed the finish line.
    If so, triggers the standard finish flow.
    """
    # If already finished, do nothing (prevent double counting)
    if not is_active(racer):
        return False

    # Standard rule: Position >= Board Length
    if racer.position >= engine.state.board.length:
        mark_finished(engine, racer)
        return True

    return False


def mark_finished(
    engine: GameEngine,
    racer: RacerState | ActiveRacerState,
    rank: int | None = None,
) -> None:
    """
    Sets a racer as finished at a specific rank.
    WARNING: Does not handle collisions. If rank X is taken, it overwrites.
    Callers doing complex re-ordering must manage displacement manually.
    """
    if rank is None:
        # Default behavior: Append to next available spot
        rank = sum(1 for r in engine.state.racers if r.finished) + 1

    # Update State
    old_rank = racer.finish_position
    racer.finish_position = rank

    # Update VP
    rewards = engine.state.rules.winner_vp

    # Undo old VP if re-ranking (e.g., bumping down)
    if old_rank is not None and old_rank > 0 and old_rank <= len(rewards):
        racer.victory_points -= rewards[old_rank - 1]

    # Apply new VP
    if rank <= len(rewards):
        racer.victory_points += rewards[rank - 1]

    engine.log_info(
        f"!!! {racer.repr} FINISHED rank {rank} ({racer.victory_points} VP) !!!",
    )

    # Emit event (important for listeners)
    # Only emit if it's a new finish or a meaningful change
    if old_rank is None:
        engine.push_event(
            RacerFinishedEvent(
                target_racer_idx=racer.idx,
                finishing_position=rank,
                phase=Phase.REACTION,
                responsible_racer_idx=None,
                source="System",
            ),
        )

    # Strip abilities
    engine.clear_all_abilities(racer.idx)

    # Auto-check for race end
    check_race_over_condition(engine)


def check_race_over_condition(engine: GameEngine) -> None:
    """Standard check: If 2+ racers finished, end race.
    Also handles 'Sole Survivor' rule: if only 1 active racer remains,
    they auto-finish.
    """
    # 1. Standard Condition
    count = sum(1 for r in engine.state.racers if r.finished)
    if count >= 2:
        end_race(engine)
        return

    # 2. Sole Survivor Condition (Fix for Mouth/Elimination bugs)
    active_racers = [r for r in engine.state.racers if r.active]

    # If only 1 racer is active, they auto-finish at the next rank.
    if len(active_racers) == 1:
        survivor = active_racers[0]
        next_rank = count + 1
        engine.log_info(
            f"Last survivor {survivor.repr} auto-finishes at Rank {next_rank}",
        )
        mark_finished(engine, survivor, rank=next_rank)
        return

    # If 0 active racers (everyone finished or eliminated), force end.
    if len(active_racers) == 0:
        end_race(engine)


def end_race(engine: GameEngine) -> None:
    """Forces the race to end immediately."""
    if not engine.state.race_active:
        return

    engine.state.race_active = False
    engine.log_info("Race ended! 🏁")

    engine.state.queue.clear()
    log_final_standings(engine)
