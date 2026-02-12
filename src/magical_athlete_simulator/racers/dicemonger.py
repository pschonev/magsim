from __future__ import annotations

from dataclasses import dataclass
from functools import reduce
from typing import TYPE_CHECKING, override

from magical_athlete_simulator.core.abilities import Ability
from magical_athlete_simulator.core.agent import BooleanDecisionMixin, DecisionContext
from magical_athlete_simulator.core.events import (
    AbilityTriggeredEvent,
    AbilityTriggeredEventOrSkipped,
    GameEvent,
    PreTurnStartEvent,
    RollModificationWindowEvent,
)
from magical_athlete_simulator.core.mixins import (
    ExternalAbilityMixin,
    LifecycleManagedMixin,
)
from magical_athlete_simulator.core.types import D6Values, D6VAlueSet
from magical_athlete_simulator.engine.movement import push_move
from magical_athlete_simulator.engine.roll import trigger_reroll

if TYPE_CHECKING:
    from magical_athlete_simulator.core.agent import Agent
    from magical_athlete_simulator.core.state import RacerState
    from magical_athlete_simulator.core.types import AbilityName
    from magical_athlete_simulator.engine.game_engine import GameEngine


@dataclass
class DicemongerRerollAction(Ability, BooleanDecisionMixin, ExternalAbilityMixin):
    """
    The granted reroll ability.
    - source_racer_idx: Tracks who gets the profit (from ExternalAbilityMixin).
    - used_this_turn: Mutable state (excluded from equality checks by matches_identity).
    """

    name: AbilityName = "DicemongerDeal"
    triggers: tuple[type[GameEvent], ...] = (
        RollModificationWindowEvent,
        PreTurnStartEvent,
    )
    preferred_dice: D6VAlueSet = frozenset([4, 5, 6])

    # state
    used_this_turn: bool = False

    @override
    def execute(
        self,
        event: GameEvent,
        owner: RacerState,
        engine: GameEngine,
        agent: Agent,
    ) -> AbilityTriggeredEventOrSkipped:
        # 1. Reset Logic
        if isinstance(event, PreTurnStartEvent):
            if engine.state.current_racer_idx == owner.idx:
                self.used_this_turn = False
            return "skip_trigger"

        # 2. Reroll Logic
        if not isinstance(event, RollModificationWindowEvent):
            return "skip_trigger"

        # Eligibility
        if (
            event.target_racer_idx != owner.idx
            or self.used_this_turn
            or event.roll_serial != engine.state.roll_state.serial_id
        ):
            return "skip_trigger"

        # Ask Agent
        should_reroll = agent.make_boolean_decision(
            engine,
            DecisionContext(
                source=self,
                event=event,
                game_state=engine.state,
                source_racer_idx=owner.idx,
            ),
        )

        if not should_reroll:
            return "skip_trigger"

        # Execute
        source_racer = engine.get_racer(self.source_racer_idx)
        engine.log_info(
            f"{owner.repr} uses {self.name} from {source_racer.repr} to reroll!",
        )
        self.used_this_turn = True

        # Trigger the mechanic
        trigger_reroll(engine, owner.idx, self.name)

        # Dicemonger Profit Logic (+1 Move)
        # "Whenever ANOTHER racer rerolls this way..."
        if owner.idx != self.source_racer_idx:
            engine.log_info(f"{source_racer.repr} profits +1 from {self.name}.")
            push_move(
                engine,
                distance=1,
                phase=event.phase,
                moved_racer_idx=self.source_racer_idx,
                source=self.name,
                responsible_racer_idx=self.source_racer_idx,
                emit_ability_triggered="immediately",
            )

        return AbilityTriggeredEvent(
            responsible_racer_idx=owner.idx,
            source=self.name,
            phase=event.phase,
            target_racer_idx=owner.idx,
        )

    @override
    def get_auto_boolean_decision(
        self,
        engine: GameEngine,
        ctx: DecisionContext[DicemongerRerollAction],
    ) -> bool:
        dice_val = ctx.game_state.roll_state.dice_value
        if dice_val is None:
            return False

        default_dice_preference = frozenset[D6Values]([4, 5, 6])
        racer = engine.get_racer(ctx.source_racer_idx)

        preferred_dice_sets = [
            a.preferred_dice
            for a in racer.active_abilities
            if a.preferred_dice != default_dice_preference
        ]
        preferred_dice_sets = (
            preferred_dice_sets if preferred_dice_sets else [default_dice_preference]
        )

        preferred_dice = reduce(lambda a, b: a.intersection(b), preferred_dice_sets)
        preferred_dice = preferred_dice if preferred_dice else default_dice_preference

        engine.log_debug(f"{preferred_dice=} for {racer.repr}")
        return dice_val not in preferred_dice


@dataclass
class DicemongerRerollManager(Ability, LifecycleManagedMixin):
    """
    The intrinsic ability that grants the Reroll Action to everyone.
    """

    name: AbilityName = "DicemongerRerollManager"
    triggers: tuple[type[GameEvent], ...] = ()

    @override
    def on_gain(self, engine: GameEngine, owner_idx: int) -> None:
        """Grant the reroll action to everyone."""
        for racer in engine.state.racers:
            # Create instance pointing to ME
            # Note: ExternalAbilityMixin handles the equality logic via matches_identity
            action = DicemongerRerollAction(source_racer_idx=owner_idx)
            engine.log_debug(
                f"{engine.get_racer(owner_idx).repr} granted {action.name} to {engine.get_racer(racer.idx).repr}",
            )
            engine.grant_ability(racer.idx, action)

    @override
    def on_loss(self, engine: GameEngine, owner_idx: int) -> None:
        """Revoke the reroll action from everyone."""
        # Create dummy for matching
        dummy = DicemongerRerollAction(source_racer_idx=owner_idx)

        for racer in engine.state.racers:
            engine.revoke_ability(racer.idx, dummy)
