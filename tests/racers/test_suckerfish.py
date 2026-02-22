from magical_athlete_simulator.engine.scenario import GameScenario, RacerConfig


def test_suckerfish_follows_mover(scenario: type[GameScenario]):
    """Suckerfish moves to leader's end tile when leader leaves shared space."""
    game = scenario(
        [
            RacerConfig(0, "Banana", start_pos=5),
            RacerConfig(1, "Suckerfish", start_pos=5),
        ],
        dice_rolls=[3],  # Banana moves
    )
    
    game.run_turn()  # Banana turn: 5 -> 8
    sucker = game.get_racer(1)
    assert sucker.position == 8, "Suckerfish should follow to 8"

def test_suckerfish_ignores_wrong_start(scenario: type[GameScenario]):
    """Suckerfish ignores if leader did not start on shared space."""
    game = scenario(
        [
            RacerConfig(0, "Banana", start_pos=6),  # Different start
            RacerConfig(1, "Suckerfish", start_pos=5),
        ],
        dice_rolls=[3],
    )
    
    game.run_turn()
    sucker = game.get_racer(1)
    assert sucker.position == 5, "Should not move (wrong start tile)"

def test_suckerfish_rides_leaptoad_jump(scenario: type[GameScenario]):
    """
    Suckerfish should arrive at the FINAL destination of a Leaptoad, 
    even if Leaptoad jumped over obstacles.
    """
    game = scenario(
        [
            RacerConfig(0, "Leaptoad", start_pos=5),
            RacerConfig(1, "Suckerfish", start_pos=5),
            RacerConfig(2, "Banana", start_pos=7),  # Obstacle at 7
        ],
        dice_rolls=[2],  # Leaptoad rolls 2
    )

    # Leaptoad moves 2: 5 -> 6 -> 7(blocked) -> 8.
    game.run_turn()
    leaptoad = game.get_racer(0)
    sucker = game.get_racer(1)

    assert leaptoad.position == 8, "Leaptoad should jump obstacle at 7"
    assert sucker.position == 8, "Suckerfish should land on Leaptoad's final tile (8)"


def test_suckerfish_rides_hare_speed_bonus(scenario: type[GameScenario]):
    """
    Suckerfish should ride the full distance including Hare's speed bonus.
    """
    game = scenario(
        [
            RacerConfig(0, "Hare", start_pos=5),
            RacerConfig(1, "Suckerfish", start_pos=5),
        ],
        dice_rolls=[3],  # Hare rolls 3 (+2 bonus = 5)
    )

    # Hare moves 3 + 2 = 5 spaces. 5 -> 10.
    game.run_turn()
    hare = game.get_racer(0)
    sucker = game.get_racer(1)

    assert hare.position == 10, "Hare moves 5 spaces (3+2)"
    assert sucker.position == 10, "Suckerfish follows Hare to 10"


def test_suckerfish_rides_hare_into_huge_baby(scenario: type[GameScenario]):
    """
    Suckerfish should end up where the Hare FINALLY lands, 
    even if Hare was pushed back by Huge Baby.
    """
    game = scenario(
        [
            RacerConfig(0, "Hare", start_pos=5),
            RacerConfig(1, "Suckerfish", start_pos=5),
            RacerConfig(2, "HugeBaby", start_pos=10),
        ],
        dice_rolls=[3],  # Hare rolls 3 (+2 bonus = 5) -> Lands on 10
    )

    # 1. Hare moves 5 -> 10.
    # 2. HugeBaby pushes Hare 10 -> 9.
    # 3. PostMoveEvent emitted for 5 -> 9.
    # 4. Suckerfish triggers on 5 -> 9 move.
    
    game.run_turn()
    hare = game.get_racer(0)
    sucker = game.get_racer(1)

    assert hare.position == 9, "Hare pushed back by HugeBaby (10 -> 9)"
    assert sucker.position == 9, "Suckerfish follows to FINAL destination (9)"

def test_suckerfish_follows_centaur_across_finish_line(scenario: type[GameScenario]):
    """
    Suckerfish should follow a racer (Centaur) who crosses the finish line,
    successfully finishing the race in 2nd place.
    """
    game = scenario(
        [
            # Placed near the end of the track (assuming standard length, e.g., 39)
            RacerConfig(0, "Centaur", start_pos=28),
            RacerConfig(1, "Suckerfish", start_pos=28),
            RacerConfig(2, "Banana", start_pos=10),
        ],
        dice_rolls=[6],  # Centaur rolls enough to cross the finish line
    )

    game.run_turn()
    centaur = game.get_racer(0)
    sucker = game.get_racer(1)

    assert not centaur.active, "Centaur should have finished the race (inactive)"
    assert not sucker.active, "Suckerfish should have followed and finished the race (inactive)"
    assert sucker.position == centaur.position, "Suckerfish should end on the same finishing space"


def test_suckerfish_follows_mouth_across_finish_line(scenario: type[GameScenario]):
    """
    Suckerfish should follow Mouth across the finish line. 
    Because racer powers deactivate when they finish the race, Mouth's elimination
    power does not trigger, allowing Suckerfish to safely claim 2nd place.
    """
    game = scenario(
        [
            RacerConfig(0, "Mouth", start_pos=28),
            RacerConfig(1, "Suckerfish", start_pos=28),
            RacerConfig(2, "Banana", start_pos=10),
        ],
        dice_rolls=[6],  # Mouth rolls enough to cross the finish line
    )

    game.run_turn()
    mouth = game.get_racer(0)
    sucker = game.get_racer(1)

    assert not mouth.active, "Mouth should have finished the race"
    assert not sucker.active, "Suckerfish should have finished the race"
    assert sucker.position == mouth.position, "Suckerfish safely reached the finish line with Mouth"
