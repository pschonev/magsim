from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Self, override

from magical_athlete_simulator.core.abilities import Ability, copied_racer_repr
from magical_athlete_simulator.core.agent import (
    Agent,
    SelectionDecisionContext,
    SelectionDecisionMixin,
    SelectionInteractive,
)
from magical_athlete_simulator.core.events import TurnStartEvent
from magical_athlete_simulator.core.mixins import SetupPhaseMixin
from magical_athlete_simulator.core.types import RacerName, RacerStat

if TYPE_CHECKING:
    from magical_athlete_simulator.core.events import (
        AbilityTriggeredEventOrSkipped,
        GameEvent,
    )
    from magical_athlete_simulator.core.state import ActiveRacerState
    from magical_athlete_simulator.core.types import AbilityName
    from magical_athlete_simulator.engine.game_engine import GameEngine


@dataclass
class TwinCopyAbility(Ability, SetupPhaseMixin, SelectionDecisionMixin[RacerStat]):
    name: AbilityName = "TwinCopy"
    triggers: tuple[type[GameEvent], ...] = (TurnStartEvent,)

    copied_racer: RacerName | None = None

    def _copied_racer_repr(self, owner: ActiveRacerState) -> str:
        return copied_racer_repr(self, owner)

    @override
    def execute(
        self,
        event: GameEvent,
        owner: ActiveRacerState,
        engine: GameEngine,
        agent: Agent,
    ) -> AbilityTriggeredEventOrSkipped:
        if (
            isinstance(event, TurnStartEvent)
            and owner.idx == event.target_racer_idx
            and self.copied_racer is not None
        ):
            engine.log_info(
                f"{owner.repr} acts as {self._copied_racer_repr(owner)}.",
            )
        return "skip_trigger"

    @override
    def on_setup(
        self,
        engine: GameEngine,
        owner: ActiveRacerState,
        agent: Agent,
    ) -> None:
        draws = engine.draw_racers(k=15)

        # simulate past races
        winners: list[RacerStat] = []
        for i, racers in enumerate([draws[0:5], draws[5:10], draws[10:15]]):
            weights = [r.winrate for r in racers]
            winner: RacerStat = engine.rng.choices(
                population=racers,
                k=1,
                weights=weights if sum(weights) else None,
            )[0]
            participants = ", ".join(
                [
                    f"{r.racer_name} ({r.winrate * 100:.1f}% WR)"
                    for r in racers
                    if r.racer_name != winner.racer_name
                ],
            )
            engine.log_info(
                f"Race {i}: {winner.racer_name} ({winner.avg_vp:.2f} ØVP, {winner.winrate * 100:.1f}% WR) won the race against {participants}",
            )
            winners.append(winner)

        picked_racer = agent.make_selection_decision(
            engine,
            ctx=SelectionDecisionContext[
                SelectionInteractive[RacerStat],
                RacerStat,
            ](
                source=self,
                event=None,
                game_state=engine.state,
                source_racer_idx=owner.idx,
                options=winners,
            ),
        )
        if picked_racer is None:
            raise AssertionError(
                "Twin should always have a target to pick.",
            )

        engine.log_info(f"{owner.repr} picked {picked_racer.racer_name}!")
        self.copied_racer = picked_racer.racer_name
        engine.state.remove_racers([picked_racer.racer_name])

        # Instantiate fresh abilities
        new_core = engine.instantiate_racer_abilities(picked_racer.racer_name)
        # Keep Twin ability
        new_core.append(self)

        engine.replace_core_abilities(owner.idx, new_core)

    @override
    def get_auto_selection_decision(
        self,
        engine: GameEngine,
        ctx: SelectionDecisionContext[Self, RacerStat],
    ) -> RacerStat | None:
        return max(ctx.options, key=lambda r: r.avg_vp)
