from magical_athlete_simulator.engine.scenario import GameScenario, RacerConfig


def test_lovable_loser_vp_gain(scenario: type[GameScenario]):
    """Lovable Loser gains 1 VP at start of turn if strictly in last place."""
    game = scenario(
        [
            RacerConfig(0, "LovableLoser", start_pos=0),
            RacerConfig(1, "Banana", start_pos=5),  # Ahead
            RacerConfig(2, "Mastermind", start_pos=1),
            RacerConfig(3, "Scoocher", start_pos=10),
        ],
        dice_rolls=[1],
    )

    game.run_turn()
    loser = game.get_racer(0)
    scoocher = game.get_racer(3)
    assert loser.victory_points == 1, "Should gain VP for being last"
    assert scoocher.position == 11


def test_lovable_loser_no_gain_if_tied(scenario: type[GameScenario]):
    """Lovable Loser gains nothing if tied for last place."""
    game = scenario(
        [
            RacerConfig(0, "LovableLoser", start_pos=0),
            RacerConfig(1, "Banana", start_pos=0),  # Tied last
        ],
        dice_rolls=[1],
    )

    game.run_turn()
    loser = game.get_racer(0)
    assert loser.victory_points == 0, "Should NOT gain VP if tied for last"
