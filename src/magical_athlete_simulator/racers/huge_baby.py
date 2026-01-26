from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, override

from magical_athlete_simulator.core.abilities import Ability
from magical_athlete_simulator.core.events import (
    AbilityTriggeredEvent,
    AbilityTriggeredEventOrSkipped,
    GameEvent,
    Phase,
    PostMoveEvent,
    PostWarpEvent,
)
from magical_athlete_simulator.core.mixins import (
    ApproachHookMixin,
    LifecycleManagedMixin,
)
from magical_athlete_simulator.core.modifiers import SpaceModifier
from magical_athlete_simulator.engine.movement import push_warp

if TYPE_CHECKING:
    from magical_athlete_simulator.core.agent import Agent
    from magical_athlete_simulator.core.types import AbilityName, ModifierName
    from magical_athlete_simulator.engine.game_engine import GameEngine


@dataclass(eq=True)
class HugeBabyModifier(SpaceModifier, ApproachHookMixin):
    """The physical manifestation of the Huge Baby on the board."""

    name: AbilityName | ModifierName = "HugeBabyBlocker"
    priority: int = 10

    @override
    def on_approach(
        self,
        target: int,
        moving_racer_idx: int,
        engine: GameEngine,
        event: GameEvent,
    ) -> int:
        # 1. ALLOW THE OWNER TO PASS
        if moving_racer_idx == self.owner_idx:
            return target

        # Prevent others from entering the tile
        if target == 0:
            return target

        if self.owner_idx is None:
            msg = f"Expected ID of {self.display_name} owner but got None"
            raise ValueError(msg)

        engine.push_event(
            AbilityTriggeredEvent(
                self.owner_idx,
                source=self.name,
                phase=Phase.SYSTEM,
                target_racer_idx=moving_racer_idx,
            ),
        )
        # Redirect to the previous tile
        return max(0, target - 1)


@dataclass
class HugeBabyPush(Ability, LifecycleManagedMixin):
    name: AbilityName = "HugeBabyPush"
    triggers: tuple[type[GameEvent], ...] = (
        PostMoveEvent,
        PostWarpEvent,
    )

    def _get_modifier(self, owner_idx: int) -> HugeBabyModifier:
        return HugeBabyModifier(owner_idx=owner_idx)

    @override
    def on_gain(self, engine: GameEngine, owner_idx: int):
        racer = engine.get_racer(owner_idx)
        if racer.position > 0:
            mod = HugeBabyModifier(owner_idx=owner_idx)
            engine.state.board.register_modifier(racer.position, mod, engine)

    @override
    def on_loss(self, engine: GameEngine, owner_idx: int):
        # [FIX] "Search and Destroy"
        # We scan for the blocker instead of assuming it is at racer.position.
        # This handles cases where:
        # A) We are at Tile 0 (No blocker exists) -> No Warning.
        # B) We just moved, and the blocker is still at start_tile -> Finds and removes it.

        racer = engine.get_racer(owner_idx)
        template = HugeBabyModifier(owner_idx=owner_idx)
        board = engine.state.board

        # 1. Optimization: Check current position first (Silent Check)
        if template in board.dynamic_modifiers.get(racer.position, []):
            board.unregister_modifier(racer.position, template, engine)
            return

        # 2. Fallback: Scan the board
        # This handles the "Overtake" race condition (blocker left behind at start_tile)
        for tile, modifiers in list(board.dynamic_modifiers.items()):
            if template in modifiers:
                board.unregister_modifier(tile, template, engine)
                return

    @override
    def execute(
        self,
        event: GameEvent,
        owner_idx: int,
        engine: GameEngine,
        agent: Agent,
    ) -> AbilityTriggeredEventOrSkipped:
        # --- ARRIVAL LOGIC ---
        if isinstance(event, (PostMoveEvent, PostWarpEvent)):
            if event.target_racer_idx != owner_idx:
                return "skip_trigger"

            # [FIXED ZOMBIE CHECK]
            # Use safe removal to avoid warnings if on_loss() beat us to it.
            racer = engine.get_racer(owner_idx)
            if self.name not in racer.active_abilities:
                if event.start_tile != 0:
                    template = self._get_modifier(owner_idx)
                    # Check existence before removing
                    if template in engine.state.board.dynamic_modifiers.get(
                        event.start_tile,
                        [],
                    ):
                        engine.state.board.unregister_modifier(
                            event.start_tile,
                            template,
                            engine,
                        )
                return "skip_trigger"

            # 1. ATOMIC MOVE: Clean up the OLD tile
            if event.start_tile != 0:
                mod_to_remove = self._get_modifier(owner_idx)
                # Here we WANT a warning if it's missing, because that would be a bug
                # in normal operation (we expect to have a blocker).
                engine.state.board.unregister_modifier(
                    event.start_tile,
                    mod_to_remove,
                    engine,
                )

            if event.end_tile == 0:
                return "skip_trigger"

            # 2. Register at NEW tile
            mod_to_add = self._get_modifier(owner_idx)
            engine.state.board.register_modifier(event.end_tile, mod_to_add, engine)

            # ... (Push logic continues below) ...
            # 3. "Active Push": Eject any racers already on this tile
            victims = [
                r
                for r in engine.state.racers
                if r.position == event.end_tile
                and r.idx != owner_idx
                and not r.finished
            ]

            for v in victims:
                target = max(0, event.end_tile - 1)
                push_warp(
                    engine,
                    target,
                    phase=event.phase,
                    warped_racer_idx=v.idx,
                    source=self.name,
                    responsible_racer_idx=None,
                )
                engine.log_info(f"HugeBaby pushes {v.repr} to {target}")

                engine.push_event(
                    AbilityTriggeredEvent(
                        owner_idx,
                        self.name,
                        event.phase,
                        target_racer_idx=v.idx,
                    ),
                )

            return "skip_trigger"

        return "skip_trigger"
