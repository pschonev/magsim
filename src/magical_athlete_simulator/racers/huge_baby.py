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
    WarpData,
)
from magical_athlete_simulator.core.mixins import (
    ApproachHookMixin,
    LifecycleManagedMixin,
)
from magical_athlete_simulator.core.modifiers import SpaceModifier
from magical_athlete_simulator.engine.movement import push_simultaneous_warp

if TYPE_CHECKING:
    from magical_athlete_simulator.core.agent import Agent
    from magical_athlete_simulator.core.state import RacerState
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

        engine.log_info(
            f"{engine.get_racer(moving_racer_idx).repr} got blocked by {self.display_name}!",
        )
        engine.push_event(
            AbilityTriggeredEvent(
                self.owner_idx,
                source=self.name,
                phase=Phase.SYSTEM,
                target_racer_idx=moving_racer_idx,
                movement_distance=-1,
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

    @override
    def on_gain(self, engine: GameEngine, owner_idx: int):
        if (racer := engine.get_active_racer(owner_idx)) is None:
            return
        if racer.position > 0:
            modifier = HugeBabyModifier(owner_idx=owner_idx)
            engine.state.board.register_modifier(racer.position, modifier, engine)

    @override
    def on_loss(self, engine: GameEngine, owner_idx: int):
        if (racer := engine.get_active_racer(owner_idx)) is None:
            return
        modifier_template = HugeBabyModifier(owner_idx=owner_idx)
        board = engine.state.board

        # 1. Optimization: Check current position first
        if modifier_template in board.dynamic_modifiers.get(racer.position, []):
            board.unregister_modifier(racer.position, modifier_template, engine)
            return

        # 2. Fallback: Scan the board
        for tile, modifiers in list(board.dynamic_modifiers.items()):
            if modifier_template in modifiers:
                board.unregister_modifier(tile, modifier_template, engine)
                return

    @override
    def execute(
        self,
        event: GameEvent,
        owner: RacerState,
        engine: GameEngine,
        agent: Agent,
    ) -> AbilityTriggeredEventOrSkipped:
        if (
            not isinstance(event, (PostMoveEvent, PostWarpEvent))
            or event.target_racer_idx != owner.idx
        ):
            return "skip_trigger"

        modifier_template = HugeBabyModifier(owner_idx=owner.idx)

        # 1. CLEANUP OLD TILE
        if (
            event.start_tile != 0
            and modifier_template
            in engine.state.board.dynamic_modifiers.get(event.start_tile, [])
        ):
            engine.state.board.unregister_modifier(
                event.start_tile,
                modifier_template,
                engine,
            )

        # 2. REGISTER NEW TILE
        if event.end_tile != 0 and self in owner.active_abilities:
            engine.state.board.register_modifier(
                event.end_tile,
                modifier_template,
                engine,
            )

            # 3. PUSH VICTIMS (Only if we successfully placed the blocker)
            if (target := max(0, event.end_tile - 1)) >= 0:
                victims = engine.get_racers_at_position(
                    event.end_tile,
                    except_racer_idx=owner.idx,
                )
                if victims:
                    engine.log_info(
                        f"{owner.repr} landed on {target} and pushes away {', '.join([v.repr for v in victims])} using {self.name}",
                    )
                    warps = [
                        WarpData(warping_racer_idx=v.idx, target_tile=target)
                        for v in victims
                    ]
                    push_simultaneous_warp(
                        engine,
                        warps=warps,
                        phase=Phase.PRE_MAIN,
                        source=self.name,
                        responsible_racer_idx=owner.idx,
                        emit_ability_triggered="after_resolution",
                    )

        return "skip_trigger"
