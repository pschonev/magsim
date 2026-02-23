from magsim.engine.scenario import GameScenario, RacerConfig


def test_party_animal_pull_moves_everyone_towards_party_animal(scenario: type[GameScenario]):
    """
    TurnStart: everyone (except PartyAnimal and anyone already on his tile) moves 1 step toward him.
    Then PartyAnimal still takes its normal roll-based move.
    """
    game = scenario(
        [
            RacerConfig(0, "PartyAnimal", start_pos=10),
            RacerConfig(1, "Banana", start_pos=5),    # behind -> +1 to 6
            RacerConfig(2, "Centaur", start_pos=13),  # ahead  -> -1 to 12
        ],
        dice_rolls=[2],  # PartyAnimal main move after pull
    )

    game.run_turn()

    pa = game.get_racer(0)
    banana = game.get_racer(1)
    centaur = game.get_racer(2)

    assert banana.position == 6
    assert centaur.position == 12
    assert pa.position == 12  # pull doesn't move PA; then rolls 2


def test_party_animal_pull_skips_racers_already_on_party_tile(scenario: type[GameScenario]):
    """
    Racers already on PartyAnimal's position should not be included in the simultaneous moves.
    """
    game = scenario(
        [
            RacerConfig(0, "PartyAnimal", start_pos=10),
            RacerConfig(1, "Banana", start_pos=10),   # same tile -> should not move during pull
            RacerConfig(2, "Centaur", start_pos=12),  # ahead -> -1
        ],
        dice_rolls=[1],
    )

    game.run_turn()

    pa = game.get_racer(0)
    banana = game.get_racer(1)
    centaur = game.get_racer(2)

    assert banana.position == 10
    assert centaur.position == 11
    assert pa.position == 12


def test_party_self_boost_adds_bonus_equal_to_neighbors(scenario: type[GameScenario]):
    """
    PartyAnimal gets +N to its roll where N = number of other active racers on its tile.
    Setup: two guests share tile with PartyAnimal, so roll 2 becomes 4.
    """
    game = scenario(
        [
            RacerConfig(0, "PartyAnimal", start_pos=5),
            RacerConfig(1, "Banana", start_pos=5),
            RacerConfig(2, "Gunk", start_pos=5),
            RacerConfig(3, "Centaur", start_pos=20),  # keep a distant racer so PartyPull doesn't end the race
        ],
        dice_rolls=[2],
    )

    game.run_turn()

    pa = game.get_racer(0)
    assert pa.position == 8  # 5 + (2 + 2 guests) - 1 Gunk


def test_party_self_boost_zero_when_alone(scenario: type[GameScenario]):
    """
    If PartyAnimal has no guests on its tile at roll time, there is no roll bonus.
    """
    game = scenario(
        [
            RacerConfig(0, "PartyAnimal", start_pos=5),
            RacerConfig(1, "Banana", start_pos=8),
        ],
        dice_rolls=[3],
    )

    game.run_turn()

    pa = game.get_racer(0)
    assert pa.position == 8  # 5 + 3


def test_party_self_boost_and_gunk_slime_cancel(scenario: type[GameScenario]):
    """
    PartyAnimal with exactly one guest on its tile gets +1 (PartySelfBoost),
    but if Gunk is present (Slime -1), the modifiers cancel and net move equals base roll.
    """
    game = scenario(
        [
            RacerConfig(0, "PartyAnimal", start_pos=2),
            RacerConfig(1, "Gunk", start_pos=0),     # slimes others
            RacerConfig(2, "Banana", start_pos=2),   # guest gives +1
        ],
        dice_rolls=[4],
    )

    game.run_turn()

    pa = game.get_racer(0)
    assert pa.position == 6  # 2 + 4 ( +1 -1 cancels )


def test_party_pull_ignores_finished_or_eliminated_targets(scenario: type[GameScenario]):
    """
    PartyPull iterates engine.state.racers but should skip non-active (is_active check).
    """
    game = scenario(
        [
            RacerConfig(0, "PartyAnimal", start_pos=10),
            RacerConfig(1, "Banana", start_pos=5),
            RacerConfig(2, "Centaur", start_pos=15),
        ],
        dice_rolls=[1],
    )

    # Mark Centaur finished before PartyAnimal turn begins.
    game.get_racer(2).finish_position = 1

    game.run_turn()

    banana = game.get_racer(1)
    centaur = game.get_racer(2)

    assert banana.position == 6  # pulled toward 10
    assert centaur.position == 15  # unchanged (not active)
