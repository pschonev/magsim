from magical_athlete_simulator.engine.scenario import GameScenario, RacerConfig


def test_heckler_basic_jeer(scenario: type[GameScenario]):
    """
    Racer starts at 5, rolls 1, ends at 6 (net +1).
    Heckler jeers and moves +2.
    """
    game = scenario(
        [
            RacerConfig(0, "Heckler", start_pos=0),
            RacerConfig(1, "Banana", start_pos=5),
        ],
        dice_rolls=[3, 1],
    )

    game.run_turns(2)

    heckler = game.get_racer(0)
    banana = game.get_racer(1)

    assert banana.position == 6
    assert heckler.position == 5


def test_heckler_no_jeer_on_big_move(scenario: type[GameScenario]):
    """
    Racer moves +6, Heckler doesn't jeer.
    """
    game = scenario(
        [
            RacerConfig(0, "Heckler", start_pos=0),
            RacerConfig(1, "Banana", start_pos=5),
        ],
        dice_rolls=[3, 6],
    )

    game.run_turns(2)

    heckler = game.get_racer(0)
    banana = game.get_racer(1)

    assert banana.position == 11
    assert heckler.position == 3


def test_heckler_multiple_jeers_in_round(scenario: type[GameScenario]):
    """
    Heckler and three racers barely move, Heckler jeers each and moves +8 total.
    """
    game = scenario(
        [
            RacerConfig(0, "Heckler", start_pos=0),
            RacerConfig(1, "Banana", start_pos=5),
            RacerConfig(2, "Centaur", start_pos=10),
            RacerConfig(3, "Gunk", start_pos=15),
        ],
        dice_rolls=[2, 1, 1, 1],
    )

    game.run_turns(4)

    heckler = game.get_racer(0)

    assert heckler.position == 9


def test_heckler_trip_recovery(scenario: type[GameScenario]):
    """
    Heckler recovers from trip and triggers his own ability.
    """
    game = scenario(
        [
            RacerConfig(0, "Heckler", start_pos=0),
            RacerConfig(1, "Gunk", start_pos=5),
            RacerConfig(2, "Banana", start_pos=3),
        ],
        dice_rolls=[6],
    )

    heckler = game.get_racer(0)
    gunk = game.get_racer(1)
    banana = game.get_racer(2)

    heckler.tripped = True
    gunk.tripped = True
    game.run_turns(2)

    assert heckler.position == 4
    assert gunk.position == 5
    assert banana.position == 3
    
    assert heckler.tripped == True # trips again on Banana
    assert gunk.tripped == False



def test_heckler_copycat_shared_state(scenario: type[GameScenario]):
    """
    Copycat copies Heckler.
    """
    game = scenario(
        [
            RacerConfig(0, "Heckler", start_pos=20),
            RacerConfig(1, "Copycat", start_pos=5),
            RacerConfig(2, "Banana", start_pos=10),
            RacerConfig(3, "Gunk", start_pos=15),
        ],
        dice_rolls=[3, 3, 2, 1],
    )

    game.run_turns(4)

    heckler = game.get_racer(0)
    copycat = game.get_racer(1)

    assert heckler.position == 26
    assert copycat.position == 11
