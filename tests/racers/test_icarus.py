from magsim.engine.scenario import GameScenario, RacerConfig
from magsim.racers.icarus import IcarusFlightRisk


def plain(idx: int, start_pos: int = 0) -> RacerConfig:
    return RacerConfig(idx, "Centaur", abilities=set(), start_pos=start_pos)


def test_icarus_gets_plus_three_to_main_move(scenario: type[GameScenario]):
    game = scenario([RacerConfig(0, "Icarus"), plain(1, 10)], dice_rolls=[3])

    game.run_turn()

    assert game.get_racer(0).position == 6


def test_icarus_rolling_below_six_survives(scenario: type[GameScenario]):
    game = scenario([RacerConfig(0, "Icarus"), plain(1, 10)], dice_rolls=[5])

    game.run_turn()

    icarus = game.get_racer(0)
    assert icarus.eliminated is False
    assert icarus.position == 8


def test_icarus_rolling_six_is_eliminated_without_moving(scenario: type[GameScenario]):
    game = scenario(
        [RacerConfig(0, "Icarus", start_pos=4), plain(1, 10), plain(2, 12)],
        dice_rolls=[6],
    )

    game.run_turn()

    icarus = game.get_racer(0)
    assert icarus.eliminated is True
    assert icarus.position is None
    assert icarus.abilities == set()
    assert game.state.race_active is True


def test_icarus_elimination_event_names_icarus_as_cause(scenario: type[GameScenario]):
    game = scenario(
        [RacerConfig(0, "Icarus"), plain(1, 10), plain(2, 12)],
        dice_rolls=[6],
    )

    game.run_turn()

    assert game.get_racer(0).eliminated is True
    assert game.get_racer(1).eliminated is False
    assert game.get_racer(2).eliminated is False


def test_icarus_elimination_in_two_racer_game_finishes_the_other(
    scenario: type[GameScenario],
):
    game = scenario([RacerConfig(0, "Icarus"), plain(1, 10)], dice_rolls=[6])

    game.run_turn()

    other = game.get_racer(1)
    assert game.state.race_active is False
    assert other.finish_position == 1
    assert other.victory_points == 4


def test_other_racers_rolling_six_do_not_eliminate_icarus(
    scenario: type[GameScenario],
):
    game = scenario([plain(0), RacerConfig(1, "Icarus", start_pos=5)], dice_rolls=[6])

    game.run_turn()

    assert game.get_racer(1).eliminated is False


def test_icarus_roll_override_of_six_does_not_eliminate(
    scenario: type[GameScenario],
):
    game = scenario(
        [RacerConfig(0, "Mole"), plain(1, 20), plain(2, 22)],
        dice_rolls=[3],
    )
    game.engine.grant_ability(0, IcarusFlightRisk())

    game.run_turn()

    mole = game.get_racer(0)
    assert mole.eliminated is False
    assert mole.position == 9
