from __future__ import annotations

from typing import TYPE_CHECKING, cast

from magical_athlete_simulator.core.events import (
    AbilityTriggeredEvent,
    BaseValueModificationEvent,
    ExecuteMainMoveEvent,
    MoveDistanceQuery,
    PerformMainRollEvent,
    Phase,
    ResolveMainMoveEvent,
    RollData,
    RollModificationWindowEvent,
    RollResultEvent,
)
from magical_athlete_simulator.core.mixins import RollModificationMixin
from magical_athlete_simulator.engine.movement import push_move

if TYPE_CHECKING:
    from magical_athlete_simulator.core.types import D6Values, Source
    from magical_athlete_simulator.engine.game_engine import GameEngine


def log_roll_breakdown(
    engine: GameEngine,
    base_value: int,
    modifier_sources: list[tuple[str, int]],
    final_value: int,
    *,
    is_override: bool = False,
) -> None:
    """
    Logs the roll breakdown in a standardized format.
    Can be used by the main roll handler or abilities that override values (e.g. Alchemist).
    """
    roll_type = "Base Value Override" if is_override else "Dice Roll"

    if modifier_sources:
        parts = [f"{name}({delta:+d})" for name, delta in modifier_sources]
        mods_str = " + ".join(parts)
        total_delta = sum(delta for _, delta in modifier_sources)
        engine.log_info(
            f"{roll_type}: {base_value} | Mods: {mods_str} = {total_delta:+d} -> Result: {final_value}",
        )
    else:
        engine.log_info(f"{roll_type}: {base_value} | Mods: 0 -> Result: {final_value}")


def report_base_value_change(
    engine: GameEngine,
    racer_idx: int,
    old_value: float,
    new_value: int,
    source: Source,
) -> None:
    """Helper to emit telemetry event for base value manipulation."""
    engine.push_event(
        BaseValueModificationEvent(
            target_racer_idx=racer_idx,
            responsible_racer_idx=racer_idx,  # Usually self
            old_value=old_value,
            new_value=new_value,
            source=source,
            phase=Phase.ROLL_WINDOW,
        ),
    )


def handle_perform_main_roll(engine: GameEngine, event: PerformMainRollEvent) -> None:
    racer = engine.get_racer(event.target_racer_idx)
    if racer.tripped:
        engine.log_info(f"Skipping roll because {racer.repr} is tripped.")
        racer.main_move_consumed = True
        return

    if racer.main_move_consumed:
        engine.log_info(f"Skipping roll because {racer.repr} already used main move.")
        return

    engine.state.roll_state.serial_id += 1
    current_serial = engine.state.roll_state.serial_id

    if racer.roll_override is not None:
        source, base = racer.roll_override
        engine.state.roll_state.dice_value = None  # Not a dice roll
        racer.can_reroll = False

        report_base_value_change(
            engine,
            racer.idx,
            old_value=3.5,
            new_value=base,
            source=source,
        )

        racer.roll_override = None  # Consume it
    else:
        base = cast("D6Values", engine.rng.randint(1, 6))
        engine.state.roll_state.dice_value = base
        racer.can_reroll = True

    engine.state.roll_state.base_value = base

    query = MoveDistanceQuery(event.target_racer_idx, base)

    # Apply ALL modifiers attached to this racer
    roll_event_triggered_events: list[AbilityTriggeredEvent] = []

    # Capture Breakdown
    modifier_breakdown: list[RollData] = []

    for mod in engine.get_racer(event.target_racer_idx).modifiers:
        if isinstance(mod, RollModificationMixin):
            val_before = query.final_value

            roll_event_triggered_events.extend(
                mod.modify_roll(
                    query,
                    mod.owner_idx,
                    engine,
                    rolling_racer_idx=event.target_racer_idx,
                ),
            )

            val_after = query.final_value
            delta = val_after - val_before

            if delta != 0 and mod.owner_idx is not None:
                modifier_breakdown.append(
                    RollData(rolling_racer_idx=mod.owner_idx, delta=delta),
                )

    final = query.final_value
    engine.state.roll_state.final_value = final

    log_roll_breakdown(
        engine,
        base_value=base,
        modifier_sources=query.modifier_sources,
        final_value=final,
        is_override=False,
    )

    # Fire Window
    engine.push_event(
        RollModificationWindowEvent(
            target_racer_idx=event.target_racer_idx,
            current_roll_val=final,
            roll_serial=current_serial,
            responsible_racer_idx=event.target_racer_idx,
            source=event.source,
            modifier_breakdown=query.modifier_sources,
        ),
    )

    # Fire Resolution with Breakdown
    engine.push_event(
        ResolveMainMoveEvent(
            target_racer_idx=event.target_racer_idx,
            roll_serial=current_serial,
            responsible_racer_idx=event.responsible_racer_idx,
            source=event.source,
            roll_event_triggered_events=roll_event_triggered_events,
            modifier_breakdown=modifier_breakdown,  # Pass it
        ),
    )


def resolve_main_move(engine: GameEngine, event: ResolveMainMoveEvent) -> None:
    """Resolves the roll window."""
    if event.roll_serial != engine.state.roll_state.serial_id:
        engine.log_debug("Ignoring stale roll resolution (Re-roll occurred).")
        return

    # Notify listeners (RollResultEvent) - Phase 20 (MAIN_ACT)
    engine.push_event(
        RollResultEvent(
            target_racer_idx=event.target_racer_idx,
            responsible_racer_idx=event.responsible_racer_idx,
            source=event.source,
            dice_value=engine.state.roll_state.dice_value,
            base_value=engine.state.roll_state.base_value,
            final_value=engine.state.roll_state.final_value,
            phase=Phase.MAIN_ACT,
            modifier_breakdown=event.modifier_breakdown,  # Pass it
        ),
    )

    # 1. Fire triggered events
    for ability_triggered_event in event.roll_event_triggered_events:
        engine.push_event(ability_triggered_event)

    # 2. Schedule Execution
    engine.push_event(
        ExecuteMainMoveEvent(
            target_racer_idx=event.target_racer_idx,
            responsible_racer_idx=event.responsible_racer_idx,
            source=event.source,
            roll_serial=event.roll_serial,
        ),
    )


def handle_execute_main_move(engine: GameEngine, event: ExecuteMainMoveEvent) -> None:
    """Actually performs the move if it hasn't been cancelled."""
    racer = engine.get_racer(event.target_racer_idx)

    if racer.main_move_consumed:
        engine.log_debug(
            f"Skipping execution: {racer.repr} main move was consumed/cancelled.",
        )
        return

    dist = engine.state.roll_state.final_value
    if dist > 0:
        push_move(
            engine=engine,
            moved_racer_idx=event.target_racer_idx,
            distance=dist,
            phase=Phase.MOVE_EXEC,
            source="System",
            responsible_racer_idx=None,
            emit_ability_triggered="never",
            is_main_move=True,
        )


def trigger_reroll(engine: GameEngine, source_idx: int, source: Source) -> None:
    """
    Cancels the current roll resolution and schedules a new roll immediately.
    """
    engine.log_info(
        f"RE-ROLL TRIGGERED by {engine.get_racer(source_idx).repr} ({source})",
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
