from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, Self, override

from magical_athlete_simulator.core.abilities import (
    Ability,
    CopyAbilityProtocol,
    copied_racer_repr,
)
from magical_athlete_simulator.core.agent import (
    Agent,
    SelectionDecisionContext,
    SelectionDecisionMixin,
)
from magical_athlete_simulator.core.events import (
    AbilityTriggeredEvent,
    AbilityTriggeredEventOrSkipped,
    GameEvent,
    PostMoveEvent,
    PostWarpEvent,
    TurnStartEvent,
)
from magical_athlete_simulator.core.state import RacerState

if TYPE_CHECKING:
    from magical_athlete_simulator.core.types import AbilityName
    from magical_athlete_simulator.engine.game_engine import GameEngine


@dataclass
class AbilityCopyLead(Ability, SelectionDecisionMixin[RacerState]):
    name: AbilityName = "CopyLead"
    triggers: tuple[type[GameEvent], ...] = (
        TurnStartEvent,
        PostMoveEvent,
        PostWarpEvent,
    )

    current_copied_racer: RacerState | Literal["start_of_game"] | None = "start_of_game"

    @property
    def _current_copied_racer_repr(self) -> str:
        if not isinstance(self.current_copied_racer, RacerState):
            raise TypeError("Unexpected type for self.current_copied_racer")

        # first check if the copied racer has a copy ability
        try:
            deep_copying_ability = next(
                a
                for a in self.current_copied_racer.active_abilities.values()
                if isinstance(a, CopyAbilityProtocol)
            )
        except StopIteration:
            # if the racer doesn't copy anyone, just return his repr
            return self.current_copied_racer.repr

        return f"{self.current_copied_racer.repr} ({copied_racer_repr(copying_ability=deep_copying_ability, copying_racer=self.current_copied_racer)})"

    @override
    def execute(
        self,
        event: GameEvent,
        owner: RacerState,
        engine: GameEngine,
        agent: Agent,
    ) -> AbilityTriggeredEventOrSkipped:
        if not isinstance(event, (TurnStartEvent, PostWarpEvent, PostMoveEvent)):
            return "skip_trigger"

        # Only for logging at start of own turn
        if isinstance(event, TurnStartEvent) and owner.idx == event.target_racer_idx:
            if self.current_copied_racer is None:
                engine.log_info(
                    f"{owner.repr} is in the sole lead and doesn't copy anyone.",
                )
            elif self.current_copied_racer == "start_of_game":
                pass
            else:
                engine.log_info(
                    f"{owner.repr} currently copies the behaviour of {self._current_copied_racer_repr}.",
                )

        # 1. Determine leaders
        active = [r for r in engine.state.racers if r.active]
        max_pos = max(r.position for r in active)
        valid_targets = engine.get_racers_at_position(
            max_pos,
            except_racer_idx=owner.idx,
        )

        # 2. If Copycat leads, they lose abilities
        if not valid_targets:
            if self.current_copied_racer is None:
                # We are already in the correct state. Do nothing.
                return "skip_trigger"

            engine.update_racer_abilities(owner.idx, new_abilities={self.name})
            engine.log_info(
                f"{owner.repr} is in the sole lead and loses {self._current_copied_racer_repr} ability.",
            )
            self.current_copied_racer = None
            return "skip_trigger"

        # Sort for deterministic behavior
        valid_targets.sort(key=lambda r: r.idx)

        # 3. Ask the Agent which leader to copy
        target = agent.make_selection_decision(
            engine,
            SelectionDecisionContext(
                source=self,
                game_state=engine.state,
                source_racer_idx=owner.idx,
                options=valid_targets,
            ),
        )

        # Nothing new to copy
        if target is None:
            engine.log_warning(
                f"{owner.repr} did not copy anyone.",
            )
            return "skip_trigger"

        if target.abilities == owner.abilities.difference(
            {self.name},
        ):
            return "skip_trigger"

        self.current_copied_racer = target
        engine.log_info(
            f"{owner.repr} decided to copy {self._current_copied_racer_repr} using {self.name}!",
        )

        # 4. Perform the Update
        new_abilities = set(target.abilities)
        new_abilities.add(self.name)
        engine.update_racer_abilities(owner.idx, new_abilities)

        return AbilityTriggeredEvent(
            responsible_racer_idx=owner.idx,
            source=self.name,
            phase=event.phase,
            target_racer_idx=target.idx,
        )

    @override
    def get_auto_selection_decision(
        self,
        engine: GameEngine,
        ctx: SelectionDecisionContext[Self, RacerState],
    ) -> RacerState:
        # Always return the first option (deterministic tie-break)
        # options are already sorted by idx in execute()
        return ctx.options[0]
