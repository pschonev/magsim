"""Shared builders for the dice-wish tests: real engines, granted powers, real agent decisions."""

from collections.abc import Sequence
from typing import cast

from magsim.core.abilities import Ability
from magsim.core.agent import (
    BooleanInteractive,
    DecisionContext,
    SelectionDecisionContext,
    SelectionInteractive,
)
from magsim.core.state import RollState
from magsim.core.types import D6Values, RacerName
from magsim.engine.board import Board, SpaceModifier, VictoryPointTile
from magsim.engine.game_engine import GameEngine
from magsim.engine.scenario import GameScenario, RacerConfig
from magsim.racers.cheatah import FACES, CheatahSleightOfPaw
from magsim.racers.mr_dice_guy import MrDiceGuyMoreAbility
from magsim.racers.mush import MushGlobsterMashAbility

BOARD_LENGTH = 30
DECIDER_IDX = 0
CHEATAH_SAMPLES = 400
DEFAULT_SEED = 0


def build_engine(
    name: RacerName,
    *,
    position: int = 0,
    powers: Sequence[RacerName] = (),
    vp_tile_at: int | None = None,
    other: RacerName = "Centaur",
    seed: int = DEFAULT_SEED,
) -> GameEngine:
    """Racer 0 is `name` at `position` holding persistent `powers`; racer 1 is a bystander."""
    features: dict[int, list[SpaceModifier]] = {}
    if vp_tile_at is not None:
        features[vp_tile_at] = [VictoryPointTile(owner_idx=None)]
    scenario = GameScenario(
        racers_config=[
            RacerConfig(DECIDER_IDX, name, start_pos=position),
            RacerConfig(1, other),
        ],
        board=Board(length=BOARD_LENGTH, static_features=features),
        seed=seed,
    )
    engine = scenario.engine
    for power in powers:
        for ability in engine.instantiate_racer_abilities(power):
            engine.grant_ability(DECIDER_IDX, ability, persistent=True)
    return engine


def find_ability[A: Ability](engine: GameEngine, kind: type[A]) -> A:
    for ability in engine.get_racer(DECIDER_IDX).active_abilities:
        if isinstance(ability, kind):
            return ability
    msg = f"{kind.__name__} not active on racer {DECIDER_IDX}"
    raise AssertionError(msg)


def set_drawn_powers(engine: GameEngine, drawn: Sequence[RacerName]) -> None:
    """Record the powers Mush has drawn so far (the granted abilities are set up separately)."""
    find_ability(engine, MushGlobsterMashAbility).copied_racers = list(drawn)


def pick_duplicate(engine: GameEngine, duplicates: Sequence[int]) -> int | None:
    """Ask the racer's agent which duplicated value Mr Dice Guy takes as the main move."""
    ctx = SelectionDecisionContext[SelectionInteractive[int], int](
        source=find_ability(engine, MrDiceGuyMoreAbility),
        event=None,
        game_state=engine.state,
        source_racer_idx=DECIDER_IDX,
        options=sorted(duplicates, reverse=True),
    )
    return engine.get_agent(DECIDER_IDX).make_selection_decision(engine, ctx)


def cheatah_support(engine: GameEngine) -> frozenset[int]:
    """Faces Cheatah's agent ever picks over a fixed number of draws from the seeded rng."""
    ctx = SelectionDecisionContext[SelectionInteractive[int], int](
        source=find_ability(engine, CheatahSleightOfPaw),
        event=None,
        game_state=engine.state,
        source_racer_idx=DECIDER_IDX,
        options=FACES,
    )
    agent = engine.get_agent(DECIDER_IDX)
    picks = [
        agent.make_selection_decision(engine, ctx) for _ in range(CHEATAH_SAMPLES)
    ]
    assert None not in picks
    return frozenset(face for face in picks if face is not None)


def rerolls[A: Ability](
    engine: GameEngine,
    kind: type[A],
    rolled: D6Values,
    final: int | None = None,
) -> bool:
    """Ask the racer's agent whether `kind` (a reroll ability) rerolls the pending roll."""
    engine.state.roll_state = RollState(
        serial_id=1,
        dice_value=rolled,
        dice_values=(rolled,),
        base_value=rolled,
        final_value=rolled if final is None else final,
    )
    ctx = DecisionContext[BooleanInteractive](
        source=cast("BooleanInteractive", find_ability(engine, kind)),
        event=None,
        game_state=engine.state,
        source_racer_idx=DECIDER_IDX,
    )
    return engine.get_agent(DECIDER_IDX).make_boolean_decision(engine, ctx)
