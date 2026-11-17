from magsim.engine.scenario import GameScenario, RacerConfig


def plain(idx: int, start_pos: int = 0) -> RacerConfig:
    return RacerConfig(idx, "Centaur", abilities=set(), start_pos=start_pos)


def athlete(start_pos: int = 0) -> RacerConfig:
    return RacerConfig(0, "MagicalAthlete", start_pos=start_pos)


def test_roll_1_moves_seven(scenario: type[GameScenario]):
    game = scenario([athlete(), plain(1, 20)], dice_rolls=[1])

    game.run_turn()

    assert game.get_racer(0).position == 7


def test_fixed_move_ignores_roll_modifiers(scenario: type[GameScenario]):
    game = scenario(
        [athlete(), RacerConfig(1, "Coach", start_pos=0), plain(2, 20)],
        dice_rolls=[1],
    )

    game.run_turn()

    assert game.get_racer(0).position == 7


def test_roll_2_warps_all_tied_last_to_owner(scenario: type[GameScenario]):
    game = scenario(
        [athlete(10), plain(1, 2), plain(2, 2), plain(3, 5)],
        dice_rolls=[2],
    )

    game.run_turn()

    assert game.get_racer(0).position == 10
    assert game.get_racer(1).position == 10
    assert game.get_racer(2).position == 10
    assert game.get_racer(3).position == 5


def test_roll_2_does_nothing_when_owner_tied_for_last(
    scenario: type[GameScenario],
):
    game = scenario([athlete(2), plain(1, 2), plain(2, 9)], dice_rolls=[2])

    game.run_turn()

    assert [r.position for r in game.state.racers] == [2, 2, 9]


def test_roll_3_warps_to_lead_and_trips_everyone_there(
    scenario: type[GameScenario],
):
    game = scenario(
        [athlete(), plain(1, 10), plain(2, 10), plain(3, 4)],
        dice_rolls=[3],
    )

    game.run_turn()

    assert game.get_racer(0).position == 10
    assert not game.get_racer(0).tripped
    assert game.get_racer(1).tripped
    assert game.get_racer(2).tripped
    assert not game.get_racer(3).tripped


def test_roll_4_moves_four_and_takes_extra_turn(scenario: type[GameScenario]):
    game = scenario([athlete(), plain(1, 20)], dice_rolls=[4])

    game.run_turn()

    assert game.get_racer(0).position == 4
    assert game.state.current_racer_idx == 0


def test_roll_5_pushes_all_tied_leaders_back(scenario: type[GameScenario]):
    game = scenario(
        [athlete(), plain(1, 10), plain(2, 10), plain(3, 4)],
        dice_rolls=[5],
    )

    game.run_turn()

    assert [r.position for r in game.state.racers] == [0, 5, 5, 4]


def test_roll_5_pushes_owner_back_when_leading(scenario: type[GameScenario]):
    game = scenario([athlete(10), plain(1, 4)], dice_rolls=[5])

    game.run_turn()

    assert game.get_racer(0).position == 5


def test_roll_5_clamps_at_start(scenario: type[GameScenario]):
    game = scenario([athlete(), plain(1, 3)], dice_rolls=[5])

    game.run_turn()

    assert game.get_racer(1).position == 0


def test_roll_6_moves_six_and_trips_passed_racers(scenario: type[GameScenario]):
    game = scenario(
        [athlete(), plain(1, 2), plain(2, 5), plain(3, 6)],
        dice_rolls=[6],
    )

    game.run_turn()

    assert game.get_racer(0).position == 6
    assert game.get_racer(1).tripped
    assert game.get_racer(2).tripped
    assert not game.get_racer(3).tripped


def test_roll_6_trip_triggers_scoocher(scenario: type[GameScenario]):
    game = scenario(
        [athlete(), plain(1, 2), RacerConfig(2, "Scoocher", start_pos=20)],
        dice_rolls=[6],
    )

    game.run_turn()

    assert game.get_racer(2).position == 22
