from magsim.engine.scenario import GameScenario, RacerConfig


def test_inchworm_cancels_opponent_rolling_one(scenario: type[GameScenario]):
    """
    Inchworm reacts when an opponent rolls a 1:
    1. Cancels the opponent's move.
    2. Inchworm creeps forward 1 space.
    """
    game = scenario(
        [
            RacerConfig(0, "Inchworm", start_pos=0),
            RacerConfig(1, "Centaur", start_pos=10),
        ],
        dice_rolls=[2, 1],  # Inchworm rolls 2, Centaur rolls 1
    )

    game.run_turn()  # Inchworm turn
    game.run_turn()  # Centaur turn

    inchworm = game.get_racer(0)
    centaur = game.get_racer(1)

    # Centaur stay put (move cancelled)
    assert centaur.position == 10
    assert centaur.main_move_consumed is True

    # Inchworm: 2 (Own Move) + 1 (Ability Bonus) = 3
    assert inchworm.position == 3


def test_inchworm_ignores_own_one_roll(scenario: type[GameScenario]):
    """
    Inchworm's ability does NOT trigger on its own rolls.
    Rolling a 1 results in a normal move of 1 (unless modified by others).
    """
    game = scenario(
        [
            RacerConfig(0, "Inchworm", start_pos=0),
            RacerConfig(1, "Gunk", start_pos=0),  # Reduces move by 1
        ],
        dice_rolls=[1],
    )

    game.run_turn()

    inchworm = game.get_racer(0)
    
    # Roll 1 - 1 (Gunk) = 0.
    # Checks that no "Cancel" logic occurred (which might refund move) 
    # and no "Creep" logic occurred (which would add +1).
    assert inchworm.position == 0


def test_inchworm_and_skipper_interaction(scenario: type[GameScenario]):
    """
    Scenario: Centaur rolls 1.
    - Inchworm triggers: Cancels Centaur, Creeps +1.
    - Skipper triggers: Steals next turn.
    
    Verify:
    1. Centaur doesn't move.
    2. Inchworm moves +1.
    3. Next turn is Skipper (skipping Inchworm/Banana in natural order).
    4. Turn order resumes to Centaur after Skipper.
    """
    game = scenario(
        [
            RacerConfig(0, "Centaur", start_pos=0),
            RacerConfig(1, "Inchworm", start_pos=0),
            RacerConfig(2, "Banana", start_pos=0),
            RacerConfig(3, "Skipper", start_pos=0),
        ],
        dice_rolls=[1, 2],  # Centaur 1, Skipper 2
    )

    # Turn 0: Centaur rolls 1
    game.run_turn()

    centaur = game.get_racer(0)
    inchworm = game.get_racer(1)
    
    # Mechanics Check
    assert centaur.position == 0  # Cancelled
    assert inchworm.position == 1  # Creep
    
    # Turn Override Check
    assert game.engine.state.current_racer_idx == 3, "Skipper should steal turn"

    # Turn 1: Skipper (Stolen Turn)
    game.run_turn()
    
    skipper = game.get_racer(3)
    assert skipper.position == 2
    
    # Turn Order Resume Check (Wraps to 0)
    assert game.engine.state.current_racer_idx == 0
