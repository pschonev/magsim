from magsim.engine.scenario import GameScenario, RacerConfig


def test_skipper_skipping(scenario: type[GameScenario]):
    """
    When Skipper steals a turn, it should skip intervening racers.
    Order: 0 (Roller), 1 (Skipped), 2 (Skipper).
    Racer 1 should receive a 'MainMoveSkippedEvent' or be logged as skipped.
    We verify the engine state knows 1 was skipped implicitly by checking turn order.
    """
    game = scenario(
        [
            RacerConfig(0, "Banana", start_pos=0),
            RacerConfig(1, "Centaur", start_pos=0),
            RacerConfig(2, "Skipper", start_pos=0),
        ],
        dice_rolls=[1, 5],
    )

    game.run_turns(2)
    assert game.get_racer(1).position == 0 # Verify Centaur (1) has NOT moved yet
    assert game.get_racer(2).position == 5
    assert game.state.current_racer_idx == 0


def test_skipper_does_not_trigger_on_non_one(scenario: type[GameScenario]):
    """
    Racer rolls 2. Skipper does nothing.
    """
    game = scenario(
        [
            RacerConfig(0, "Banana", start_pos=0),
            RacerConfig(1, "Skipper", start_pos=0),
        ],
        dice_rolls=[2, 3],
    )

    game.run_turn()
    assert game.state.next_turn_override is None
    # Next turn should be Skipper (1) naturally
    game.run_turn()
    assert game.get_racer(1).position == 3


def test_skipper_multiple_skippers_race_condition(scenario: type[GameScenario]):
    """
    Two Skippers (2 and 3). Banana (0) rolls 1.
    Both trigger. The last one to trigger wins the override?
    Or logic handles it?
    Assuming standard priority:
    - Skipper 2 triggers -> override = 2.
    - Skipper 3 triggers -> override = 3.
    Final override should be 3.
    """
    game = scenario(
        [
            RacerConfig(0, "Banana", start_pos=0),
            RacerConfig(1, "Centaur", start_pos=0),
            RacerConfig(2, "Copycat", start_pos=0),  # A
            RacerConfig(3, "Skipper", start_pos=10),  # B
        ],
        dice_rolls=[2, 1],
    )

    game.run_turns(2)
    # Depending on implementation order (usually index order or registration order).
    # If they register in order 2, then 3:
    # 2 sets override 2.
    # 3 sets override 3.
    assert game.state.current_racer_idx == 3
