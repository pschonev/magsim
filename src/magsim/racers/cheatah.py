from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Self, override

from magsim.ai.evaluation import (
    banned_faces,
    get_benefit_at,
    get_current_modifiers,
    get_hazard_at,
    wished_faces,
)
from magsim.core.abilities import Ability
from magsim.core.agent import (
    Agent,
    SelectionDecisionContext,
    SelectionDecisionMixin,
    SelectionInteractive,
)
from magsim.core.events import (
    AbilityTriggeredEvent,
    AbilityTriggeredEventOrSkipped,
    GameEvent,
    TurnStartEvent,
)

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from magsim.core.state import ActiveRacerState
    from magsim.core.types import AbilityName
    from magsim.engine.game_engine import GameEngine

FACES = (1, 2, 3, 4, 5, 6)
BASELINE_FACE = 6


def face_utilities(
    engine: GameEngine,
    me: ActiveRacerState,
    faces: Sequence[int],
) -> dict[int, int]:
    """Banned and hazard faces are dropped; the rest are ranked (benefit tile, wished, distance), utility = rank from 1; wishes keep only wished and benefit faces."""
    mods = get_current_modifiers(engine, me.idx)
    banned = banned_faces(engine, me)
    wished = wished_faces(engine, me)

    def landing(face: int) -> int:
        return me.position + face + mods

    def has_benefit(face: int) -> bool:
        return get_benefit_at(engine, landing(face)) is not None

    allowed = [f for f in faces if f not in banned] or list(faces)
    safe = [f for f in allowed if get_hazard_at(engine, landing(f)) is None]
    ranked = sorted(safe, key=lambda f: (has_benefit(f), f in wished, landing(f)))
    utilities = {face: rank for rank, face in enumerate(ranked, start=1)}
    if not wished:
        return utilities
    kept = {f: u for f, u in utilities.items() if f in wished or has_benefit(f)}
    return kept or utilities


def solve_mix(
    utilities: Mapping[int, int],
) -> tuple[dict[int, float], dict[int, float]]:
    """Equilibrium of "Cheatah gains u_k unless k is guessed": returns (pick mix, guess mix). No positive face: empty mixes."""
    if len(utilities) == 0:
        return {}, {}
    ranked = sorted(utilities, key=utilities.__getitem__, reverse=True)
    for size in range(len(ranked), 1, -1):
        support = ranked[:size]
        inverse_sum = sum(1 / utilities[face] for face in support)
        value = (size - 1) / inverse_sum
        if utilities[support[-1]] >= value:
            pick = {face: 1 / (utilities[face] * inverse_sum) for face in support}
            guess = {face: 1 - value / utilities[face] for face in support}
            return pick, guess
    return {ranked[0]: 1.0}, {ranked[0]: 1.0}


def sample(engine: GameEngine, mix: Mapping[int, float]) -> int:
    return engine.rng.choices(list(mix), weights=list(mix.values()))[0]


@dataclass
class CheatahSleightOfPaw(Ability, SelectionDecisionMixin[int]):
    name: AbilityName = "CheatahSleightOfPaw"
    triggers: tuple[type[GameEvent], ...] = (TurnStartEvent,)

    @override
    def execute(
        self,
        event: GameEvent,
        owner: ActiveRacerState,
        engine: GameEngine,
        agent: Agent,
    ) -> AbilityTriggeredEventOrSkipped:
        if (
            not isinstance(event, TurnStartEvent)
            or event.target_racer_idx != owner.idx
            or not engine.can_replace_main_roll(owner.idx)
        ):
            return "skip_trigger"

        face = agent.make_selection_decision(
            engine,
            ctx=SelectionDecisionContext[SelectionInteractive[int], int](
                source=self,
                event=event,
                game_state=engine.state,
                source_racer_idx=owner.idx,
                options=FACES,
            ),
        )
        if face is None:
            return "skip_trigger"

        _, guess_mix = solve_mix(face_utilities(engine, owner, FACES))
        guess = sample(engine, guess_mix) if len(guess_mix) > 0 else None

        if face == guess:
            engine.log_info(
                f"{owner.repr} sets the die to {face} but it is guessed: no main move.",
            )
            engine.skip_main_move(
                responsible_racer_idx=owner.idx,
                source=self.name,
                skipped_racer_idx=owner.idx,
            )
        else:
            engine.log_info(f"{owner.repr} sets the die to {face} (guessed {guess}).")
            owner.roll_override = (self.name, face)

        return AbilityTriggeredEvent(
            responsible_racer_idx=owner.idx,
            source=self.name,
            phase=event.phase,
            target_racer_idx=owner.idx,
            detail=face,
        )

    @override
    def get_baseline_selection_decision(
        self,
        engine: GameEngine,
        ctx: SelectionDecisionContext[Self, int],
    ) -> int | None:
        return BASELINE_FACE

    @override
    def get_auto_selection_decision(
        self,
        engine: GameEngine,
        ctx: SelectionDecisionContext[Self, int],
    ) -> int | None:
        if (me := engine.get_active_racer(ctx.source_racer_idx)) is None:
            return None
        pick, _ = solve_mix(face_utilities(engine, me, ctx.options))
        if len(pick) == 0:
            return max(ctx.options)
        return sample(engine, pick)
