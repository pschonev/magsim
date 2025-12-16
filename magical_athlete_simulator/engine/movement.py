from typing import TYPE_CHECKING

from magical_athlete_simulator.core.events import (
    MoveCmdEvent,
    PassingEvent,
    Phase,
    PostMoveEvent,
    PostWarpEvent,
    PreMoveEvent,
    PreWarpEvent,
    WarpCmdEvent,
)
from magical_athlete_simulator.engine.flow import check_finish

if TYPE_CHECKING:
    from magical_athlete_simulator.engine.game_engine import GameEngine


def handle_move_cmd(engine: GameEngine, evt: MoveCmdEvent):
    racer = engine.get_racer(evt.racer_idx)
    if racer.finished:
        return

    # Moving 0 is not moving at all
    if evt.distance == 0:
        return

    start = racer.position
    distance = evt.distance

    # 1. Departure hook
    engine.publish_to_subscribers(
        PreMoveEvent(
            racer_idx=evt.racer_idx,
            start_tile=start,
            distance=distance,
            source=evt.source,
            phase=evt.phase,
        ),
    )

    # 2. Resolve spatial modifiers (Huge Baby etc.)
    intended = start + distance
    end = engine.state.board.resolve_position(
        intended,
        evt.racer_idx,
        engine,
    )  # [file:1]

    # If you get fully blocked back to your start, treat as “no movement”
    if end == start:
        return

    engine.log_info(f"Move: {racer.repr} {start}->{end} ({evt.source})")  # [file:1]

    # 3. Passing events (unchanged from your current logic)
    if distance > 0:
        for tile in range(start + 1, min(end, engine.state.board.length)):
            if tile < end:
                victims = [
                    r
                    for r in engine.state.racers
                    if r.position == tile and r.idx != racer.idx and not r.finished
                ]
                for v in victims:
                    engine.push_event(
                        PassingEvent(racer.idx, v.idx, tile),
                        phase=Phase.MOVE_EXEC,
                    )  # [file:1]

    # 4. Commit position
    racer.position = end

    # Finish check as in your current engine
    if check_finish(engine, racer):  # may log finish + mark race_over, etc. [file:1]
        return

    # 5. Board “on land” hooks (Trip, VP, MoveDelta, etc.)
    engine.state.board.trigger_on_land(end, racer.idx, evt.phase, engine)  # [file:1]

    # 6. Arrival hook
    engine.publish_to_subscribers(
        PostMoveEvent(
            racer_idx=evt.racer_idx,
            start_tile=start,
            end_tile=end,
            source=evt.source,
            phase=evt.phase,
        ),
    )


def handle_warp_cmd(engine: GameEngine, evt: WarpCmdEvent):
    racer = engine.get_racer(evt.racer_idx)
    if racer.finished:
        return

    start = racer.position

    # Warping to the same tile is not movement
    if start == evt.target_tile:
        return

    # 1. Departure hook
    engine.publish_to_subscribers(
        PreWarpEvent(
            racer_idx=evt.racer_idx,
            start_tile=start,
            target_tile=evt.target_tile,
            source=evt.source,
            phase=evt.phase,
        ),
    )

    # 2. Resolve spatial modifiers on the target
    resolved = engine.state.board.resolve_position(
        evt.target_tile,
        evt.racer_idx,
        engine,
    )  # [file:1]

    if resolved == start:
        return

    engine.log_info(f"Warp: {racer.repr} -> {resolved} ({evt.source})")  # [file:1]
    racer.position = resolved

    if check_finish(engine, racer):
        return

    # 3. Board hooks on landing
    engine.state.board.trigger_on_land(
        resolved,
        racer.idx,
        evt.phase,
        engine,
    )  # [file:1]

    # 4. Arrival hook
    engine.publish_to_subscribers(
        PostWarpEvent(
            racer_idx=evt.racer_idx,
            start_tile=start,
            end_tile=resolved,
            source=evt.source,
            phase=evt.phase,
        ),
    )


def push_move(
    engine: GameEngine,
    racer_idx: int,
    distance: int,
    source: str,
    phase: int,
):
    if distance == 0:
        return
    # Pass phase into the event data
    engine.push_event(MoveCmdEvent(racer_idx, distance, source, phase), phase=phase)


def push_warp(engine: GameEngine, racer_idx: int, target: int, source: str, phase: int):
    if engine.get_racer(racer_idx).position == target:
        return
    # Pass phase into the event data
    engine.push_event(WarpCmdEvent(racer_idx, target, source, phase), phase=phase)
