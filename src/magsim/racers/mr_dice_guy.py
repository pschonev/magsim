from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import TYPE_CHECKING, cast, override

from magsim.ai.evaluation import get_benefit_at, get_current_modifiers, get_hazard_at
from magsim.core.abilities import Ability
from magsim.core.agent import (
    SelectionDecisionContext,
    SelectionDecisionMixin,
    SelectionInteractive,
)
from magsim.core.mixins import MainRollMixin, MainRollResult
from magsim.engine.roll import roll_die

if TYPE_CHECKING:
    from typing import Self

    from magsim.core.agent import Agent
    from magsim.core.events import GameEvent
    from magsim.core.state import ActiveRacerState
    from magsim.core.types import AbilityName, D6Values
    from magsim.engine.game_engine import GameEngine

DICE_COUNT = 6


@dataclass
class MrDiceGuyMoreAbility(Ability, MainRollMixin, SelectionDecisionMixin[int]):
    name: AbilityName = "MrDiceGuyMore"
    triggers: tuple[type[GameEvent], ...] = ()

    @override
    def roll_main(
        self,
        engine: GameEngine,
        owner: ActiveRacerState,
        agent: Agent,
    ) -> MainRollResult:
        dice = tuple(roll_die(engine, owner.idx) for _ in range(DICE_COUNT))
        engine.log_info(
            f"{owner.repr} rolls all six dice: {sorted(dice)} ({self.name})."
        )

        duplicates = sorted(
            (value for value, count in Counter(dice).items() if count > 1),
            reverse=True,
        )
        if not duplicates:
            engine.log_info(f"{owner.repr} rolled no duplicate and does not move.")
            engine.skip_main_move(
                responsible_racer_idx=owner.idx,
                source=self.name,
                skipped_racer_idx=owner.idx,
            )
            return MainRollResult(dice=dice, base_value=0, counting_die=None)

        chosen = agent.make_selection_decision(
            engine,
            ctx=SelectionDecisionContext[SelectionInteractive[int], int](
                source=self,
                event=None,
                game_state=engine.state,
                source_racer_idx=owner.idx,
                options=duplicates,
            ),
        )
        value = chosen if chosen is not None else duplicates[0]
        engine.log_info(f"{owner.repr} picks {value} as the main move.")
        return MainRollResult(
            dice=dice,
            base_value=value,
            counting_die=cast("D6Values", value),
        )

    @override
    def get_auto_selection_decision(
        self,
        engine: GameEngine,
        ctx: SelectionDecisionContext[Self, int],
    ) -> int | None:
        if (me := engine.get_active_racer(ctx.source_racer_idx)) is None:
            return None

        mods = get_current_modifiers(engine, me.idx)
        landings = {value: me.position + value + mods for value in ctx.options}

        for value in ctx.options:
            if benefit := get_benefit_at(engine, landings[value]):
                engine.log_info(f"{me.repr} picks {value} to reach {benefit}!")
                return value

        safe = [v for v in ctx.options if not get_hazard_at(engine, landings[v])]
        return safe[0] if safe else ctx.options[0]
