from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Self, override

from magsim.ai.evaluation import get_benefit_at, get_current_modifiers, get_hazard_at
from magsim.core.abilities import Ability
from magsim.core.agent import BooleanDecisionMixin, BooleanInteractive, DecisionContext
from magsim.core.mixins import MainRollMixin, MainRollResult
from magsim.engine.roll import roll_die

if TYPE_CHECKING:
    from magsim.core.agent import Agent
    from magsim.core.events import GameEvent
    from magsim.core.state import ActiveRacerState
    from magsim.core.types import AbilityName, D6Values
    from magsim.engine.game_engine import GameEngine

BASELINE_STOP_ABOVE = 3
MAX_DIE = 6


@dataclass
class ShowOffGuysWatchAbility(Ability, MainRollMixin, BooleanDecisionMixin):
    name: AbilityName = "ShowOffGuysWatch"
    triggers: tuple[type[GameEvent], ...] = ()
    total: int = 0
    last: int = 0

    @override
    def roll_main(
        self,
        engine: GameEngine,
        owner: ActiveRacerState,
        agent: Agent,
    ) -> MainRollResult:
        dice: list[D6Values] = [roll_die(engine, owner.idx)]
        self.total = self.last = dice[0]
        engine.log_info(f"{owner.repr} rolls {dice[0]} ({self.name}).")

        while self._wants_to_continue(engine, owner, agent):
            die = roll_die(engine, owner.idx)
            dice.append(die)
            engine.log_info(f"{owner.repr} keeps rolling: {die} after {self.last}.")
            if die <= self.last:
                engine.log_info(
                    f"{owner.repr} rolled the same or lower and does not move."
                )
                engine.skip_main_move(
                    responsible_racer_idx=owner.idx,
                    source=self.name,
                    skipped_racer_idx=owner.idx,
                )
                return MainRollResult(
                    dice=tuple(dice), base_value=0, counting_die=dice[0]
                )
            self.total += die
            self.last = die

        return MainRollResult(
            dice=tuple(dice), base_value=self.total, counting_die=dice[0]
        )

    def _wants_to_continue(
        self,
        engine: GameEngine,
        owner: ActiveRacerState,
        agent: Agent,
    ) -> bool:
        if self.last >= MAX_DIE:
            return False
        return agent.make_boolean_decision(
            engine,
            DecisionContext[BooleanInteractive](
                source=self,
                event=None,
                game_state=engine.state,
                source_racer_idx=owner.idx,
            ),
        )

    @override
    def get_baseline_boolean_decision(
        self,
        engine: GameEngine,
        ctx: DecisionContext[Self],
    ) -> bool:
        return self.last <= BASELINE_STOP_ABOVE

    @override
    def get_auto_boolean_decision(
        self,
        engine: GameEngine,
        ctx: DecisionContext[Self],
    ) -> bool:
        if (me := engine.get_active_racer(ctx.source_racer_idx)) is None:
            return False

        landing = me.position + self.total + get_current_modifiers(engine, me.idx)
        if benefit := get_benefit_at(engine, landing):
            engine.log_info(f"{me.repr} stops showing off to reach {benefit}!")
            return False
        if hazard := get_hazard_at(engine, landing):
            engine.log_info(f"{me.repr} keeps showing off to escape {hazard}!")
            return True
        return self.last <= BASELINE_STOP_ABOVE
