"""Pin the interpretations listed under "Open questions" in docs/second_wind_analysis.md.

Each test documents the current behaviour so a designer ruling shows up as a failing test.
"""

from magsim.engine.scenario import GameScenario, RacerConfig


def dummy(idx: int, pos: int = 0) -> RacerConfig:
    return RacerConfig(idx, "Centaur", abilities=set(), start_pos=pos)


def test_show_off_counting_die_is_the_first_die(scenario: type[GameScenario]):
    """Open question: Show-Off's roll-triggers (e.g. Magical Athlete's) see only the first die, not the chain total."""
    game = scenario(
        [RacerConfig(0, "ShowOff", start_pos=0), dummy(1, 20)],
        dice_rolls=[1, 2, 6],
    )
    game.run_turn()

    assert game.state.roll_state.dice_values == (1, 2, 6)
    assert game.state.roll_state.dice_value == 1


def test_mr_dice_guy_counting_die_is_the_picked_duplicate(
    scenario: type[GameScenario],
):
    """Open question: Mr. Dice Guy's single dice_value is the duplicated number he moves by."""
    game = scenario(
        [RacerConfig(0, "MrDiceGuy", start_pos=0), dummy(1, 20)],
        dice_rolls=[4, 4, 1, 2, 3, 6],
    )
    game.run_turn()

    assert game.state.roll_state.dice_value == 4


def test_mr_dice_guy_bust_has_no_counting_die(scenario: type[GameScenario]):
    """Open question: a no-duplicate bust leaves dice_value None, so telemetry and dice_value readers ignore it."""
    game = scenario(
        [RacerConfig(0, "MrDiceGuy", start_pos=0), dummy(1, 20)],
        dice_rolls=[1, 2, 3, 4, 5, 6],
    )
    game.run_turn()

    assert game.state.roll_state.dice_value is None
    assert len(game.state.roll_state.dice_values) == 6
