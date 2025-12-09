from typing import Any


from tests.test_utils import RacerConfig


def test_scoocher_ignores_own_ability(scenario):
    """
    Scenario: Scoocher uses an ability (e.g. if they had one, or simple move).
    Verify: Does not trigger self.
    """
    game = scenario(
        [RacerConfig(0, "Scoocher", {"ScoochStep"}, start_pos=0)], dice_rolls=[4]
    )
    game.run_turn()
    assert game.get_racer(0).position == 4  # Just the main move


def test_scoocher_infinite_loop_prevention(scenario):
    """
    Scenario: Two Scoochers. Someone else triggers an ability.
    Sequence:
    - Trigger happens.
    - Scoocher A moves (Triggers B).
    - Scoocher B moves (Triggers A).
    - Scoocher A moves (Triggers B)...
    Verify: Engine detects loop and halts after one cycle.
    """
    game = scenario(
        [
            RacerConfig(0, "Magician", {"MagicalReroll"}, start_pos=0),
            RacerConfig(1, "Scoocher", {"ScoochStep"}, start_pos=10),  # Scoocher A
            RacerConfig(2, "Scoocher", {"ScoochStep"}, start_pos=20),  # Scoocher B
        ],
        dice_rolls=[1, 6],  # Magician rolls 1 (Trigger), then 6
    )

    game.run_turn()

    assert game.get_racer(0).position == 6
    assert game.get_racer(1).position == 12
    assert game.get_racer(2).position == 21


def test_scoocher_productive_loop_duplicate(scenario):
    """
    Scenario: Two Scoochers. Someone else triggers an ability.
    Sequence:
    - Trigger happens.
    - Scoocher A moves (Triggers B).
    - Scoocher B moves (Triggers A).
    - Scoocher A moves (Triggers B)...
    Verify: Engine detects loop and halts after one cycle.
    """
    game = scenario(
        [
            RacerConfig(0, "Magician", {"MagicalReroll"}, start_pos=0),
            RacerConfig(1, "Scoocher", {"ScoochStep"}, start_pos=10),  # Scoocher A
            RacerConfig(2, "Scoocher", {"ScoochStep"}, start_pos=19),  # Scoocher B
        ],
        dice_rolls=[1, 6],  # Magician rolls 1 (Trigger), then 6
    )

    game.run_turn()

    assert game.get_racer(1).position == 13
    assert game.get_racer(2).position == 21
