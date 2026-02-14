from magical_athlete_simulator.engine.scenario import GameScenario, RacerConfig


def test_mouth_eats_exactly_one_victim(scenario: type[GameScenario]):
    """
    Mouth should eliminate exactly one other racer when landing/warping onto a tile
    occupied by exactly one other racer. [code_file:49]
    """
    game = scenario(
        [
            RacerConfig(0, "Mouth", start_pos=10),
            RacerConfig(1, "Banana", start_pos=14),
        ],
        dice_rolls=[4],  # Mouth 10 -> 14
    )

    game.run_turn()

    mouth = game.get_racer(0)
    banana = game.get_racer(1)

    assert mouth.position == 14
    assert banana.eliminated is True
    assert banana.active is False  # active := not finished and not eliminated [code_file:17]


def test_mouth_does_not_eat_if_two_targets_present(scenario: type[GameScenario]):
    """
    Mouth only eats if exactly one other racer shares its tile (len(others_on_space) == 1). [code_file:49]
    If it lands on a tile with two other racers, it should skip. [code_file:49]
    """
    game = scenario(
        [
            RacerConfig(0, "Mouth", start_pos=10),
            RacerConfig(1, "Banana", start_pos=14),
            RacerConfig(2, "Hare", start_pos=14),
        ],
        dice_rolls=[4],
    )

    game.run_turn()

    assert game.get_racer(1).eliminated is False
    assert game.get_racer(2).eliminated is False

def test_mouth_eats_last_opponent_race_over_and_winner_scored(scenario: type[GameScenario]):
    game = scenario(
        [
            RacerConfig(0, "Mouth", start_pos=10),
            RacerConfig(1, "Banana", start_pos=14),
        ],
        dice_rolls=[4],  # Mouth lands on Banana and eats
    )

    game.run_turn()

    mouth = game.get_racer(0)
    banana = game.get_racer(1)

    assert banana.eliminated is True
    assert game.state.race_active is False 
    assert mouth.finished is True
    assert mouth.finish_position == 1
    assert mouth.victory_points == 4

def test_hare_hubris_skip_still_works_after_mouth_elimination(scenario: type[GameScenario]):
    """
    Sequence:
    - Mouth eats Banana on turn 1.
    - Next up: Hare is sole leader at start of their turn -> should skip moving (hubris).
    """
    game = scenario(
        [
            RacerConfig(0, "Mouth", start_pos=0),
            RacerConfig(1, "Banana", start_pos=3),
            RacerConfig(2, "Hare", start_pos=10),
        ],
        dice_rolls=[3, 6, 6],  # Hare roll values shouldn't matter if hubris causes skip
    )

    game.run_turn()  # Mouth: 0->3 eats Banana
    assert game.get_racer(1).eliminated is True

    hare_before = game.get_racer(2).position
    game.run_turn()  # Hare turn
    hare_after = game.get_racer(2).position

    assert hare_after == hare_before, "Hare should skip when sole leader at turn start."


def test_lovable_loser_bonus_still_applies_after_mouth_elimination(scenario: type[GameScenario]):
    """
    After Mouth removes a racer, LovableLoser should still correctly detect being sole last
    and gain +1 VP at turn start. [code_file:17]
    """
    game = scenario(
        [
            RacerConfig(0, "Mouth", start_pos=3),
            RacerConfig(1, "Banana", start_pos=6),
            RacerConfig(2, "LovableLoser", start_pos=0),
        ],
        dice_rolls=[3, 3, 3],
    )

    game.run_turn()  # Mouth: 3->6 eats Banana
    assert game.get_racer(1).eliminated is True

    ll = game.get_racer(2)
    assert ll.victory_points == 0
    game.run_turn()  # LovableLoser turn start should award +1 VP
    assert game.get_racer(2).victory_points == 1

def test_mouth_finish_leaves_sole_survivor_crash(scenario: type[GameScenario]):
    game = scenario(
        [
            RacerConfig(0, "Mouth", start_pos=25),
            RacerConfig(1, "Centaur", start_pos=29),
            RacerConfig(2, "LovableLoser", start_pos=0),
        ],
        dice_rolls=[
            4,   # Mouth eats Centaur
            3,   # LovableLoser moves
            3,  # Mouth finishes
            3,   # Next roll (if game doesn't end, LL tries to move and crashes)
        ],
    )

    game.run_turns(3)

    assert game.get_racer(0).finish_position == 1 
    
    # this crashes if LovableLoser has another turn
    game.run_turn()

    assert game.get_racer(2).finish_position == 2
