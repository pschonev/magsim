from magsim.engine.scenario import GameScenario, RacerConfig

CANCEL_VP = 3


def plain(idx: int, start_pos: int = 0) -> RacerConfig:
    return RacerConfig(idx, "Centaur", abilities=set(), start_pos=start_pos)


def test_spoilsport_cancels_race_when_all_others_five_ahead(
    scenario: type[GameScenario],
):
    game = scenario(
        [RacerConfig(0, "Spoilsport"), plain(1, 5), plain(2, 9)],
        dice_rolls=[3],
    )

    game.run_turn()

    assert not game.state.race_active
    assert game.get_racer(0).victory_points == CANCEL_VP
    assert game.get_racer(0).position == 0


def test_spoilsport_does_not_cancel_when_one_racer_is_only_four_ahead(
    scenario: type[GameScenario],
):
    game = scenario(
        [RacerConfig(0, "Spoilsport"), plain(1, 5), plain(2, 4)],
        dice_rolls=[3],
    )

    game.run_turn()

    assert game.state.race_active
    assert game.get_racer(0).victory_points == 0
    assert game.get_racer(0).position == 3


def test_spoilsport_ignores_finished_and_eliminated_racers(
    scenario: type[GameScenario],
):
    game = scenario(
        [RacerConfig(0, "Spoilsport", start_pos=3), plain(1, 10), plain(2, 4), plain(3, 5)],
        dice_rolls=[3],
    )
    game.get_racer(2).finish_position = 1
    game.get_racer(3).eliminate()

    game.run_turn()

    assert not game.state.race_active
    assert game.get_racer(0).victory_points == CANCEL_VP


def test_spoilsport_cancel_awards_no_finish_position(
    scenario: type[GameScenario],
):
    game = scenario(
        [RacerConfig(0, "Spoilsport"), plain(1, 6)],
        dice_rolls=[3],
    )

    game.run_turn()

    assert all(r.finish_position is None for r in game.state.racers)


def test_spoilsport_cancels_on_trip_recovery_turn(
    scenario: type[GameScenario],
):
    game = scenario(
        [RacerConfig(0, "Spoilsport"), plain(1, 6)],
        dice_rolls=[3],
    )
    game.get_racer(0).tripped = True

    game.run_turn()

    assert not game.state.race_active
