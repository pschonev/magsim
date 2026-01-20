from __future__ import annotations

from typing import TYPE_CHECKING

from magical_athlete_simulator.core.events import (
    AbilityTriggeredEvent,
    ExecuteMainMoveEvent,
    MoveDistanceQuery,
    PerformMainRollEvent,
    Phase,
    ResolveMainMoveEvent,
    RollModificationWindowEvent,
    RollResultEvent,
)
from magical_athlete_simulator.core.mixins import RollModificationMixin
from magical_athlete_simulator.engine.movement import push_move

if TYPE_CHECKING:
    from magical_athlete_simulator.core.types import Source
    from magical_athlete_simulator.engine.game_engine import GameEngine


def handle_perform_main_roll(engine: GameEngine, event: PerformMainRollEvent) -> None:
    racer = engine.get_racer(event.target_racer_idx)
    if racer.main_move_consumed:
        engine.log_info(f"Skipping roll because {racer.repr} already used main move.")
        return

    engine.state.roll_state.serial_id += 1
    current_serial = engine.state.roll_state.serial_id

    if racer.roll_override is not None:
        base = racer.roll_override
        engine.state.roll_state.dice_value = None  # Not a dice roll
        engine.state.roll_state.can_reroll = False
        racer.roll_override = None  # Consume it
    else:
        base = engine.rng.randint(1, 6)
        engine.state.roll_state.dice_value = base
        engine.state.roll_state.can_reroll = True

    engine.state.roll_state.base_value = base

    query = MoveDistanceQuery(event.target_racer_idx, base)

    # Apply ALL modifiers attached to this racer
    roll_event_triggered_events: list[AbilityTriggeredEvent] = []
    for mod in engine.get_racer(event.target_racer_idx).modifiers:
        if isinstance(mod, RollModificationMixin):
            roll_event_triggered_events.extend(
                mod.modify_roll(
                    query,
                    mod.owner_idx,
                    engine,
                    rolling_racer_idx=event.target_racer_idx,
                ),
            )

    final = query.final_value
    engine.state.roll_state.base_value = base
    engine.state.roll_state.final_value = final

    # Logging
    if query.modifier_sources:
        parts = [f"{name}:{delta:+d}" for (name, delta) in query.modifier_sources]
        mods_str = ", ".join(parts)
        total_delta = sum(delta for _, delta in query.modifier_sources)
        engine.log_info(
            f"Dice Roll: {base} (Mods: {total_delta} [{mods_str}]) -> Result: {final}",
        )
    else:
        engine.log_info(f"Dice Roll: {base} (Mods: 0) -> Result: {final}")

    # 3. Fire the 'Window' event. Listeners can call trigger_reroll() here.
    engine.push_event(
        RollModificationWindowEvent(
            target_racer_idx=event.target_racer_idx,
            current_roll_val=final,
            roll_serial=current_serial,
            responsible_racer_idx=event.target_racer_idx,
            source=event.source,
        ),
    )

    # 4. Schedule the resolution.
    engine.push_event(
        ResolveMainMoveEvent(
            target_racer_idx=event.target_racer_idx,
            roll_serial=current_serial,
            responsible_racer_idx=event.responsible_racer_idx,
            source=event.source,
            roll_event_triggered_events=roll_event_triggered_events,
        ),
    )


def resolve_main_move(engine: GameEngine, event: ResolveMainMoveEvent):
    """
    Resolves the roll window. It announces the result, fires modifier events,
    then schedules the physical execution.
    """
    if event.roll_serial != engine.state.roll_state.serial_id:
        engine.log_debug("Ignoring stale roll resolution (Re-roll occurred).")
        return

    # 1. Notify listeners (RollResultEvent) - Phase 20 (MAIN_ACT)
    engine.push_event(
        RollResultEvent(
            target_racer_idx=event.target_racer_idx,
            responsible_racer_idx=event.responsible_racer_idx,
            source=event.source,
            dice_value=engine.state.roll_state.dice_value,
            base_value=engine.state.roll_state.base_value,
            final_value=engine.state.roll_state.final_value,
            phase=Phase.MAIN_ACT,
        ),
    )

    # 2. Emit ability triggers generated during roll calculation (e.g. +1 modifiers)
    # RESTORED: These fire now, immediately after the result is announced,
    # restoring the original timing behavior.
    for ability_triggered_event in event.roll_event_triggered_events:
        engine.push_event(ability_triggered_event)

    # 3. Schedule the physical move - Phase 21 (MOVE_EXEC)
    # This delay allows Inchworm/Lackey (listening to step 1) to intervene
    # before step 3 actually runs.
    engine.push_event(
        ExecuteMainMoveEvent(
            target_racer_idx=event.target_racer_idx,
            responsible_racer_idx=event.responsible_racer_idx,
            source=event.source,
            roll_serial=event.roll_serial,
            # We don't need to pass the events forward anymore, as we emitted them above.
            roll_event_triggered_events=[],
        ),
    )


def handle_execute_main_move(engine: GameEngine, event: ExecuteMainMoveEvent):
    """
    Actually performs the move if it hasn't been cancelled.
    """
    racer = engine.get_racer(event.target_racer_idx)

    # Check if Inchworm cancelled this move in the previous event step
    if racer.main_move_consumed:
        engine.log_info(
            f"Skipped execution: {racer.repr} main move was consumed/cancelled.",
        )
        return

    dist = engine.state.roll_state.final_value

    if dist > 0:
        push_move(
            engine=engine,
            moved_racer_idx=event.target_racer_idx,
            distance=dist,
            phase=Phase.MOVE_EXEC,
            source=event.source,
            responsible_racer_idx=event.responsible_racer_idx,
            emit_ability_triggered="never",
        )


def trigger_reroll(engine: GameEngine, source_idx: int, source: Source):
    """Cancels the current roll resolution and schedules a new roll immediately."""
    engine.log_info(
        f"RE-ROLL TRIGGERED by {engine.get_racer(source_idx).name} ({source})",
    )
    engine.state.roll_state.serial_id += 1

    engine.push_event(
        PerformMainRollEvent(
            target_racer_idx=engine.state.current_racer_idx,
            phase=Phase.ROLL_DICE,
            source=source,
            responsible_racer_idx=engine.state.current_racer_idx,
        ),
    )
