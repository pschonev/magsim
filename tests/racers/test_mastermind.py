from magsim.ai.baseline_agent import BaselineAgent
from magsim.engine.scenario import GameScenario, RacerConfig


def test_mastermind_predicts_winner_and_takes_second(scenario: type[GameScenario]):
    """
    Scenario: Mastermind (idx 0) vs Gunk (idx 1, Leader) vs Scoocher (idx 2).
    - Mastermind uses BaselineAgent (predicts Leader -> Gunk).
    - Gunk finishes 1st.
    - Mastermind triggers ability and finishes 2nd immediately.
    """
    game = scenario(
        [
            RacerConfig(0, "Mastermind", start_pos=0),
            RacerConfig(1, "Gunk", start_pos=10),
            RacerConfig(2, "Scoocher", start_pos=0),
        ],
        # Rolls:
        # 1. Mastermind: 2 (Moves 0->2, Predicts Gunk)
        # 2. Gunk: 6 (Moves 10->16, Finishes)
        dice_rolls=[2, 6], 
    )
    
    # Attach AI to Mastermind
    game.engine.agents[0] = BaselineAgent()

    # Run the full race (or just enough turns to finish)
    game.engine.run_race()
    
    mastermind = game.get_racer(0)
    gunk = game.get_racer(1)

    # Gunk finished 1st
    assert gunk.finished
    assert gunk.finish_position == 1

    # Mastermind piggybacked to 2nd
    assert mastermind.finished
    assert mastermind.finish_position == 2


def test_mastermind_houserule_steal_first_place(scenario: type[GameScenario]):
    """
    House Rule: Mastermind Steals 1st Place.
    Scenario: Mastermind (idx 0) vs Gunk (idx 1, Leader).
    - Mastermind uses BaselineAgent (predicts Gunk).
    - Gunk crosses finish line.
    - Mastermind triggers, takes 1st place, bumping Gunk to 2nd.
    """
    game = scenario(
        [
            RacerConfig(0, "Mastermind", start_pos=0),
            RacerConfig(1, "Gunk", start_pos=10),
            RacerConfig(2, "Scoocher", start_pos=0),
        ],
        # Rolls:
        # 1. Mastermind: 2 (Moves 0->2, Predicts Gunk)
        # 2. Gunk: 6 (Moves 10->16, Finishes)
        dice_rolls=[2, 6], 
    )
    
    game.engine.agents[0] = BaselineAgent()
    
    # Enable House Rule
    game.engine.state.rules.hr_mastermind_steal_1st = True

    game.engine.run_race()
    
    mastermind = game.get_racer(0)
    gunk = game.get_racer(1)

    # Mastermind stole 1st place
    assert mastermind.finished
    assert mastermind.finish_position == 1
    assert mastermind.victory_points == 4  # Standard 1st place VP

    # Gunk bumped to 2nd place
    assert gunk.finished
    assert gunk.finish_position == 2
    assert gunk.victory_points == 2  # Standard 2nd place VP
