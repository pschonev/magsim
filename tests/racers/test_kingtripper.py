from magsim.engine.scenario import GameScenario, RacerConfig


def test_kingtripper_trips_sole_leader(scenario: type[GameScenario]):
    game = scenario(
        [
            RacerConfig(0, "Kingtripper", start_pos=0),
            RacerConfig(1, "Centaur", start_pos=10),
            RacerConfig(2, "Hypnotist", start_pos=5),
        ],
        dice_rolls=[2],
    )

    game.run_turn()

    assert game.get_racer(1).tripped
    assert not game.get_racer(2).tripped
    assert game.get_racer(0).position == 2


def test_kingtripper_does_nothing_when_strictly_leading(
    scenario: type[GameScenario],
):
    game = scenario(
        [
            RacerConfig(0, "Kingtripper", start_pos=10),
            RacerConfig(1, "Centaur", start_pos=9),
            RacerConfig(2, "Hypnotist", start_pos=5),
        ],
        dice_rolls=[2],
    )

    game.run_turn()

    assert not any(r.tripped for r in game.state.racers)
    assert game.get_racer(0).position == 12


def test_kingtripper_tie_picks_highest_winrate(scenario: type[GameScenario]):
    """Twin has a higher winrate than Centaur in the stats file."""
    game = scenario(
        [
            RacerConfig(0, "Kingtripper", start_pos=0),
            RacerConfig(1, "Centaur", start_pos=10),
            RacerConfig(2, "Twin", start_pos=10),
        ],
        dice_rolls=[2],
    )

    game.run_turn()

    assert game.get_racer(2).tripped
    assert not game.get_racer(1).tripped


def test_kingtripper_ignores_finished_leader(scenario: type[GameScenario]):
    game = scenario(
        [
            RacerConfig(0, "Kingtripper", start_pos=0),
            RacerConfig(1, "Centaur", start_pos=25),
            RacerConfig(2, "Hypnotist", start_pos=5),
        ],
        dice_rolls=[2],
    )
    game.get_racer(1).finish_position = 1

    game.run_turn()

    assert game.get_racer(2).tripped
