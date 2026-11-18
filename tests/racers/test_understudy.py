from typing import override

from magsim.core.agent import Agent, SelectionDecisionContext, SelectionInteractive
from magsim.core.types import RacerStat
from magsim.engine.scenario import GameScenario, RacerConfig


def plain(idx: int, name: str = "Centaur", start_pos: int = 0) -> RacerConfig:
    return RacerConfig(idx, name, abilities=set(), start_pos=start_pos)  # pyright: ignore[reportArgumentType]


class PickNamed(Agent):
    def __init__(self, name: str) -> None:
        self.name = name

    @override
    def make_selection_decision[R](
        self,
        engine,
        ctx: SelectionDecisionContext[SelectionInteractive[R], R],
    ) -> R | None:
        return next(o for o in ctx.options if o.racer_name == self.name)  # pyright: ignore[reportAttributeAccessIssue]


def ability_names(game: GameScenario, idx: int) -> set[str]:
    return {a.name for a in game.get_racer(idx).active_abilities}


def test_understudy_copies_best_opponent_by_default(scenario: type[GameScenario]):
    game = scenario(
        [RacerConfig(0, "Understudy"), plain(1, "Banana"), plain(2, "Legs")],
        dice_rolls=[3],
    )

    assert ability_names(game, 0) == {"LongLegs", "UnderstudyMethod"}


def test_understudy_uses_agent_choice(scenario: type[GameScenario]):
    game = scenario(
        [
            RacerConfig(0, "Understudy", agent=PickNamed("Banana")),
            plain(1, "Banana"),
            plain(2, "Legs"),
        ],
        dice_rolls=[3],
    )

    assert ability_names(game, 0) == {"BananaTrip", "UnderstudyMethod"}


def test_understudy_copies_only_opponent_when_one_exists(scenario: type[GameScenario]):
    game = scenario(
        [RacerConfig(0, "Understudy"), plain(1, "Hare")],
        dice_rolls=[3],
    )

    ability = next(
        a for a in game.get_racer(0).active_abilities if a.name == "UnderstudyMethod"
    )
    assert ability.copied_racer == "Hare"


def test_understudy_copied_power_is_usable(scenario: type[GameScenario]):
    game = scenario(
        [
            RacerConfig(0, "Understudy", agent=PickNamed("Gloth")),
            RacerConfig(1, "Gloth"),
        ],
        dice_rolls=[4],
    )

    game.run_turn()

    assert game.get_racer(0).position == 3


def test_understudy_keeps_ability_when_no_opponent_exists(
    scenario: type[GameScenario],
):
    game = scenario([RacerConfig(0, "Understudy")], dice_rolls=[3])

    assert ability_names(game, 0) == {"UnderstudyMethod"}


def test_copier_of_understudy_gets_understudy_ability(
    scenario: type[GameScenario],
):
    game = scenario(
        [RacerConfig(0, "Copycat"), RacerConfig(1, "Understudy"), plain(2, "Legs")],
        dice_rolls=[3],
    )

    game.engine.replace_core_abilities(
        0,
        game.engine.instantiate_racer_abilities("Understudy"),
    )

    assert ability_names(game, 0) == {"UnderstudyMethod"}
