from typing import override

from magsim.core.agent import (
    Agent,
    BooleanInteractive,
    DecisionContext,
    SelectionDecisionContext,
    SelectionInteractive,
)
from magsim.engine.scenario import GameScenario, RacerConfig


class SwapWithLeader(Agent):
    """Always uses the power and picks the racer furthest ahead."""

    @override
    def make_boolean_decision(self, engine, ctx: DecisionContext[BooleanInteractive]) -> bool:
        return True

    @override
    def make_selection_decision[R](
        self,
        engine,
        ctx: SelectionDecisionContext[SelectionInteractive[R], R],
    ) -> R | None:
        return max(ctx.options, key=lambda o: o.position)  # pyright: ignore[reportAttributeAccessIssue]


def test_flip_flop_swaps_places_with_huge_baby(scenario: type[GameScenario]):
    """A swap is simultaneous, so Huge Baby's blocker leaves with it and does not redirect Flip Flop."""
    game = scenario(
        [
            RacerConfig(0, "FlipFlop", start_pos=12, agent=SwapWithLeader()),
            RacerConfig(1, "HugeBaby", start_pos=13),
            RacerConfig(2, "Centaur", abilities=set(), start_pos=5),
        ],
        dice_rolls=[1],
    )

    game.run_turn()

    assert game.get_racer(0).position == 13
    assert game.get_racer(1).position == 12


def test_huge_baby_still_blocks_a_racer_warping_onto_it(scenario: type[GameScenario]):
    """Outside a swap, a racer warping onto Huge Baby's space is put behind it."""
    game = scenario(
        [
            RacerConfig(0, "Hypnotist", start_pos=13, agent=SwapWithLeader()),
            RacerConfig(1, "HugeBaby", start_pos=13),
            RacerConfig(2, "Centaur", abilities=set(), start_pos=20),
        ],
        dice_rolls=[1],
    )

    game.run_turn()

    assert game.get_racer(2).position == 12
