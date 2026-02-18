from magical_athlete_simulator.engine.scenario import GameScenario, RacerConfig


def test_hypnotist_warps_furthest_ahead_target(scenario: type[GameScenario]):
    """
    Hypnotist is behind and should warp the furthest-ahead racer back onto Hypnotist's space,
    then still take their normal dice move.
    """
    game = scenario(
        [
            RacerConfig(0, "Hypnotist", start_pos=3),
            RacerConfig(1, "Banana", start_pos=8),
            RacerConfig(2, "Centaur", start_pos=12),
        ],
        dice_rolls=[4],
    )

    game.run_turn()

    hypnotist = game.get_racer(0)
    banana = game.get_racer(1)
    centaur = game.get_racer(2)

    assert centaur.position == 3
    assert banana.position == 8
    assert hypnotist.position == 7


def test_hypnotist_does_nothing_when_in_lead(scenario: type[GameScenario]):
    """
    Hypnotist is in the lead at turn start, so auto-strategy should not warp anyone.
    Hypnotist only moves by the dice.
    """
    game = scenario(
        [
            RacerConfig(0, "Hypnotist", start_pos=10),
            RacerConfig(1, "Banana", start_pos=8),
            RacerConfig(2, "Centaur", start_pos=9),
        ],
        dice_rolls=[2],
    )

    game.run_turn()

    hypnotist = game.get_racer(0)
    banana = game.get_racer(1)
    centaur = game.get_racer(2)

    assert hypnotist.position == 12
    assert banana.position == 8
    assert centaur.position == 9


def test_hypnotist_warp_while_recovering(scenario: type[GameScenario]):
    """
    Hypnotist warps Banana (who is ahead) onto Hypnotist's tile.
    Warps are not movement-by-distance, so Banana should not be tripped by BananaTrip while warping.
    """
    game = scenario(
        [
            RacerConfig(0, "Hypnotist", start_pos=5),
            RacerConfig(1, "Banana", start_pos=3),
            RacerConfig(2, "Centaur", start_pos=15),
        ],
        dice_rolls=[1],
    )


    hypnotist = game.get_racer(0)
    centaur = game.get_racer(2)

    hypnotist.tripped = True

    game.run_turn()

    assert hypnotist.tripped == False
    assert centaur.position == hypnotist.position


def test_hypnotist_can_warp_finished_racer_is_ignored(scenario: type[GameScenario]):
    """
    A finished racer should not be a valid target (get_active_racers filters them out),
    so Hypnotist should warp the next-best active target.
    """
    game = scenario(
        [
            RacerConfig(0, "Hypnotist", start_pos=0),
            RacerConfig(1, "Banana", start_pos=25),
            RacerConfig(2, "Centaur", start_pos=30),
        ],
        dice_rolls=[3],
    )

    game.get_racer(2).finish_position = 1

    game.run_turn()

    hypnotist = game.get_racer(0)
    banana = game.get_racer(1)
    centaur = game.get_racer(2)

    assert banana.position == 0
    assert centaur.position == 30
    assert hypnotist.position == 3


def test_hypnotist_copycat_copies_and_warps(scenario: type[GameScenario]):
    """
    Copycat is behind the leader Hypnotist, so Copycat should copy HypnotistWarp.
    On Copycat's turn, it warps the furthest-ahead racer (Hypnotist) back to Copycat's tile,
    then takes its normal dice move.
    """
    game = scenario(
        [
            RacerConfig(0, "Banana", start_pos=7),
            RacerConfig(1, "Copycat", start_pos=0),
            RacerConfig(2, "Hypnotist", start_pos=10),
        ],
        dice_rolls=[2, 4, 2],
    )

    game.run_turns(3)

    banana = game.get_racer(0)
    copycat = game.get_racer(1)
    hypnotist = game.get_racer(2)

    assert "BananaTrip" not in copycat.abilities
    assert banana.position == 0
    assert copycat.position == 4
    assert hypnotist.position == 2
