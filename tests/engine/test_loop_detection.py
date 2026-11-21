from magsim.engine.board import BOARD_DEFINITIONS
from magsim.engine.loop_detection import MAX_EVENTS_PER_TURN, LoopDetector
from magsim.engine.scenario import GameScenario, RacerConfig


def test_event_cap_aborts_cascades_with_ever_changing_board_state():
    detector = LoopDetector()

    assert not any(detector.check_global_sanity(h) for h in range(MAX_EVENTS_PER_TURN))
    assert detector.check_global_sanity(MAX_EVENTS_PER_TURN)


def test_event_cap_resets_each_turn():
    detector = LoopDetector()
    for h in range(MAX_EVENTS_PER_TURN):
        detector.check_global_sanity(h)

    detector.reset_for_turn()

    assert not detector.check_global_sanity(0)


def test_scoocher_understudy_cascade_on_bonkbug_board_is_aborted():
    """Two Scoocher-likes plus Romantic/Copycat never repeat a board state, so only the event cap ends the turn."""
    board = BOARD_DEFINITIONS["TwistyTwirl"]()
    board.forced_twists = ["Bonkbug"]
    game = GameScenario(
        [
            RacerConfig(0, "Understudy"),
            RacerConfig(1, "Romantic"),
            RacerConfig(2, "Scoocher"),
            RacerConfig(3, "Copycat"),
        ],
        board=board,
        seed=2590,
    )

    game.run_turn()

    assert game.engine.bug_reason == "CRITICAL_LOOP_DETECTED"
