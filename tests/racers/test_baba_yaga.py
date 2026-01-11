from magical_athlete_simulator.engine.scenario import GameScenario, RacerConfig

def test_baba_yaga_trips_multiple_arrivals(scenario: type[GameScenario]):
    """Baba Yaga arriving on a space with others should trip them."""
    game = scenario(
        [
            RacerConfig(0, "BabaYaga", start_pos=0),
            RacerConfig(1, "Centaur", start_pos=4),
            RacerConfig(2, "Banana", start_pos=4),
        ],
        dice_rolls=[4] # Baba Yaga moves 0 -> 4
    )
    
    game.run_turn()
    
    baba_yaga = game.get_racer(0)
    centaur = game.get_racer(1)
    banana = game.get_racer(2)
    
    assert centaur.tripped is True, "Centaur should be tripped"
    assert banana.tripped is True, "Banana should be tripped"
    assert baba_yaga.tripped is False, "Baba Yaga should not be tripped"

def test_others_trip_arriving_on_baba_yaga(scenario: type[GameScenario]):
    """Racers arriving on Baba Yaga's space should be tripped."""
    game = scenario(
        [
            RacerConfig(0, "Banana", start_pos=0),
            RacerConfig(1, "BabaYaga", start_pos=4),
        ],
        dice_rolls=[4] # Victim moves 0 -> 4
    )
    
    game.run_turn()
    
    banana = game.get_racer(0)
    baba_yaga = game.get_racer(1)
    assert banana.tripped is True, "Banana should be tripped by landing on Baba Yaga"
    assert baba_yaga.tripped is False, "Baba Yaga should not be tripped"

def test_baba_yaga_does_not_trip_at_start(scenario: type[GameScenario]):
    """
    Verify that Baba Yaga does not trip everyone at the starting line simply 
    because the game initialized or someone else moved away.
    """
    game = scenario(
        [
            RacerConfig(0, "BabaYaga", start_pos=0),
            RacerConfig(1, "Banana", start_pos=0),  # Shares start with Baba
            RacerConfig(2, "Mastermind", start_pos=0),    # Shares start with Baba
        ],
        dice_rolls=[
            3,  # Baba Yaga rolls 3. Moves 0 -> 3.
                # Should NOT trip Banana or Gunk (she left them).
            2,  # Banana rolls 2. Moves 0 -> 2.
                # Should NOT trip (didn't land on Baba).
            1,  # Mastermind rolls 1. Moves 0 -> 1.
        ],
    )

    # Turn 1: Baba moves 0 -> 3
    game.run_turn()
    baba = game.get_racer(0)
    banana = game.get_racer(1)
    mastermind = game.get_racer(2)

    assert baba.position == 3
    assert not banana.tripped, "Banana tripped when Baba moved AWAY from start"
    assert not mastermind.tripped, "Gunk tripped when Baba moved AWAY from start"

    # Turn 2: Banana moves 0 -> 2
    game.run_turn()
    assert banana.position == 2
    assert not banana.tripped, "Banana tripped moving to empty tile"

    # Turn 3: Gunk moves 0 -> 1
    game.run_turn()
    assert mastermind.position == 1


def test_baba_yaga_trips_on_collision(scenario: type[GameScenario]):
    """
    Verify the positive cases: Baba trips when landing on someone,
    and someone trips when landing on Baba.
    """
    game = scenario(
        [
            RacerConfig(0, "BabaYaga", start_pos=0),
            RacerConfig(1, "Banana", start_pos=5),
        ],
        dice_rolls=[
            5,  # Baba rolls 5. Moves 0 -> 5. Lands on Banana. -> TRIP Banana.
            5,  # Baba rolls 5. Moves 5 -> 10.
            5,  # Banana (Recovered) rolls 5. Moves 5 -> 10. Lands on Baba. -> TRIP Banana.
        ],
    )

    # Turn 1: Baba lands on Banana
    game.run_turn()
    banana = game.get_racer(1)
    assert banana.tripped, "Banana should be tripped when Baba lands on them"

    # Turn 2: Banana is tripped. Recovers.
    game.run_turn()
    assert not banana.tripped, "Banana should recover from trip"
    assert banana.position == 5, "Banana should not move while recovering"

    # Turn 3: Baba moves away
    game.run_turn()
    baba = game.get_racer(0)
    assert baba.position == 10

    # Turn 4: Banana lands on Baba
    game.run_turn()
    assert banana.position == 10
    assert banana.tripped, "Banana should trip when landing on Baba"
