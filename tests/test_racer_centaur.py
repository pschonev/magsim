from tests.test_utils import RacerConfig
from magical_athlete_simulator.game import MoveCmdEvent, WarpCmdEvent, Phase


def test_centaur_tramples_multiple_victims(scenario):
    """
    Scenario: Centaur moves 6 spaces, passing racers at pos 2 and 4.
    Verify: Both victims are trampled back 2 spaces.
    """
    game = scenario(
        [
            RacerConfig(0, "Centaur", {"Trample"}, start_pos=0),
            RacerConfig(1, "Scoocher", {"ScoochStep"}, start_pos=2),
            RacerConfig(2, "Gunk", {"Slime"}, start_pos=4),
        ],
        dice_rolls=[6],
    )
    game.run_turn()

    # Scoocher: 2 -> 0
    # Gunk: 4 -> 2
    # Scoocher detects one Gunk trigger and 2 Centaur triggers for 3 moves in total
    assert game.get_racer(1).position == 3
    assert game.get_racer(2).position == 2


def test_centaur_floor_clamping(scenario):
    """
    Scenario: Centaur passes someone at position 1.
    Verify: Victim moves to 0, not -1.
    """
    game = scenario(
        [
            RacerConfig(0, "Centaur", {"Trample"}, start_pos=0),
            RacerConfig(1, "Scoocher", {"ScoochStep"}, start_pos=1),
        ],
        dice_rolls=[6],
    )
    game.run_turn()
    assert game.get_racer(1).position == 0


def test_centaur_ignore_finished_racers(scenario):
    """
    Scenario: Centaur passes a racer who has already finished (pos > 20).
    Verify: Finished racer is NOT affected.
    """
    game = scenario(
        [
            RacerConfig(0, "Centaur", {"Trample"}, start_pos=18),
            RacerConfig(1, "Scoocher", {"ScoochStep"}, start_pos=21),  # Finished
        ],
        dice_rolls=[6],  # Moves 18->24
    )
    # Manually mark as finished to simulate game state
    game.get_racer(1).finished = True

    game.run_turn()

    assert game.get_racer(1).position == 21
    assert game.get_racer(1).finished is True


def test_centaur_trample_triggers_on_passive_move(scenario):
    """
    Scenario: Centaur is moved passively (0->4) via a MoveCmdEvent (e.g., "WindGust").
    Verify: Passing logic fires, Scoocher is trampled.
    """
    game = scenario(
        [
            RacerConfig(0, "Centaur", {"Trample"}, start_pos=0),
            RacerConfig(1, "Scoocher", {}, start_pos=2),  # Victim at 2
        ],
        dice_rolls=[1],  # Irrelevant, used for main move only
    )

    # Inject a passive MOVE (0 -> 0+4 = 4)
    game.engine.push_event(
        MoveCmdEvent(
            racer_idx=0, distance=4, source="AnonymousMoveEvent", phase=Phase.BOARD
        ),
        phase=Phase.BOARD,
    )

    game.run_turn()

    # Centaur moved 0->4 (Passive) + 1 (Roll) = 5
    assert game.get_racer(0).position == 5
    # Scoocher WAS trampled (2 -> 0)
    assert game.get_racer(1).position == 0


def test_centaur_trample_ignores_warp(scenario):
    """
    Scenario: Centaur is moved passively (0->4) via a WarpCmdEvent (e.g., "Portal").
    Verify: Passing logic does NOT fire, Scoocher is safe.
    """
    game = scenario(
        [
            RacerConfig(0, "Centaur", {"Trample"}, start_pos=0),
            RacerConfig(1, "Scoocher", {}, start_pos=2),  # Victim at 2
        ],
        dice_rolls=[1],
    )

    # Inject a passive WARP (Target = 4)
    # Warps set position directly, they don't use distance.
    game.engine.push_event(
        WarpCmdEvent(
            racer_idx=0, target_tile=4, source="AnonymousWarpEvent", phase=Phase.BOARD
        ),
        phase=Phase.BOARD,
    )

    game.run_turn()

    # Centaur warped to 4, then rolled 1 but then warped to space 4
    assert game.get_racer(0).position == 4
    # Scoocher was NOT trampled (stays at 2) because Warps don't "Pass"
    assert game.get_racer(1).position == 2
