from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Self, override

from magical_athlete_simulator.core.abilities import Ability
from magical_athlete_simulator.core.agent import (
    Agent,
    SelectionDecisionContext,
    SelectionDecisionMixin,
    SelectionInteractive,
)
from magical_athlete_simulator.core.mixins import SetupPhaseMixin
from magical_athlete_simulator.core.registry import RACER_ABILITIES
from magical_athlete_simulator.core.types import RacerStat

if TYPE_CHECKING:
    from magical_athlete_simulator.core.events import (
        AbilityTriggeredEventOrSkipped,
        GameEvent,
    )
    from magical_athlete_simulator.core.types import AbilityName
    from magical_athlete_simulator.engine.game_engine import GameEngine


@dataclass
class EggCopyAbility(Ability, SetupPhaseMixin, SelectionDecisionMixin[RacerStat]):
    name: AbilityName = "EggCopy"
    triggers: tuple[type[GameEvent], ...] = ()

    @override
    def execute(
        self,
        event: GameEvent,
        owner_idx: int,
        engine: GameEngine,
        agent: Agent,
    ) -> AbilityTriggeredEventOrSkipped:
        return "skip_trigger"

    @override
    def on_setup(self, engine: GameEngine, owner_idx: int, agent: Agent) -> None:
        racer_options = engine.draw_racers(k=3)
        engine.log_info(
            f"Egg drew {', '.join(f'{r.racer_name} ({r.avg_vp:.2f} ØVP)' for r in racer_options)}.",
        )

        picked_racer = agent.make_selection_decision(
            engine,
            ctx=SelectionDecisionContext[
                SelectionInteractive[RacerStat],
                RacerStat,
            ](
                source=self,
                game_state=engine.state,
                source_racer_idx=owner_idx,
                options=racer_options,
            ),
        )
        if picked_racer is None:
            raise AssertionError(
                "Egg should always have a target to pick.",
            )

        engine.log_info(f"Egg picked {picked_racer.racer_name}!")
        engine.state.remove_racers([picked_racer.racer_name])

        picked_racer_abilities = RACER_ABILITIES[picked_racer.racer_name]
        engine.update_racer_abilities(
            racer_idx=owner_idx,
            new_abilities=engine.get_racer(owner_idx).abilities.union(
                picked_racer_abilities,
            ),
        )

    @override
    def get_auto_selection_decision(
        self,
        engine: GameEngine,
        ctx: SelectionDecisionContext[Self, RacerStat],
    ) -> RacerStat | None:
        return max(ctx.options, key=lambda r: r.avg_vp)
