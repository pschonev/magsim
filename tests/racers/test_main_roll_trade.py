from typing import override

from magsim.core.agent import (
    Agent,
    BooleanInteractive,
    DecisionContext,
    SelectionDecisionContext,
    SelectionInteractive,
)
from magsim.engine.scenario import GameScenario, RacerConfig


class AlwaysUse(Agent):
    def __init__(self) -> None:
        self.asked: list[str] = []

    @override
    def make_boolean_decision(
        self, engine, ctx: DecisionContext[BooleanInteractive]
    ) -> bool:
        self.asked.append(ctx.source.name)  # pyright: ignore[reportAttributeAccessIssue]
        return True

    @override
    def make_selection_decision[R](
        self,
        engine,
        ctx: SelectionDecisionContext[SelectionInteractive[R], R],
    ) -> R | None:
        self.asked.append(ctx.source.name)  # pyright: ignore[reportAttributeAccessIssue]
        return max(ctx.options, key=lambda o: o.position)  # pyright: ignore[reportAttributeAccessIssue]


def test_legs_and_mole_trade_main_roll_only_once(scenario: type[GameScenario]):
    agent = AlwaysUse()
    game = scenario(
        [
            RacerConfig(0, "Legs", abilities={"LongLegs", "MoleTunnel"}, agent=agent),
            RacerConfig(1, "Centaur", start_pos=20),
        ],
        dice_rolls=[1],
    )

    game.run_turn()

    assert len(agent.asked) == 1
    assert (
        game.get_racer(0).position == {"LongLegs": 5, "MoleTunnel": 6}[agent.asked[0]]
    )


def test_legs_and_flip_flop_trade_main_roll_only_once(scenario: type[GameScenario]):
    agent = AlwaysUse()
    game = scenario(
        [
            RacerConfig(0, "Legs", abilities={"LongLegs", "FlipFlopSwap"}, agent=agent),
            RacerConfig(1, "Centaur", start_pos=20),
        ],
        dice_rolls=[1],
    )

    game.run_turn()

    assert len(agent.asked) == 1
    expected = {"LongLegs": (5, 20), "FlipFlopSwap": (20, 0)}[agent.asked[0]]
    assert (game.get_racer(0).position, game.get_racer(1).position) == expected


def test_tripped_legs_does_not_trigger(scenario: type[GameScenario]):
    game = scenario(
        [RacerConfig(0, "Legs"), RacerConfig(1, "Scoocher", start_pos=10)],
        dice_rolls=[1],
    )
    game.get_racer(0).tripped = True

    game.run_turn()

    assert game.get_racer(0).position == 0
    assert game.get_racer(1).position == 10


def test_tripped_hare_does_not_trigger(scenario: type[GameScenario]):
    game = scenario(
        [
            RacerConfig(0, "Hare", start_pos=15),
            RacerConfig(1, "Scoocher", start_pos=10),
        ],
        dice_rolls=[1],
    )
    game.get_racer(0).tripped = True

    game.run_turn()

    assert game.get_racer(0).position == 15
    assert game.get_racer(1).position == 10


def test_mush_with_granted_legs_and_mole_trades_once(scenario: type[GameScenario]):
    agent = AlwaysUse()
    game = scenario(
        [
            RacerConfig(0, "Mush", agent=agent),
            RacerConfig(1, "Centaur", start_pos=20),
        ],
        dice_rolls=[1],
    )
    for name in ("Legs", "Mole"):
        for ability in game.engine.instantiate_racer_abilities(name):
            game.engine.grant_ability(0, ability, persistent=True)

    game.run_turn()

    assert len(agent.asked) == 1
    assert (
        game.get_racer(0).position == {"LongLegs": 5, "MoleTunnel": 6}[agent.asked[0]]
    )
