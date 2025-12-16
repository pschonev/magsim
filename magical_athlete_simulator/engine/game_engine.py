import heapq
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from rich.logging import RichHandler

from magical_athlete_simulator.ai.smart_agent import SmartAgent
from magical_athlete_simulator.core import LOGGER_NAME
from magical_athlete_simulator.core.events import (
    AbilityTriggeredEvent,
    GameEvent,
    MoveCmdEvent,
    MoveDistanceQuery,
    PassingEvent,
    PerformRollEvent,
    PostMoveEvent,
    PostWarpEvent,
    PreMoveEvent,
    PreWarpEvent,
    RacerFinishedEvent,
    ResolveMainMoveEvent,
    RollModificationWindowEvent,
    ScheduledEvent,
    TurnStartEvent,
    WarpCmdEvent,
)
from magical_athlete_simulator.core.mixins import (
    LifecycleManagedMixin,
    RollModificationMixin,
)
from magical_athlete_simulator.core.registry import RACER_ABILITIES
from magical_athlete_simulator.core.types import AbilityName, ModifierName, Phase
from magical_athlete_simulator.engine.logging import (
    ContextFilter,
    RichMarkupFormatter,
)
from magical_athlete_simulator.racers import get_ability_classes

if TYPE_CHECKING:
    import random

    from magical_athlete_simulator.core.agent import Agent
    from magical_athlete_simulator.core.modifiers import RacerModifier
    from magical_athlete_simulator.core.state import (
        GameState,
        LogContext,
        RacerState,
    )


logger = logging.getLogger(LOGGER_NAME)

AbilityCallback = Callable[[GameEvent, int, "GameEngine"], None]


@dataclass
class Subscriber:
    callback: AbilityCallback
    owner_idx: int


@dataclass
class GameEngine:
    state: GameState
    rng: random.Random
    log_context: LogContext
    subscribers: dict[type[GameEvent], list[Subscriber]] = field(default_factory=dict)
    agents: dict[int, Agent] = field(default_factory=dict)
    logging_enabled: bool = True

    def __post_init__(self) -> None:
        """Assigns starting abilities to all racers and fires on_gain hooks."""
        if self.logging_enabled:
            rich_handler = RichHandler(markup=True, show_path=False, show_time=False)
            rich_handler.setFormatter(RichMarkupFormatter())
            rich_handler.addFilter(ContextFilter(self))
            logger.handlers.clear()
            logger.addHandler(rich_handler)
            logger.propagate = False

        # Assign starting abilities
        for racer in self.state.racers:
            initial = RACER_ABILITIES.get(racer.name, set())
            self.update_racer_abilities(racer.idx, initial)

        # Rebuild subscribers
        self._rebuild_subscribers()

        for racer in self.state.racers:
            _ = self.agents.setdefault(racer.idx, SmartAgent(self.state.board))

    def _rebuild_subscribers(self):
        """Rebuild event subscriptions from each racer's active_abilities."""
        self.subscribers.clear()
        for racer in self.state.racers:
            for ability in racer.active_abilities.values():
                ability.register(self, racer.idx)

    def get_agent(self, racer_idx: int) -> Agent:
        return self.agents[racer_idx]

    def add_racer_modifier(self, target_idx: int, modifier: RacerModifier):
        racer = self.get_racer(target_idx)
        if modifier not in racer.modifiers:
            racer.modifiers.append(modifier)
            if self.logging_enabled:
                logger.info(f"ENGINE: Added {modifier.name} to {racer.repr}")

    def remove_racer_modifier(self, target_idx: int, modifier: RacerModifier):
        racer = self.get_racer(target_idx)
        if modifier in racer.modifiers:
            racer.modifiers.remove(modifier)
            if self.logging_enabled:
                logger.info(f"ENGINE: Removed {modifier.name} from {racer.repr}")

    def subscribe(
        self,
        event_type: type[GameEvent],
        callback: AbilityCallback,
        owner_idx: int,
    ):
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(Subscriber(callback, owner_idx))

    def update_racer_abilities(self, racer_idx: int, new_abilities: set[AbilityName]):
        racer = self.get_racer(racer_idx)
        current_instances = racer.active_abilities
        old_names = set(current_instances.keys())

        removed = old_names - new_abilities
        added = new_abilities - old_names

        # 1. Handle Removed
        for name in removed:
            instance = current_instances.pop(name)

            if isinstance(instance, LifecycleManagedMixin):
                instance.__class__.on_loss(self, racer_idx)

            # Selective Unsubscribe
            for event_type in self.subscribers:
                self.subscribers[event_type] = [
                    sub
                    for sub in self.subscribers[event_type]
                    if not (
                        sub.owner_idx == racer_idx
                        and getattr(sub.callback, "__self__", None) == instance
                    )
                ]

        # 2. Handle Added
        for name in added:
            ability_cls = get_ability_classes().get(name)
            if ability_cls:
                instance = ability_cls()

                instance.register(self, racer_idx)
                current_instances[name] = instance

                if isinstance(instance, LifecycleManagedMixin):
                    instance.__class__.on_gain(self, racer_idx)

    def get_racer(self, idx: int) -> RacerState:
        return self.state.racers[idx]

    def get_racer_pos(self, idx: int) -> int:
        return self.state.racers[idx].position

    # --- Action Queuing ---

    def push_event(self, event: GameEvent, *, phase: int):
        self.state.serial += 1
        sched = ScheduledEvent(phase, 0, self.state.serial, event)
        heapq.heappush(self.state.queue, sched)

        # --- In GameEngine Class ---

    def push_move(self, racer_idx: int, distance: int, source: str, phase: int):
        if distance == 0:
            return
        # Pass phase into the event data
        self.push_event(MoveCmdEvent(racer_idx, distance, source, phase), phase=phase)

    def push_warp(self, racer_idx: int, target: int, source: str, phase: int):
        if self.get_racer(racer_idx).position == target:
            return
        # Pass phase into the event data
        self.push_event(WarpCmdEvent(racer_idx, target, source, phase), phase=phase)

    def emit_ability_trigger(
        self,
        source_idx: int | None,
        ability: AbilityName | ModifierName | str,
        log_context: str,
    ):
        self.push_event(
            AbilityTriggeredEvent(source_idx, ability, log_context),
            phase=Phase.REACTION,
        )

    def trigger_reroll(self, source_idx: int, reason: str):
        """Cancels the current roll resolution and schedules a new roll immediately."""
        logger.info(
            f"!!! RE-ROLL TRIGGERED by {self.get_racer(source_idx).name} ({reason}) !!!",
        )
        # Increment serial to kill any pending ResolveMainMove events
        self.state.roll_state.serial_id += 1

        # CHANGED: We schedule the new roll at Phase.REACTION + 1.
        # This guarantees that any AbilityTriggeredEvents (Phase 25) caused by the
        # act of triggering the reroll (e.g. Scoocher moving) are processed
        # BEFORE the dice are rolled again.
        self.push_event(
            PerformRollEvent(self.state.current_racer_idx),
            phase=Phase.REACTION + 1,
        )

    # --- Event Loop ---

    def publish_to_subscribers(self, event: GameEvent):
        if type(event) not in self.subscribers:
            return
        subs = self.subscribers[type(event)]
        curr = self.state.current_racer_idx
        count = len(self.state.racers)
        # Ordered iteration: Start from current player, go clockwise
        ordered_subs = sorted(subs, key=lambda s: (s.owner_idx - curr) % count)

        for sub in ordered_subs:
            # If a re-roll happened mid-loop during a Window event, we might want to abort
            # further listeners for this specific serial, but simplified here:
            sub.callback(event, sub.owner_idx, self)

    def run_race(self):
        while not self.state.race_over:
            self.run_turn()
            self.advance_turn()

    def run_turn(self):
        self.state.history.clear()
        cr = self.state.current_racer_idx
        racer = self.state.racers[cr]
        racer.reroll_count = 0

        self.log_context.start_turn_log(racer.repr)
        if self.logging_enabled:
            logger.info(f"=== START TURN: {racer.repr} ===")

        if racer.tripped:
            if self.logging_enabled:
                logger.info(f"{racer.repr} recovers from Trip.")
            racer.tripped = False
            self.push_event(TurnStartEvent(cr), phase=Phase.SYSTEM)
        else:
            self.push_event(TurnStartEvent(cr), phase=Phase.SYSTEM)
            self.push_event(PerformRollEvent(cr), phase=Phase.ROLL_DICE)

        while self.state.queue and not self.state.race_over:
            sched = heapq.heappop(self.state.queue)

            # Loop Detection
            state_hash = self.state.get_state_hash()
            event_sig = hash(repr(sched.event))
            if (state_hash, event_sig) in self.state.history:
                logger.warning(f"Loop detected for {sched.event}. Discarding.")
                continue
            self.state.history.add((state_hash, event_sig))

            self.handle_event(sched.event)

    def handle_event(self, event: GameEvent):
        match event:
            case (
                TurnStartEvent()
                | PassingEvent()
                | AbilityTriggeredEvent()
                | RollModificationWindowEvent()
            ):
                self.publish_to_subscribers(event)

            case MoveCmdEvent():
                self._handle_move_cmd(event)

            case WarpCmdEvent():
                self._handle_warp_cmd(event)

            case PerformRollEvent():
                self._handle_perform_roll(event)

            case ResolveMainMoveEvent():
                self._resolve_main_move(event)

            case _:
                pass

    def _handle_perform_roll(self, event: PerformRollEvent) -> None:
        self.state.roll_state.serial_id += 1
        current_serial = self.state.roll_state.serial_id

        base = self.rng.randint(1, 6)
        query = MoveDistanceQuery(event.racer_idx, base)

        # Apply ALL modifiers attached to this racer
        for mod in self.get_racer(event.racer_idx).modifiers:
            if isinstance(mod, RollModificationMixin):
                mod.modify_roll(query, mod.owner_idx, self)

        final = query.final_value
        self.state.roll_state.base_value = base
        self.state.roll_state.final_value = final

        # Logging with sources
        if query.modifier_sources:
            parts = [f"{name}:{delta:+d}" for (name, delta) in query.modifier_sources]
            mods_str = ", ".join(parts)
            total_delta = sum(delta for _, delta in query.modifier_sources)
            logger.info(
                f"Dice Roll: {base} (Mods: {total_delta} [{mods_str}]) -> Result: {final}",
            )
        else:
            logger.info(f"Dice Roll: {base} (Mods: 0) -> Result: {final}")

        # 3. Fire the 'Window' event. Listeners can call trigger_reroll() here.
        self.push_event(
            RollModificationWindowEvent(event.racer_idx, final, current_serial),
            phase=Phase.ROLL_WINDOW,
        )

        # 4. Schedule the resolution. If trigger_reroll() was called in step 3,
        # serial_id will increment, and this event will be ignored in _resolve_main_move.
        self.push_event(
            ResolveMainMoveEvent(event.racer_idx, current_serial),
            phase=Phase.MAIN_ACT,
        )

    def _resolve_main_move(self, event: ResolveMainMoveEvent):
        # If serial doesn't match, it means a re-roll happened.
        if event.roll_serial != self.state.roll_state.serial_id:
            logger.debug("Ignoring stale roll resolution (Re-roll occurred).")
            return

        dist = self.state.roll_state.final_value
        if dist > 0:
            self.push_move(event.racer_idx, dist, "MainMove", phase=Phase.MOVE_EXEC)

    def _handle_move_cmd(self, evt: MoveCmdEvent):
        racer = self.get_racer(evt.racer_idx)
        if racer.finished:
            return

        # Moving 0 is not moving at all
        if evt.distance == 0:
            return

        start = racer.position
        distance = evt.distance

        # 1. Departure hook
        self.publish_to_subscribers(
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
        end = self.state.board.resolve_position(
            intended,
            evt.racer_idx,
            self,
        )  # [file:1]

        # If you get fully blocked back to your start, treat as “no movement”
        if end == start:
            return

        logger.info(f"Move: {racer.repr} {start}->{end} ({evt.source})")  # [file:1]

        # 3. Passing events (unchanged from your current logic)
        if distance > 0:
            for tile in range(start + 1, min(end, self.state.board.length)):
                if tile < end:
                    victims = [
                        r
                        for r in self.state.racers
                        if r.position == tile and r.idx != racer.idx and not r.finished
                    ]
                    for v in victims:
                        self.push_event(
                            PassingEvent(racer.idx, v.idx, tile),
                            phase=Phase.MOVE_EXEC,
                        )  # [file:1]

        # 4. Commit position
        racer.position = end

        # Finish check as in your current engine
        if self._check_finish(racer):  # may log finish + mark race_over, etc. [file:1]
            return

        # 5. Board “on land” hooks (Trip, VP, MoveDelta, etc.)
        self.state.board.trigger_on_land(end, racer.idx, evt.phase, self)  # [file:1]

        # 6. Arrival hook
        self.publish_to_subscribers(
            PostMoveEvent(
                racer_idx=evt.racer_idx,
                start_tile=start,
                end_tile=end,
                source=evt.source,
                phase=evt.phase,
            ),
        )

    def _handle_warp_cmd(self, evt: WarpCmdEvent):
        racer = self.get_racer(evt.racer_idx)
        if racer.finished:
            return

        start = racer.position

        # Warping to the same tile is not movement
        if start == evt.target_tile:
            return

        # 1. Departure hook
        self.publish_to_subscribers(
            PreWarpEvent(
                racer_idx=evt.racer_idx,
                start_tile=start,
                target_tile=evt.target_tile,
                source=evt.source,
                phase=evt.phase,
            ),
        )

        # 2. Resolve spatial modifiers on the target
        resolved = self.state.board.resolve_position(
            evt.target_tile,
            evt.racer_idx,
            self,
        )  # [file:1]

        if resolved == start:
            return

        logger.info(f"Warp: {racer.repr} -> {resolved} ({evt.source})")  # [file:1]
        racer.position = resolved

        if self._check_finish(racer):
            return

        # 3. Board hooks on landing
        self.state.board.trigger_on_land(
            resolved,
            racer.idx,
            evt.phase,
            self,
        )  # [file:1]

        # 4. Arrival hook
        self.publish_to_subscribers(
            PostWarpEvent(
                racer_idx=evt.racer_idx,
                start_tile=start,
                end_tile=resolved,
                source=evt.source,
                phase=evt.phase,
            ),
        )

    def _check_finish(self, racer: RacerState) -> bool:
        if racer.finished:
            return False

        if racer.position >= self.state.board.length:
            # Count how many finished before this one
            finishing_position = sum(1 for r in self.state.racers if r.finished) + 1
            racer.finish_position = finishing_position

            if self.logging_enabled:
                logger.info(f"!!! {racer.repr} FINISHED rank {finishing_position} !!!")

            # Emit finish event
            self.push_event(
                RacerFinishedEvent(racer.idx, finishing_position),
                phase=Phase.REACTION,
            )

            # Strip abilities
            self.update_racer_abilities(racer.idx, set())

            # Check if race is over (2 finishers)
            finished_count = sum(1 for r in self.state.racers if r.finished)
            if finished_count >= 2:
                self.state.race_over = True
                # Mark remaining as eliminated
                for r in self.state.racers:
                    if not r.finished:
                        r.eliminated = True
                self.state.queue.clear()
                self._log_final_standings()

            return True

        return False

    def _log_final_standings(self):
        if not self.logging_enabled:
            return
        logger.info("=== FINAL STANDINGS ===")
        for racer in sorted(
            self.state.racers,
            key=lambda r: r.finish_position if r.finish_position else 999,
        ):
            if racer.finish_position:
                status = f"Rank {racer.finish_position}"
            else:
                status = "Eliminated"
            logger.info(
                f"Result: {racer.repr} pos={racer.position} vp={racer.victory_points} {status}",
            )

    def advance_turn(self):
        if self.state.race_over:
            return
        curr = self.state.current_racer_idx
        n = len(self.state.racers)
        next_idx = (curr + 1) % n
        while not self.state.racers[next_idx].active:  # Skip finished/eliminated
            next_idx = (next_idx + 1) % n
            if next_idx == curr:
                break
        if next_idx < curr:
            self.log_context.new_round()
        self.state.current_racer_idx = next_idx
