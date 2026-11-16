from magsim.engine.scenario import GameScenario, RacerConfig


def plain(idx: int, start_pos: int = 0) -> RacerConfig:
    return RacerConfig(idx, "Centaur", abilities=set(), start_pos=start_pos)


def test_speed_demon_without_vp_gets_no_bonus(scenario: type[GameScenario]):
    game = scenario([RacerConfig(0, "SpeedDemon"), plain(1, 10)], dice_rolls=[3])

    game.run_turn()

    assert game.get_racer(0).position == 3


def test_speed_demon_gets_plus_one_per_vp(scenario: type[GameScenario]):
    game = scenario([RacerConfig(0, "SpeedDemon"), plain(1, 10)], dice_rolls=[3])
    game.get_racer(0).victory_points = 2

    game.run_turn()

    assert game.get_racer(0).position == 5


def test_speed_demon_bonus_counts_all_vp_held(scenario: type[GameScenario]):
    game = scenario([RacerConfig(0, "SpeedDemon"), plain(1, 20)], dice_rolls=[1])
    game.get_racer(0).victory_points = 5

    game.run_turn()

    assert game.get_racer(0).position == 6


def test_speed_demon_leading_by_three_survives(scenario: type[GameScenario]):
    game = scenario(
        [RacerConfig(0, "SpeedDemon", start_pos=9), plain(1, 6), plain(2, 6)],
        dice_rolls=[1],
    )

    game.run_turn()

    speed_demon = game.get_racer(0)
    assert speed_demon.eliminated is False
    assert speed_demon.position == 10


def test_speed_demon_leading_by_four_is_eliminated_before_rolling(
    scenario: type[GameScenario],
):
    game = scenario(
        [RacerConfig(0, "SpeedDemon", start_pos=10), plain(1, 6), plain(2, 6)],
        dice_rolls=[6],
    )

    game.run_turn()

    speed_demon = game.get_racer(0)
    assert speed_demon.eliminated is True
    assert speed_demon.position is None
    assert speed_demon.abilities == set()
    assert game.state.race_active is True


def test_speed_demon_leading_by_more_than_four_is_eliminated(
    scenario: type[GameScenario],
):
    game = scenario(
        [RacerConfig(0, "SpeedDemon", start_pos=15), plain(1, 6), plain(2, 6)],
        dice_rolls=[1],
    )

    game.run_turn()

    assert game.get_racer(0).eliminated is True


def test_speed_demon_lead_is_measured_against_the_best_other_racer(
    scenario: type[GameScenario],
):
    game = scenario(
        [RacerConfig(0, "SpeedDemon", start_pos=10), plain(1, 2), plain(2, 7)],
        dice_rolls=[1],
    )

    game.run_turn()

    assert game.get_racer(0).eliminated is False


def test_speed_demon_tied_or_behind_survives(scenario: type[GameScenario]):
    game = scenario(
        [RacerConfig(0, "SpeedDemon", start_pos=5), plain(1, 5), plain(2, 12)],
        dice_rolls=[1],
    )

    game.run_turn()

    assert game.get_racer(0).eliminated is False
    assert game.get_racer(0).position == 6


def test_speed_demon_is_only_checked_at_its_own_turn_start(
    scenario: type[GameScenario],
):
    game = scenario(
        [plain(0, 5), RacerConfig(1, "SpeedDemon", start_pos=10), plain(2, 5)],
        dice_rolls=[1, 1, 1],
    )

    game.run_turn()

    assert game.get_racer(1).eliminated is False

    game.run_turn()

    assert game.get_racer(1).eliminated is True


def test_speed_demon_elimination_in_two_racer_game_finishes_the_other(
    scenario: type[GameScenario],
):
    game = scenario(
        [RacerConfig(0, "SpeedDemon", start_pos=10), plain(1, 5)],
        dice_rolls=[1],
    )

    game.run_turn()

    other = game.get_racer(1)
    assert game.state.race_active is False
    assert other.finish_position == 1
    assert other.victory_points == 4
