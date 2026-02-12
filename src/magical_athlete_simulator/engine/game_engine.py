from __future__ import annotations

import heapq
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from magical_athlete_simulator.ai.smart_agent import SmartAgent
from magical_athlete_simulator.core.events import (
    AbilityTriggeredEvent,
    EmitsAbilityTriggeredEvent,
    ExecuteMainMoveEvent,
    GameEvent,
    MainMoveSkippedEvent,
    MoveCmdEvent,
    PassingEvent,
    PerformMainRollEvent,
    PreTurnStartEvent,
    RacerEliminatedEvent,
    RacerFinishedEvent,
    ResolveMainMoveEvent,
    RollModificationWindowEvent,
    RollResultEvent,
    ScheduledEvent,
    SimultaneousMoveCmdEvent,
    SimultaneousWarpCmdEvent,
    TripCmdEvent,
    TripRecoveryEvent,
    TurnEndEvent,
    TurnStartEvent,
    WarpCmdEvent,
)
from magical_athlete_simulator.core.mixins import (
    ExternalAbilityMixin,
    LifecycleManagedMixin,
    SetupPhaseMixin,
)
from magical_athlete_simulator.core.registry import (
    RACER_ABILITIES,
)
from magical_athlete_simulator.core.state import RollState
from magical_athlete_simulator.engine.logging import ContextFilter
from magical_athlete_simulator.engine.loop_detection import LoopDetector
from magical_athlete_simulator.engine.movement import (
    handle_move_cmd,
    handle_simultaneous_move_cmd,
    handle_simultaneous_warp_cmd,
    handle_trip_cmd,
    handle_warp_cmd,
)
from magical_athlete_simulator.engine.roll import (
    handle_execute_main_move,
    handle_perform_main_roll,
    resolve_main_move,
)
from magical_athlete_simulator.racers import get_ability_classes, get_all_racer_stats

if TYPE_CHECKING:
    import random

    from magical_athlete_simulator.core.abilities import Ability
    from magical_athlete_simulator.core.agent import Agent
    from magical_athlete_simulator.core.state import (
        GameState,
        LogContext,
        RacerState,
    )
    from magical_athlete_simulator.core.types import (
        ErrorCode,
        RacerName,
        RacerStat,
        Source,
    )

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
    current_processing_event: ScheduledEvent | None = None
    subscribers: dict[type[GameEvent], list[Subscriber]] = field(default_factory=dict)
    agents: dict[int, Agent] = field(default_factory=dict)

    # Errors and loop detection
    bug_reason: ErrorCode | None = None
    loop_detector: LoopDetector = field(default_factory=LoopDetector)

    # Callback for external observers
    on_event_processed: Callable[[GameEngine, GameEvent], None] | None = None
    verbose: bool = True
    _logger: logging.Logger = field(init=False, repr=False)

    def __post_init__(self) -> None:
        """Assigns starting abilities to all racers and fires on_gain hooks."""
        base = logging.getLogger("magical_athlete")
        self._logger = base.getChild(f"engine.{id(self)}")

        if self.verbose:
            self._logger.addFilter(ContextFilter(self))

        for racer in self.state.racers:
            # 1. Initial Identity (e.g. "Egg", "Copycat")
            initial_core = self.instantiate_racer_abilities(racer.name)
            self.replace_core_abilities(racer.idx, initial_core)

            _ = self.agents.setdefault(racer.idx, SmartAgent())

            # 2. Dynamic Setup Phase Handling
            # Use a set of OBJECT IDs to track processed instances (since instances are mutable/unhashable)
            processed_ids: set[int] = set()

            while True:
                # Find abilities we haven't processed yet
                # We iterate the current live list from the racer state
                new_abilities = [
                    ab for ab in racer.active_abilities if id(ab) not in processed_ids
                ]

                if not new_abilities:
                    break

                for ability in new_abilities:
                    processed_ids.add(id(ability))

                    # If this ability has setup logic (e.g. Egg picking a card), run it
                    if isinstance(ability, SetupPhaseMixin):
                        ability.on_setup(self, racer, self.agents[racer.idx])

                        # Crucially: on_setup might call replace_core_abilities,
                        # adding NEW abilities to racer.active_abilities.
                        # The 'while True' loop will catch them on the next pass.

    # --- Main Loop ---
    def run_race(self):
        while not self.state.race_over:
            self.run_turn()
            self._advance_turn()

    def run_turn(self):
        # 1. Reset detector for the new turn
        self.loop_detector.reset_for_turn()
        self.state.history.clear()

        cr = self.state.current_racer_idx
        racer = self.state.racers[cr]

        # reset roll state
        self.state.roll_state = RollState()
        racer.roll_override = None
        racer.can_reroll = True
        racer.main_move_consumed = False

        self.log_context.start_turn_log(f"{racer.idx}•{racer.name}")
        self.log_info(f"=== START TURN: {racer.repr} ===")

        # --- Pre-Turn Recording (for Heckler) ---
        self.push_event(
            PreTurnStartEvent(
                responsible_racer_idx=None,
                source="System",
            ),
        )

        if racer.tripped:
            self.log_info(f"{racer.repr} recovers from Trip.")
            racer.tripped = False
            tripping_racers = racer.tripping_racers.copy()
            racer.tripping_racers = []
            racer.main_move_consumed = True
            self.push_event(
                TripRecoveryEvent(
                    target_racer_idx=cr,
                    tripping_racers=tripping_racers,
                    responsible_racer_idx=None,
                    source="System",
                ),
            )
            self.push_event(
                TurnStartEvent(
                    target_racer_idx=cr,
                    responsible_racer_idx=None,
                    source="System",
                ),
            )
        else:
            self.push_event(
                TurnStartEvent(
                    target_racer_idx=cr,
                    responsible_racer_idx=None,
                    source="System",
                ),
            )
            self.push_event(
                PerformMainRollEvent(
                    target_racer_idx=cr,
                    responsible_racer_idx=None,
                    source="System",
                ),
            )

        turn_end_triggered = False
        while not self.state.race_over:
            if not self.state.queue:
                # If done with normal events, inject TurnEndEvent ONCE
                if not turn_end_triggered:
                    self.push_event(
                        TurnEndEvent(
                            responsible_racer_idx=None,
                            source="System",
                        ),
                    )
                    turn_end_triggered = True
                    continue  # Restart loop to process TurnEndEvent

                # If already triggered and still empty, we are truly done
                break
            # -------------------------------

            # Prepare hashes for checks
            current_board_hash = self._calculate_board_hash()
            current_system_hash = self.state.get_state_hash()

            # --- Layer 1: Exact State Cycle (Least Harmful) ---
            if self.loop_detector.check_exact_cycle(current_system_hash):
                skipped = heapq.heappop(self.state.queue)
                self.loop_detector.forget_event(skipped.serial)
                self.log_warning(
                    f"Infinite loop detected (Exact State Cycle). Dropping recursive event: {skipped.event}",
                )
                continue

            # Peek/Pop the next event
            sched = heapq.heappop(self.state.queue)

            # --- Layer 2: Heuristic Detection (Surgical Fix) ---
            if self.loop_detector.check_heuristic_loop(
                current_board_hash,
                len(self.state.queue),
                sched,
            ):
                self.log_warning(
                    f"MINOR_LOOP_DETECTED (Heuristic/Exploding). Dropping: {sched.event}",
                )
                self.bug_reason = (
                    "MINOR_LOOP_DETECTED"
                    if self.bug_reason != "CRITICAL_LOOP_DETECTED"
                    else self.bug_reason
                )
                continue

            # --- Layer 3: Global Sanity Check (Nuclear Option) ---
            if self.loop_detector.check_global_sanity(current_board_hash):
                self.log_error(
                    "CRITICAL_LOOP_DETECTED: Board state oscillation limit exceeded. Aborting turn.",
                )
                self.state.queue.clear()
                self.bug_reason = "CRITICAL_LOOP_DETECTED"
                break

            self.current_processing_event = sched
            self._handle_event(sched.event)

    def _calculate_board_hash(self) -> int:
        racer_states = tuple(
            (
                r.raw_position,
                r.active,
                r.tripped,
                r.main_move_consumed,
                tuple(sorted(a.name for a in r.active_abilities)),
            )
            for r in self.state.racers
        )
        return hash((self.state.current_racer_idx, racer_states))

    def _advance_turn(self):
        if self.state.race_over:
            return

        if self.state.next_turn_override is not None:
            next_idx = self.state.next_turn_override
            self.state.next_turn_override = None
            self.state.current_racer_idx = next_idx
            self.log_info(
                f"Turn Order Override: {self.get_racer(next_idx).repr} takes the next turn!",
            )
            return

        curr = self.state.current_racer_idx
        n = len(self.state.racers)
        next_idx = (curr + 1) % n

        start_search = next_idx
        while not self.state.racers[next_idx].active:
            next_idx = (next_idx + 1) % n
            if next_idx == start_search:
                self.state.race_over = True
                return

        if next_idx < curr:
            self.log_context.new_round()

        self.state.current_racer_idx = next_idx

    # --- Event Management ---
    def push_event(self, event: GameEvent, priority: int | None = None):
        if priority is not None:
            _priority = priority
        elif event.responsible_racer_idx is None:
            if (
                isinstance(event, EmitsAbilityTriggeredEvent)
                and event.emit_ability_triggered != "never"
            ):
                msg = f"Received a {event.__class__.__name__} with no responsible racer ID..."
                raise ValueError(msg)
            _priority = 0
        else:
            curr = self.state.current_racer_idx
            count = len(self.state.racers)
            _priority = 1 + ((event.responsible_racer_idx - curr) % count)

        if (
            self.current_processing_event
            and self.current_processing_event.event.phase == event.phase
        ):
            if self.current_processing_event.priority == 0:
                new_depth = self.current_processing_event.depth
            else:
                new_depth = self.current_processing_event.depth + 1
        else:
            new_depth = 0

        self.state.serial += 1
        sched = ScheduledEvent(
            new_depth,
            _priority,
            self.state.serial,
            event,
            mode=self.state.rules.timing_mode,
        )

        # Notify loop detector of the board state at creation time
        self.loop_detector.record_event_creation(
            sched.serial,
            self._calculate_board_hash(),
        )

        msg = f"{sched}"
        self.log_debug(msg)
        heapq.heappush(self.state.queue, sched)

        if (
            isinstance(event, EmitsAbilityTriggeredEvent)
            and event.emit_ability_triggered == "immediately"
        ):
            self.push_event(AbilityTriggeredEvent.from_event(event))

    def _rebuild_subscribers(self):
        self.subscribers.clear()
        for racer in self.state.racers:
            for ability in racer.active_abilities:
                ability.register(self, racer.idx)

    def subscribe(
        self,
        event_type: type[GameEvent],
        callback: AbilityCallback,
        owner_idx: int,
    ):
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(Subscriber(callback, owner_idx))

    def _update_abilities(self, racer_idx: int, desired_list: list[Ability]) -> None:
        """
        Low-level reconciler. Makes racer.active_abilities (list[Ability]) match desired_list.
        Handles Lifecycle hooks and Subscription updates.
        """
        racer = self.get_racer(racer_idx)
        current_list = (
            racer.active_abilities.copy()
        )  # Make a copy to avoid stale references

        to_keep: list[Ability] = []
        to_add = list(desired_list)
        to_remove: list[Ability] = []

        # Diff Logic
        for current_ab in current_list:
            found = False
            for i, desired_ab in enumerate(to_add):
                if current_ab.matches_identity(desired_ab):
                    to_keep.append(
                        current_ab
                    )  # Keep existing instance (preserves state)
                    to_add.pop(i)  # Consume this requirement
                    found = True
                    break
            if not found:
                to_remove.append(current_ab)

        # CRITICAL: Commit the new state BEFORE calling lifecycle hooks
        # This ensures nested _update_abilities calls see the correct state
        final_list = to_keep + to_add
        racer.active_abilities = final_list

        # 1. Process Removal (AFTER committing state)
        for ab in to_remove:
            if isinstance(ab, LifecycleManagedMixin):
                ab.on_loss(self, racer_idx)

            # Unsubscribe Logic
            for event_type in self.subscribers:
                self.subscribers[event_type] = [
                    sub
                    for sub in self.subscribers[event_type]
                    if not (
                        sub.owner_idx == racer_idx
                        and getattr(sub.callback, "__self__", None) == ab
                    )
                ]

        # 2. Process Addition (AFTER committing state)
        for ab in to_add:
            ab.register(self, racer_idx)
            if isinstance(ab, LifecycleManagedMixin):
                ab.on_gain(self, racer_idx)
                # Note: on_gain may call grant_ability, which calls _update_abilities again
                # But that's fine because we already committed the state above

        # 3. Subscriber Safety Net
        if to_remove or to_add:
            self._rebuild_subscribers()

    def publish_to_subscribers(self, event: GameEvent):
        if type(event) not in self.subscribers:
            return
        subs = self.subscribers[type(event)]
        curr = self.state.current_racer_idx
        count = len(self.state.racers)
        ordered_subs = sorted(subs, key=lambda s: (s.owner_idx - curr) % count)

        for sub in ordered_subs:
            sub.callback(event, sub.owner_idx, self)

    def _handle_event(self, event: GameEvent):
        match event:
            case (
                AbilityTriggeredEvent()
                | PreTurnStartEvent()
                | TurnStartEvent()
                | TurnEndEvent()
                | PassingEvent()
                | RollModificationWindowEvent()
                | RollResultEvent()
                | RacerFinishedEvent()
                | RacerEliminatedEvent()
            ):
                self.publish_to_subscribers(event)
            case TripCmdEvent():
                handle_trip_cmd(self, event)
            case MoveCmdEvent():
                handle_move_cmd(self, event)
            case SimultaneousMoveCmdEvent():
                handle_simultaneous_move_cmd(self, event)
            case WarpCmdEvent():
                handle_warp_cmd(self, event)
            case SimultaneousWarpCmdEvent():
                handle_simultaneous_warp_cmd(self, event)

            case PerformMainRollEvent():
                handle_perform_main_roll(self, event)

            case ResolveMainMoveEvent():
                self.publish_to_subscribers(event)
                resolve_main_move(self, event)
            case ExecuteMainMoveEvent():
                handle_execute_main_move(self, event)

            case _:
                pass

        if self.on_event_processed:
            self.on_event_processed(self, event)

    # -- Getters --
    def get_agent(self, racer_idx: int) -> Agent:
        return self.agents[racer_idx]

    def get_racer(self, idx: int) -> RacerState:
        return self.state.racers[idx]

    def get_racer_pos(self, idx: int) -> int:
        return self.state.racers[idx].position

    def get_racers_at_position(
        self,
        tile_idx: int,
        except_racer_idx: int | None = None,
    ) -> list[RacerState]:
        if except_racer_idx is None:
            return [r for r in self.state.racers if r.active and r.position == tile_idx]
        else:
            return [
                r
                for r in self.state.racers
                if r.active and r.position == tile_idx and r.idx != except_racer_idx
            ]

    def skip_main_move(
        self,
        *,
        responsible_racer_idx: int,
        source: Source,
        skipped_racer_idx: int,
    ) -> None:
        """
        Marks the racer's main move as consumed and emits a notification event.
        Does nothing if the move was already consumed.
        """
        racer = self.get_racer(skipped_racer_idx)
        if not racer.main_move_consumed:
            racer.main_move_consumed = True
            self.log_info(
                f"{racer.repr} has their main move skipped (Source: {source}).",
            )
            self.push_event(
                MainMoveSkippedEvent(
                    responsible_racer_idx=responsible_racer_idx,
                    source=source,
                    target_racer_idx=skipped_racer_idx,
                ),
            )

    def draw_racers(self, k: int) -> tuple[RacerStat, ...]:
        if k > len(self.state.available_racers):
            self.state.shuffle()  # shuffle cards back in pile

        drawn_racers = self.state.draw_racers(k, rng=self.rng)
        return tuple(
            stat
            for _, stat in get_all_racer_stats(self.log_error).items()
            if stat.racer_name in drawn_racers
        )

    # -- Abilities --

    def instantiate_racer_abilities(self, racer_name: RacerName) -> list[Ability]:
        """
        Factory that creates fresh instances of a racer's default abilities.
        """

        ability_names = RACER_ABILITIES.get(racer_name, set())
        instances: list[Ability] = []
        classes = get_ability_classes()

        for name in ability_names:
            cls = classes.get(name)
            if cls:
                instances.append(cls(name=name))

        return instances

    def replace_core_abilities(
        self,
        racer_idx: int,
        new_core_instances: list[Ability],
    ) -> None:
        """
        Updates the racer's Intrinsic (Identity) abilities.
        Preserves any ability that inherits from ExternalAbilityMixin.
        """
        racer = self.get_racer(racer_idx)

        # 1. Keep the buffs (The ones that opt-in to being External)
        external_abilities = [
            ab for ab in racer.active_abilities if isinstance(ab, ExternalAbilityMixin)
        ]

        # 2. Combine with new identity
        final_list = external_abilities + new_core_instances

        # 3. Reconcile
        self._update_abilities(racer_idx, final_list)

    def grant_ability(self, target_idx: int, ability_instance: Ability) -> None:
        """Adds an external ability instance."""
        racer = self.get_racer(target_idx)
        new_list = [*racer.active_abilities, ability_instance]
        self._update_abilities(target_idx, new_list)

    def revoke_ability(self, target_idx: int, ability_instance: Ability) -> None:
        """Removes a specific external ability instance."""
        racer = self.get_racer(target_idx)
        # Filter out THIS specific instance using matches_identity
        new_list = [
            ab
            for ab in racer.active_abilities
            if not ab.matches_identity(ability_instance)
        ]
        self._update_abilities(target_idx, new_list)

    def clear_all_abilities(self, racer_idx: int) -> None:
        """Removes ALL abilities."""
        self._update_abilities(racer_idx, [])

    # -- Logging --
    def _log(self, level: int, msg: str, *args: Any, **kwargs: Any) -> None:
        if not self.verbose:
            return
        self._logger.log(level, msg, *args, **kwargs)

    def log_debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._log(logging.DEBUG, msg, *args, **kwargs)

    def log_info(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._log(logging.INFO, msg, *args, **kwargs)

    def log_warning(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._log(logging.WARNING, msg, *args, **kwargs)

    def log_error(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._log(logging.ERROR, msg, *args, **kwargs)
