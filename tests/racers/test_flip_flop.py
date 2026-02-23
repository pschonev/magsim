from magsim.engine.scenario import GameScenario, RacerConfig


def test_flip_flop_chooses_furthest_target(scenario: type[GameScenario]):
    """
    FlipFlop targets the racer furthest ahead among valid candidates (>=6 spaces).
    """
    game = scenario(
        [
            RacerConfig(0, "FlipFlop", start_pos=0),
            RacerConfig(1, "Centaur", start_pos=10),      # Valid (+10)
            RacerConfig(2, "PartyAnimal", start_pos=20),  # Valid & Further (+20)
        ],
        dice_rolls=[1],
    )

    game.run_turn()

    # Should swap with PartyAnimal (20)
    assert game.get_racer(0).position == 20
    assert game.get_racer(2).position == 0


def test_flip_flop_cannot_swap_while_tripped(scenario: type[GameScenario]):
    """
    A tripped FlipFlop cannot use the swap ability and must recover instead.
    """
    game = scenario(
        [
            RacerConfig(0, "FlipFlop", start_pos=0),
            RacerConfig(1, "Centaur", start_pos=10),  # Valid target if active
        ],
        dice_rolls=[1],
    )

    # Manually trip FlipFlop before turn
    game.get_racer(0).tripped = True

    game.run_turn()

    ff = game.get_racer(0)
    
    # Recovered (Tripped -> False), but did not swap or move
    assert ff.position == 0
    assert ff.tripped is False
    assert game.get_racer(1).position == 10


def test_flip_flop_swap_consumes_main_move(scenario: type[GameScenario]):
    """
    Using the swap ability consumes the main move, preventing a dice roll.
    """
    game = scenario(
        [
            RacerConfig(0, "FlipFlop", start_pos=0),
            RacerConfig(1, "Centaur", start_pos=10),
        ],
        dice_rolls=[6],  # Roll should be ignored
    )

    game.run_turn()

    ff = game.get_racer(0)
    
    # Swapped to 10. Did NOT roll +6 (which would be 16).
    assert ff.position == 10
    assert ff.main_move_consumed is True


def test_flip_flop_swap_ignores_path_hazards(scenario: type[GameScenario]):
    """
    Swapping is a warp, so it ignores path hazards (Banana) between 
    start and destination.
    """
    game = scenario(
        [
            RacerConfig(0, "FlipFlop", start_pos=0),
            RacerConfig(1, "Banana", start_pos=5),     # Hazard
            RacerConfig(2, "Centaur", start_pos=10),   # Target
        ],
        dice_rolls=[1],
    )

    game.run_turn()

    ff = game.get_racer(0)

    # Swapped to 10
    assert ff.position == 10
    # Did not trip on Banana at 5
    assert not ff.tripped, "Warp triggered path hazard!"


def test_flip_flop_swap_is_simultaneous_avoiding_collision(scenario: type[GameScenario]):
    """
    Swapping is simultaneous, so neither racer 'lands on' the other 
    (avoiding Baba Yaga's collision trip).
    """
    game = scenario(
        [
            RacerConfig(0, "FlipFlop", start_pos=0),
            RacerConfig(1, "BabaYaga", start_pos=10),  # Target with collision trap
        ],
        dice_rolls=[1],
    )

    game.run_turn()

    ff = game.get_racer(0)
    baba = game.get_racer(1)

    # Positions swapped
    assert ff.position == 10
    assert baba.position == 0

    # No collision trips
    assert not ff.tripped, "Simultaneous warp triggered collision trip!"
    assert not baba.tripped, "Simultaneous warp triggered collision trip!"
