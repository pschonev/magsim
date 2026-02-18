from magical_athlete_simulator.engine.scenario import GameScenario, RacerConfig


def test_cheerleader_basic_support(scenario: type[GameScenario]):
    """
    Cheerleader uses ability on two racers in last place.
    Both last-place racers move +2, Cheerleader moves +1.
    """
    game = scenario(
        [
            RacerConfig(0, "Cheerleader", start_pos=10),
            RacerConfig(1, "Banana", start_pos=0),
            RacerConfig(2, "Centaur", start_pos=0),
        ],
        dice_rolls=[1],
    )

    game.run_turn()

    cheerleader = game.get_racer(0)
    banana = game.get_racer(1)
    centaur = game.get_racer(2)

    assert cheerleader.position == 12
    assert banana.position == 2
    assert centaur.position == 2


def test_cheerleader_in_last_place(scenario: type[GameScenario]):
    """
    Cheerleader is one of the last-place racers.
    Receives both +2 from simultaneous move and +1 from self-move.
    """
    game = scenario(
        [
            RacerConfig(0, "Cheerleader", start_pos=0),
            RacerConfig(1, "Banana", start_pos=0),
            RacerConfig(2, "Centaur", start_pos=10),
        ],
        dice_rolls=[5],
    )

    game.run_turn()

    cheerleader = game.get_racer(0)
    banana = game.get_racer(1)

    assert cheerleader.position == 8
    assert banana.position == 2


def test_cheerleader_triggers_scoocher(scenario: type[GameScenario]):
    """
    Cheerleader ability emits AbilityTriggeredEvent.
    Scoocher observes and moves +1.
    """
    game = scenario(
        [
            RacerConfig(0, "Cheerleader", start_pos=5),
            RacerConfig(1, "Banana", start_pos=0),
            RacerConfig(2, "Scoocher", start_pos=10),
        ],
        dice_rolls=[2],
    )

    game.run_turn()

    scoocher = game.get_racer(2)
    assert scoocher.position == 11


def test_cheerleader_single_last_place_racer(scenario: type[GameScenario]):
    """
    Only one racer in last place.
    That racer moves +2, Cheerleader moves +1.
    """
    game = scenario(
        [
            RacerConfig(0, "Cheerleader", start_pos=10),
            RacerConfig(1, "Banana", start_pos=5),
            RacerConfig(2, "Centaur", start_pos=0),
        ],
        dice_rolls=[2],
    )

    game.run_turn()

    cheerleader = game.get_racer(0)
    centaur = game.get_racer(2)

    assert cheerleader.position == 13
    assert centaur.position == 2


def test_cheerleader_everyone_tied_for_last(scenario: type[GameScenario]):
    """
    All racers start at position 0.
    Everyone moves +2, Cheerleader also gets +1 for total +3.
    """
    game = scenario(
        [
            RacerConfig(0, "Cheerleader", start_pos=0),
            RacerConfig(1, "Banana", start_pos=0),
            RacerConfig(2, "Centaur", start_pos=0),
        ],
        dice_rolls=[2],
    )

    game.run_turn()

    cheerleader = game.get_racer(0)
    banana = game.get_racer(1)
    centaur = game.get_racer(2)

    assert cheerleader.position == 5
    assert banana.position == 2
    assert centaur.position == 2


def test_cheerleader_copycat_dynamic_gain(scenario: type[GameScenario]):
    """
    Copycat copies Cheerleader and uses the ability.
    Last-place racer moves +2, Copycat moves +1.
    """
    game = scenario(
        [
            RacerConfig(0, "Cheerleader", start_pos=10),
            RacerConfig(1, "Copycat", start_pos=5),
            RacerConfig(2, "Banana", start_pos=0),
        ],
        dice_rolls=[3, 2],
    )

    game.run_turns(2)

    copycat = game.get_racer(1)
    banana = game.get_racer(2)

    assert "CheerleaderSupport" in copycat.abilities
    assert copycat.position == 8
    assert banana.position == 4
