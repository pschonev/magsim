from magical_athlete_simulator.engine.scenario import GameScenario, RacerConfig


def test_duelist_basic_duel_win(scenario: type[GameScenario]):
    """
    Duelist shares space with another racer and wins the duel.
    Winner moves +2.
    """
    game = scenario(
        [
            RacerConfig(0, "Duelist", start_pos=5),
            RacerConfig(1, "Banana", start_pos=5),
        ],
        dice_rolls=[
        3, # Duelist Duel
        2, # Banana Duel
        5, # Duelist Main Move
        ],
    )

    game.run_turn()

    duelist = game.get_racer(0)
    banana = game.get_racer(1)

    assert duelist.position == 12
    assert banana.position == 5


def test_duelist_loses_duel(scenario: type[GameScenario]):
    """
    Duelist challenges another racer but loses.
    Opponent moves +2, Duelist stays.
    """
    game = scenario(
        [
            RacerConfig(0, "Duelist", start_pos=5),
            RacerConfig(1, "Banana", start_pos=5),
        ],
        dice_rolls=[
            2, # Duelist Duel
        6, # Banana Duel
        3 # Duelist Main Move
        ],
    )

    game.run_turn()

    duelist = game.get_racer(0)
    banana = game.get_racer(1)

    assert duelist.position == 8
    assert banana.position == 7


def test_duelist_tie_goes_to_duelist(scenario: type[GameScenario]):
    """
    Duelist and opponent roll the same value.
    Duelist wins on ties (>= logic).
    """
    game = scenario(
        [
            RacerConfig(0, "Duelist", start_pos=5),
            RacerConfig(1, "Banana", start_pos=5),
        ],
        dice_rolls=[4, 4, 1],
    )

    game.run_turn()

    duelist = game.get_racer(0)

    assert duelist.position == 8


def test_duelist_multiple_targets(scenario: type[GameScenario]):
    """
    Duelist shares space with two racers.
    Auto-agent picks the one with highest index.
    """
    game = scenario(
        [
            RacerConfig(0, "Duelist", start_pos=5),
            RacerConfig(1, "Mouth", start_pos=5),
            RacerConfig(2, "Centaur", start_pos=5),
        ],
        dice_rolls=[3, 6, 1, 6, 1],
    )

    game.run_turn()

    duelist = game.get_racer(0)
    mouth = game.get_racer(1)
    centaur = game.get_racer(2)

    assert duelist.position == 6
    assert mouth.position == 7
    assert centaur.position == None # eaten by Mouth


def test_duelist_triggers_after_move(scenario: type[GameScenario]):
    """
    Duelist moves onto occupied space.
    Duel triggers on PostMoveEvent.
    """
    game = scenario(
        [
            RacerConfig(0, "Duelist", start_pos=0),
            RacerConfig(1, "Banana", start_pos=5),
        ],
        dice_rolls=[5, 6, 2],
    )

    game.run_turn()

    duelist = game.get_racer(0)

    assert duelist.position == 7


def test_duelist_copycat_on_gain_immediate_trigger(scenario: type[GameScenario]):
    """
    Duelist duels and takes the lead, then rolls. 
    Copycat copies Duelist and moves onto Banana and triggers another duel.
    """
    game = scenario(
        [
            RacerConfig(0, "Duelist", start_pos=10),
            RacerConfig(1, "Copycat", start_pos=5),
            RacerConfig(2, "Banana", start_pos=10),
        ],
        dice_rolls=[6, 3, 3, 5, 6, 3],
    )

    game.run_turns(2)

    duelist = game.get_racer(0)
    copycat = game.get_racer(1)

    assert "DuelistDuel" in copycat.abilities
    assert duelist.position == 15
    assert copycat.position == 12


def test_duelist_copycat_double_trigger_prevention(scenario: type[GameScenario]):
    """
    Copycat copies Duelist on the same space.
    Both have DuelistDuel but locked_abilities prevents double-dueling.
    """
    game = scenario(
        [
            RacerConfig(0, "Duelist", start_pos=10),
            RacerConfig(1, "Copycat", start_pos=5),
        ],
        dice_rolls=[1, 6, 5, 1],
    )

    game.run_turns(2)

    duelist = game.get_racer(0)
    copycat = game.get_racer(1)

    assert duelist.position == 11
    assert copycat.position == 13


def test_duelist_no_duel_when_alone(scenario: type[GameScenario]):
    """
    Duelist moves to empty space.
    No duel occurs.
    """
    game = scenario(
        [
            RacerConfig(0, "Duelist", start_pos=0),
            RacerConfig(1, "Banana", start_pos=10),
        ],
        dice_rolls=[5],
    )

    game.run_turn()

    duelist = game.get_racer(0)

    assert duelist.position == 5
