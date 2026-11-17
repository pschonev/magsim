from magsim.core.events import MoveCmdEvent, Phase
from magsim.engine.scenario import GameScenario, RacerConfig


def plain(idx: int, start_pos: int = 0) -> RacerConfig:
    return RacerConfig(idx, "Centaur", abilities=set(), start_pos=start_pos)


def streaker(start_pos: int = 0) -> RacerConfig:
    return RacerConfig(0, "Streaker", start_pos=start_pos)


def test_streaker_gains_vp_when_passing(scenario: type[GameScenario]):
    game = scenario([streaker(), plain(1, 2)], dice_rolls=[4])

    game.run_turn()

    assert game.get_racer(0).position == 4
    assert game.get_racer(0).victory_points == 1


def test_streaker_gains_one_vp_for_multiple_passes(scenario: type[GameScenario]):
    game = scenario([streaker(), plain(1, 1), plain(2, 2), plain(3, 3)], dice_rolls=[6])

    game.run_turn()

    assert game.get_racer(0).victory_points == 1


def test_streaker_no_vp_without_pass(scenario: type[GameScenario]):
    game = scenario([streaker(), plain(1, 10)], dice_rolls=[3])

    game.run_turn()

    assert game.get_racer(0).victory_points == 0


def test_streaker_gains_vp_on_each_main_move(scenario: type[GameScenario]):
    game = scenario([streaker(), plain(1, 2), plain(2, 7)], dice_rolls=[4, 1, 1, 6])

    game.run_turns(4)

    assert game.get_racer(0).victory_points == 2


def test_streaker_ignores_passes_during_non_main_move(
    scenario: type[GameScenario],
):
    game = scenario([streaker(), plain(1, 2)], dice_rolls=[1])
    game.engine.push_event(
        MoveCmdEvent(
            target_racer_idx=0,
            distance=4,
            source="System",
            phase=Phase.SYSTEM,
            responsible_racer_idx=None,
        ),
    )

    game.run_turn()

    assert game.get_racer(0).position == 5
    assert game.get_racer(0).victory_points == 0
