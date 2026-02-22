from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Self, override

from magical_athlete_simulator.ai.evaluation import (
    get_benefit_at,
    get_hazard_at,
    is_turn_between,
)
from magical_athlete_simulator.core.abilities import Ability
from magical_athlete_simulator.core.agent import (
    BooleanDecisionMixin,
    DecisionContext,
)
from magical_athlete_simulator.core.events import (
    AbilityTriggeredEvent,
    GameEvent,
    MoveCmdEvent,
    Phase,
    PostMoveEvent,
)
from magical_athlete_simulator.core.mixins import DestinationCalculatorMixin
from magical_athlete_simulator.core.modifiers import RacerModifier
from magical_athlete_simulator.engine.abilities import (
    add_racer_modifier,
    remove_racer_modifier,
)
from magical_athlete_simulator.engine.movement import push_move

if TYPE_CHECKING:
    from magical_athlete_simulator.core.agent import Agent
    from magical_athlete_simulator.core.state import ActiveRacerState
    from magical_athlete_simulator.core.types import AbilityName, ModifierName
    from magical_athlete_simulator.engine.game_engine import GameEngine


@dataclass(eq=False)
class SuckerfishTargetModifier(RacerModifier, DestinationCalculatorMixin):
    name: AbilityName | ModifierName = "SuckerfishTarget"
    priority: int = 0  # High priority to ensure exact landing
    target_tile: int = 0

    @override
    def calculate_destination(
        self,
        engine: GameEngine,
        racer_idx: int,
        start_tile: int,
        distance: int,
        move_cmd_event: MoveCmdEvent,
    ) -> tuple[int, list[AbilityTriggeredEvent]]:
        # We force the destination to be the specific tile we want.
        # This overrides normal distance math, but ensures we hit the target
        # even if other modifiers tried to mess with us.

        # Cleanup self immediately
        remove_racer_modifier(engine, racer_idx, self)

        return self.target_tile, [
            AbilityTriggeredEvent(
                responsible_racer_idx=racer_idx,
                source=self.name,
                phase=move_cmd_event.phase,
                target_racer_idx=move_cmd_event.target_racer_idx,
            ),
        ]


@dataclass
class SuckerfishRide(Ability, BooleanDecisionMixin):
    name: AbilityName = "SuckerfishRide"
    triggers: tuple[type[GameEvent], ...] = (PostMoveEvent,)

    @override
    def execute(
        self,
        event: GameEvent,
        owner: ActiveRacerState,
        engine: GameEngine,
        agent: Agent,
    ):
        # ignore Suckerfish' moves
        if (
            not isinstance(event, PostMoveEvent)
            or event.target_racer_idx == owner.idx
            or event.start_tile != owner.position
        ):
            return "skip_trigger"

        if (distance := event.end_tile - owner.position) == 0:
            return "skip_trigger"

        should_ride = agent.make_boolean_decision(
            engine,
            ctx=DecisionContext(
                source=self,
                event=event,
                game_state=engine.state,
                source_racer_idx=owner.idx,
            ),
        )

        if not should_ride:
            return "skip_trigger"

        engine.log_info(
            f"{owner.repr} rides the wake of {engine.get_racer(event.target_racer_idx).repr} to {event.end_tile}!",
        )

        # 1. Attach the target lock
        mod = SuckerfishTargetModifier(owner_idx=owner.idx, target_tile=event.end_tile)
        add_racer_modifier(engine, owner.idx, mod)

        # 2. Push the move command
        push_move(
            engine,
            moved_racer_idx=owner.idx,
            distance=distance,
            phase=Phase.REACTION,
            source=self.name,
            responsible_racer_idx=owner.idx,
            emit_ability_triggered="never",
        )

        # triggers in modifier
        return "skip_trigger"

    @override
    def get_baseline_boolean_decision(
        self,
        engine: GameEngine,
        ctx: DecisionContext[Self],
    ) -> bool:
        if not isinstance(ctx.event, PostMoveEvent):
            raise TypeError("Expected PostMoveEvent for Suckerfish decision!")

        if (owner := engine.get_active_racer(ctx.source_racer_idx)) is None or (
            moving_racer := engine.get_active_racer(ctx.event.target_racer_idx)
        ) is None:
            return False

        # check if moving forward
        return moving_racer.position > owner.position

    @override
    def get_auto_boolean_decision(
        self,
        engine: GameEngine,
        ctx: DecisionContext[Self],
    ) -> bool:
        if (
            (me := engine.get_active_racer(ctx.source_racer_idx)) is None
            or not isinstance(ctx.event, PostMoveEvent)
            or (driver := engine.get_racer(ctx.event.target_racer_idx)).position is None
        ):
            return False

        dest = ctx.event.end_tile
        dist = dest - me.position
        
        # 0. If the driver just finished, always follow to claim 2nd place
        if not driver.active:
            if dist > 0:
                engine.log_info(f"{me.repr} follows {driver.repr} across the finish line!")
                return True
            return False

        # Define Bad Abilities (Drivers to avoid)
        BAD_DRIVER_ABILITIES: set[AbilityName] = {
            "MouthSwallow",
            "FlipFlopSwap",
            "ThirdWheelJoin",
            "SisyphusCurse",
            "HugeBabyPush",
        }

        # Define Good Abilities (Drivers to prefer)
        GOOD_DRIVER_ABILITIES: set[AbilityName] = {
            "ScoochStep",
            "RomanticMove"
        }

        driver_abilities = driver.abilities

        # 1. Hard filters: obvious no-gos
        # Check if driver has Mouth ability AND is still on the board (active)
        if ("MouthSwallow" in driver_abilities and driver.active) or dist <= 0:
            return False

        # 2. Immediate benefit / hazard on destination
        if (benefit := get_benefit_at(engine, dest)) is not None:
            engine.log_info(f"{me.repr} hitchhikes to reach {benefit}!")
            return True

        if (hazard := get_hazard_at(engine, dest)) is not None:
            engine.log_info(
                f"{me.repr} avoids hitchhiking with {driver.repr} because of {hazard}!",
            )
            return False

        # 3. Special driver cases (Ability-based)
        if not GOOD_DRIVER_ABILITIES.isdisjoint(driver_abilities):
            return True

        # 4. Big safe rides: always take (distance ≥ 4)
        if dist >= 4:
            return True

        # 5. Small safe rides (1–3): chain logic and local options
        def moves_before_me(r_idx: int) -> bool:
            return is_turn_between(driver.idx, me.idx, r_idx)
        

        # 5a. Destination chain: highest priority among small safe rides
        for r in engine.get_racers_at_position(dest, except_racer_idx=me.idx):
            if moves_before_me(r.idx) and BAD_DRIVER_ABILITIES.isdisjoint(r.abilities):
                engine.log_info(
                    f"{me.repr} hitchhikes with {driver.repr} to get to {r.repr}!",
                )
                return True

        # 5b. Current tile: consider waiting only if no destination-chain exists
        for r in engine.get_racers_at_position(me.position, except_racer_idx=me.idx):
            # Wait for someone who moves before me AND isn't bad
            if moves_before_me(r.idx) and BAD_DRIVER_ABILITIES.isdisjoint(r.abilities):
                engine.log_info(
                    f"{me.repr} waits for another rider on his tile instead of {driver.repr} (+{dist})!",
                )
                return False

        # 5c. No chain and no better local options: just take the small, safe ride
        return True

