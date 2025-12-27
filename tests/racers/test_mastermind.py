import itertools
from tests.test_utils import GameScenario, RacerConfig


def test_mastermind_predicts_winner_and_takes_second(scenario: type[GameScenario]):
    """
    Scenario: 
      - Mastermind (idx 0) vs Scoocher (idx 1) vs Gunk (idx 2).
      - Scoocher starts significantly ahead (pos 10).
      - Mastermind should predict Scoocher (logic: pick leader).
      - Scoocher finishes 1st.
    Verify: 
      - Mastermind correctly predicts Scoocher.
      - When Scoocher finishes 1st, Mastermind immediately becomes 2nd.
    """
    infinite_dice = itertools.cycle([2, 1, 6])
    
    game = scenario(
        [
            RacerConfig(idx=0, name="Mastermind", start_pos=0),
            RacerConfig(idx=1, name="Scoocher", start_pos=10),
            RacerConfig(idx=2, name="Gunk", start_pos=0),
        ],
        # Rolls: 
        # 1. Mastermind Turn: Rolls 1. Moves 1. Predicts Scoocher.
        # 2. Scoocher Turn: Rolls 6 (Cheat). Finishes (10+6 > Finish).
        dice_rolls=list(itertools.islice(infinite_dice, 100)), 
    )
    game.engine.rng.randint.side_effect = infinite_dice 
    # Turn 1: Mastermind
    # Triggers TurnStart -> MastermindPredict -> Selects Scoocher
    game.engine.run_race()
    
    mastermind = game.get_racer(0)
    scoocher = game.get_racer(1)

    # Verify Scoocher Win
    assert scoocher.finished
    assert scoocher.finish_position == 1

    # Verify Mastermind "Piggyback" Win
    assert mastermind.finished
    assert mastermind.finish_position == 2
