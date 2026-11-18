from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Self, override

from magsim.core.abilities import Ability
from magsim.core.agent import BooleanDecisionMixin, BooleanInteractive, DecisionContext
from magsim.core.events import (
    AbilityTriggeredEvent,
    AbilityTriggeredEventOrSkipped,
    GameEvent,
    Phase,
    RollResultEvent,
)
from magsim.engine.board import MoveDeltaTile, TripTile
from magsim.engine.movement import push_move
from magsim.engine.roll import roll_die

if TYPE_CHECKING:
    from magsim.core.agent import Agent
    from magsim.core.state import ActiveRacerState
    from magsim.core.types import AbilityName
    from magsim.engine.game_engine import GameEngine


@dataclass
class NemesisGrudgeMatch(Ability, BooleanDecisionMixin):
    name: AbilityName = "NemesisGrudgeMatch"
    triggers: tuple[type[GameEvent], ...] = (RollResultEvent,)

    @override
    def execute(
        self,
        event: GameEvent,
        owner: ActiveRacerState,
        engine: GameEngine,
        agent: Agent,
    ) -> AbilityTriggeredEventOrSkipped:
        if (
            not isinstance(event, RollResultEvent)
            or event.target_racer_idx == owner.idx
            or event.dice_value is None
        ):
            return "skip_trigger"

        ctx = DecisionContext[BooleanInteractive](
            source=self,
            event=event,
            game_state=engine.state,
            source_racer_idx=owner.idx,
        )
        if not agent.make_boolean_decision(engine, ctx):
            return "skip_trigger"

        roll = roll_die(engine, owner.idx)
        engine.log_info(
            f"{owner.repr} rolls {roll} against {event.dice_value} ({self.name}).",
        )
        if roll != event.dice_value:
            return "skip_trigger"

        push_move(
            engine,
            roll,
            Phase.REACTION,
            moved_racer_idx=owner.idx,
            source=self.name,
            responsible_racer_idx=owner.idx,
        )
        return AbilityTriggeredEvent(
            responsible_racer_idx=owner.idx,
            source=self.name,
            phase=event.phase,
            target_racer_idx=owner.idx,
            movement_distance=roll,
        )

    @override
    def get_auto_boolean_decision(
        self,
        engine: GameEngine,
        ctx: DecisionContext[Self],
    ) -> bool:
        if (
            not isinstance(ctx.event, RollResultEvent)
            or ctx.event.dice_value is None
            or (me := engine.get_active_racer(ctx.source_racer_idx)) is None
        ):
            return False

        landing = me.position + ctx.event.dice_value
        return not any(
            isinstance(mod, TripTile)
            or (isinstance(mod, MoveDeltaTile) and mod.delta < 0)
            for mod in engine.state.board.get_modifiers_at(landing)
        )
