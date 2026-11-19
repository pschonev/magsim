from typing import override

from magsim.ai.baseline_agent import BaselineAgent
from magsim.core.agent import Agent, SelectionDecisionContext, SelectionInteractive
from magsim.core.events import Phase, WarpCmdEvent
from magsim.core.types import RacerName
from magsim.engine.scenario import GameScenario, RacerConfig


def cfg(idx: int, name: str, start_pos: int = 0) -> RacerConfig:
    return RacerConfig(idx, name, start_pos=start_pos)  # pyright: ignore[reportArgumentType]


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


def understudy(idx: int, start_pos: int = 0) -> RacerConfig:
    return RacerConfig(
        idx,
        "Understudy",
        start_pos=start_pos,
        agent=PickNamed("HogKnight"),
    )


def hogs(game: GameScenario, idx: int) -> int:
    return sum(m.name == "HogKnightHog" for m in game.get_racer(idx).modifiers)


def warp(game: GameScenario, idx: int, tile: int) -> None:
    game.engine.push_event(
        WarpCmdEvent(
            target_racer_idx=idx,
            target_tile=tile,
            source="System",
            phase=Phase.PRE_MAIN,
            responsible_racer_idx=None,
        ),
    )


def leave_only(game: GameScenario, *names: RacerName) -> None:
    game.state.remove_racers(
        [n for n in game.state.available_racers if n not in names],
    )


def test_hog_adds_two_to_the_riders_main_move(scenario: type[GameScenario]):
    game = scenario([cfg(0, "HogKnight"), cfg(1, "Centaur", 20)], dice_rolls=[3])

    game.run_turn()

    assert game.get_racer(0).position == 5


def test_hog_bonus_applies_every_turn(scenario: type[GameScenario]):
    game = scenario(
        [cfg(0, "HogKnight"), cfg(1, "Centaur", 20)],
        dice_rolls=[3, 1, 3],
    )

    game.run_turns(3)

    assert game.get_racer(0).position == 10


def test_hog_knight_starts_with_exactly_one_hog(scenario: type[GameScenario]):
    game = scenario([cfg(0, "HogKnight"), cfg(1, "Centaur", 20)], dice_rolls=[3])

    assert hogs(game, 0) == 1
    assert hogs(game, 1) == 0


def test_hog_does_not_boost_other_racers(scenario: type[GameScenario]):
    game = scenario([cfg(0, "HogKnight"), cfg(1, "Centaur", 20)], dice_rolls=[3, 3])

    game.run_turns(2)

    assert game.get_racer(1).position == 23


def test_stopping_on_the_rider_steals_the_hog(scenario: type[GameScenario]):
    """HogKnight 5 -> 8 (1 + 2). Centaur 3 -> 8 and takes the hog."""
    game = scenario(
        [cfg(0, "HogKnight", 5), cfg(1, "Centaur", 3)],
        dice_rolls=[1, 5],
    )

    game.run_turns(2)

    assert hogs(game, 0) == 0
    assert hogs(game, 1) == 1


def test_thief_gets_the_bonus_and_victim_loses_it(scenario: type[GameScenario]):
    game = scenario(
        [cfg(0, "HogKnight", 5), cfg(1, "LovableLoser", 3)],
        dice_rolls=[1, 5, 1, 1],
    )

    game.run_turns(4)

    assert game.get_racer(0).position == 9
    assert game.get_racer(1).position == 11


def test_passing_the_rider_does_not_steal_the_hog(scenario: type[GameScenario]):
    """HogKnight 5 -> 8, Legs 6 -> 10 (3 + 1) passes him without stopping."""
    game = scenario(
        [cfg(0, "HogKnight", 5), cfg(1, "Legs", 6)],
        dice_rolls=[1, 3],
    )

    game.run_turns(2)

    assert hogs(game, 0) == 1
    assert hogs(game, 1) == 0


def test_tripped_rider_keeps_the_hog(scenario: type[GameScenario]):
    game = scenario([cfg(0, "HogKnight"), cfg(1, "Centaur", 20)], dice_rolls=[3])
    game.engine.get_racer(0).tripped = True

    game.run_turn()

    assert hogs(game, 0) == 1
    assert game.get_racer(0).position == 0


def test_hog_travels_with_its_rider_on_a_warp(scenario: type[GameScenario]):
    game = scenario([cfg(0, "HogKnight"), cfg(1, "Centaur", 20)], dice_rolls=[3])
    warp(game, 0, 10)

    game.run_turn()

    assert hogs(game, 0) == 1
    assert game.get_racer(0).position == 15


def test_warping_onto_the_rider_steals_the_hog(scenario: type[GameScenario]):
    game = scenario(
        [cfg(0, "HogKnight", 5), cfg(1, "Centaur", 20)],
        dice_rolls=[1],
    )
    warp(game, 1, 5)

    game.run_turn()

    assert hogs(game, 0) == 0
    assert hogs(game, 1) == 1


def test_finishing_rider_with_a_hog_finishes_normally(scenario: type[GameScenario]):
    game = scenario([cfg(0, "HogKnight", 28), cfg(1, "Centaur", 20)], dice_rolls=[1])

    game.run_turn()

    assert game.get_racer(0).finish_position == 1


def test_mouth_takes_the_hog_before_eating_the_rider(scenario: type[GameScenario]):
    """Stopping on the rider steals first, so the hog survives the rider's elimination."""
    game = scenario(
        [cfg(0, "Mouth"), cfg(1, "HogKnight", 4), cfg(2, "Centaur", 20)],
        dice_rolls=[4],
    )

    game.run_turn()

    assert game.get_racer(1).eliminated
    assert hogs(game, 0) == 1


def test_stopper_takes_every_hog_from_a_double_rider(scenario: type[GameScenario]):
    """Understudy (copying HogKnight) takes HogKnight's hog and has two, then Centaur
    stops on the Understudy and takes both.
    """
    game = scenario(
        [understudy(0), cfg(1, "HogKnight", 5), cfg(2, "Centaur", 1)],
        dice_rolls=[3, 1, 4],
    )

    game.run_turn()
    assert hogs(game, 0) == 2
    assert hogs(game, 1) == 0

    game.run_turns(2)

    assert hogs(game, 0) == 0
    assert hogs(game, 2) == 2


def test_understudy_copying_hog_knight_gets_its_own_hog(
    scenario: type[GameScenario],
):
    game = scenario([understudy(0), cfg(1, "HogKnight", 20)], dice_rolls=[3])

    assert hogs(game, 0) == 1
    assert hogs(game, 1) == 1


def test_two_hogs_stack_for_the_main_move(scenario: type[GameScenario]):
    """An Understudy that steals the original hog rides two and moves 3 + 4."""
    game = scenario(
        [understudy(0), cfg(1, "HogKnight", 3), cfg(2, "Centaur", 20)],
        dice_rolls=[1, 1, 1, 3],
    )

    game.run_turn()
    assert game.get_racer(0).position == 3
    assert hogs(game, 0) == 2

    game.run_turns(3)

    assert game.get_racer(0).position == 10


def test_doppelgangster_gains_the_power_but_no_hog(scenario: type[GameScenario]):
    """Piggyback is a before-the-race power, so copying it later gives no hog."""
    game = scenario(
        [
            cfg(0, "Doppelgangster"),
            cfg(1, "HogKnight", 28),
            cfg(2, "Scoocher"),
            cfg(3, "Hare"),
        ],
        dice_rolls=[1, 1],
    )

    game.run_turns(2)

    assert game.get_racer(1).eliminated
    assert "HogKnightPiggyback" in {a.name for a in game.get_racer(0).active_abilities}
    assert hogs(game, 0) == 0


def test_mush_drawing_hog_knight_gets_no_hog(scenario: type[GameScenario]):
    game = scenario(
        [
            RacerConfig(0, "Mush", agent=BaselineAgent()),  # pyright: ignore[reportArgumentType]
            cfg(1, "Centaur", 20),
        ],
        dice_rolls=[1],
    )
    leave_only(game, "HogKnight")

    game.run_turn()

    assert hogs(game, 0) == 0
    assert game.get_racer(0).position == 1
