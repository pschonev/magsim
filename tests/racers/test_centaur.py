from magical_athlete_simulator.core.events import MoveCmdEvent, Phase, WarpCmdEvent
from magical_athlete_simulator.engine.scenario import GameScenario, RacerConfig


def test_centaur_tramples_multiple_victims(scenario: type[GameScenario]):
    """
    Scenario: Centaur moves 6 spaces (0->6), passing racers at pos 2 and 4.
    Verify:
    - Scoocher (pos 2) is trampled (-2) -> 0.
    - Gunk (pos 4) is trampled (-2) -> 2.
    """
    game = scenario(
        [
            RacerConfig(0, "Centaur", start_pos=0),
            RacerConfig(1, "Scoocher", start_pos=2),
            RacerConfig(2, "Gunk", start_pos=4),
        ],
        dice_rolls=[6],
    )
    game.run_turn()
    
    assert game.get_racer(1).position == 3
    assert game.get_racer(2).position == 2


def test_centaur_floor_clamping(scenario: type[GameScenario]):
    """Victims at position 1 should move to 0, not -1."""
    game = scenario(
        [
            RacerConfig(0, "Centaur", start_pos=0),
            RacerConfig(1, "Scoocher", start_pos=1),
        ],
        dice_rolls=[6],
    )
    game.run_turn()
    
    # Scoocher 1 -> 0 (Trample) -> 1 (Reaction to Trample trigger).
    assert game.get_racer(1).position == 1


def test_centaur_ignore_finished_racers(scenario: type[GameScenario]):
    """Finished racers should not be trampled."""
    game = scenario(
        [
            RacerConfig(0, "Centaur", start_pos=27),
            RacerConfig(1, "Scoocher", start_pos=30),  # Finished
        ],
        dice_rolls=[6],
    )
    game.get_racer(1).finish_position = 1

    game.run_turn()

    assert game.get_racer(1).position == 30
    assert game.get_racer(1).finished is True
    
    # Centaur 27 -> 33 (Finish)
    assert game.get_racer(0).finished is True
    assert game.get_racer(0).finish_position == 2


def test_centaur_trample_triggers_on_passive_move(scenario: type[GameScenario]):
    """
    Passing logic fires even for passive moves (e.g., wind gust).
    Scenario: Centaur moved 0->4 by event, passing Scoocher at 2.
    """
    game = scenario(
        [
            RacerConfig(0, "Centaur", start_pos=0),
            RacerConfig(1, "Scoocher", start_pos=2),
        ],
        dice_rolls=[1],
    )

    # Inject passive move
    game.engine.push_event(
        MoveCmdEvent(
            target_racer_idx=0,
            distance=4,
            source="System",
            phase=Phase.SYSTEM,
            responsible_racer_idx=None,
        )
    )

    game.run_turn()

    assert game.get_racer(0).position == 5
    assert game.get_racer(1).position == 1


def test_centaur_trample_ignores_warp(scenario: type[GameScenario]):
    """Warping past a racer does NOT count as passing."""
    game = scenario(
        [
            RacerConfig(0, "Centaur", start_pos=0),
            RacerConfig(1, "Scoocher", start_pos=2),
        ],
        dice_rolls=[1],
    )

    # Inject passive warp 0->4
    game.engine.push_event(
        WarpCmdEvent(
            target_racer_idx=0,
            target_tile=4,
            source="System",
            phase=Phase.PRE_MAIN,
            responsible_racer_idx=None,
            emit_ability_triggered="never",
        )
    )

    game.run_turn()

    # Centaur: Warped 0->4, then Rolled 1 -> 5
    assert game.get_racer(0).position == 5
    
    # Scoocher: Stays at 2 (No trample)
    assert game.get_racer(1).position == 2
