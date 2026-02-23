import logging
import pytest
from magsim.engine.scenario import GameScenario, RacerConfig


def test_huge_baby_push_timing_and_subsequent_move(scenario: type[GameScenario]):
    """
    Huge Baby pushes victims immediately upon arrival (pulled by PartyAnimal).
    The victim's subsequent move starts from the pushed position.
    """
    game = scenario(
        [
            RacerConfig(0, "PartyAnimal", start_pos=5),
            RacerConfig(1, "HugeBaby", start_pos=4),
        ],
        dice_rolls=[4], 
    )

    game.run_turn()

    # Baby pulled to 5
    assert game.get_racer(1).position == 5

    # PartyAnimal: Start 5 -> Pulled Baby (lands on 5) -> Pushed to 4 -> Moves +4 -> End 8
    assert game.get_racer(0).position == 8


def test_huge_baby_safe_at_start(scenario: type[GameScenario]):
    """
    No pushing occurs at the starting line (pos 0).
    """
    game = scenario(
        [
            RacerConfig(0, "HugeBaby", start_pos=0),
            RacerConfig(1, "Banana", start_pos=0),
        ],
        dice_rolls=[0],
    )

    game.run_turn()
    assert game.get_racer(1).position == 0


def test_huge_baby_bulldozes_crowd(scenario: type[GameScenario]):
    """
    Huge Baby landing on a tile pushes ALL existing racers backward.
    """
    game = scenario(
        [
            RacerConfig(0, "HugeBaby", start_pos=6),
            RacerConfig(1, "Banana", start_pos=10),
            RacerConfig(2, "Centaur", start_pos=10),
            RacerConfig(3, "Magician", start_pos=10),
        ],
        dice_rolls=[4],  # 6 -> 10
    )

    game.run_turn()

    assert game.get_racer(0).position == 10  # Baby lands
    assert game.get_racer(1).position == 9
    assert game.get_racer(2).position == 9
    assert game.get_racer(3).position == 9


def test_huge_baby_victim_lands_on_baby(scenario: type[GameScenario]):
    """
    Racer landing on Huge Baby's tile is pushed backward. Baby stays put.
    """
    game = scenario(
        [
            RacerConfig(0, "Gunk", start_pos=2),
            RacerConfig(1, "HugeBaby", start_pos=5),
        ],
        dice_rolls=[3],  # 2 -> 5
    )

    game.run_turn()

    assert game.get_racer(0).position == 4  # Pushed back
    assert game.get_racer(1).position == 5


def test_huge_baby_is_not_stuck_at_start(scenario: type[GameScenario]):
    """
    Huge Baby can move from start freely, cleaning up its initial blocker.
    """
    game = scenario(
        [
            RacerConfig(0, "HugeBaby", start_pos=0),
            RacerConfig(1, "Banana", start_pos=0),
        ],
        dice_rolls=[
            1,  # Turn 1: Baby 0 -> 1. Blocker at 1.
            4,  # Turn 2: Banana 0 -> 4.
            5,  # Turn 3: Baby 1 -> 6. Blocker at 1 removed.
            4,  # Turn 4: Banana 4 -> 8.
        ],
    )

    game.run_turn()
    assert game.get_racer(0).position == 1

    game.run_turn()
    assert game.get_racer(1).position == 4

    game.run_turn()
    assert game.get_racer(0).position == 6

    game.run_turn()
    assert game.get_racer(1).position == 8


def test_huge_baby_cannot_push_itself(scenario: type[GameScenario]):
    """
    Huge Baby's own blocker does not impede its own movement.
    """
    game = scenario(
        [RacerConfig(0, "HugeBaby", start_pos=3)],
        dice_rolls=[1],
    )
    game.run_turn()
    assert game.get_racer(0).position == 4


def test_huge_baby_blocker_is_removed_when_pulled(scenario: type[GameScenario]):
    """
    Blocker is correctly removed when Huge Baby is moved by another ability (PartyPull).
    """
    game = scenario(
        [
            RacerConfig(0, "HugeBaby", start_pos=0),
            RacerConfig(1, "PartyAnimal", start_pos=10),
            RacerConfig(2, "Scoocher", start_pos=4),
        ],
        dice_rolls=[
            5,  # Turn 1: Baby 0 -> 5 (Blocker at 5)
            1,  # Turn 2: PartyAnimal. Pulls Baby 5 -> 6. (Blocker at 5 removed)
            1,  # Turn 3: Scoocher 4 -> 5.
        ],
    )

    game.run_turn()
    assert game.get_racer(0).position == 5

    game.run_turn()
    assert game.get_racer(0).position == 6

    game.run_turn()
    # Should land on 5. If blocked, would be 4.
    assert game.get_racer(2).position == 5


def test_jump_over_huge_baby(scenario: type[GameScenario]):
    """
    Huge Baby blocks the TILE, but does not prevent jumping over it.
    """
    game = scenario(
        [
            RacerConfig(0, "Centaur", start_pos=0),
            RacerConfig(1, "HugeBaby", start_pos=5),
        ],
        dice_rolls=[6],
    )

    game.run_turn()
    assert game.get_racer(0).position == 6


def test_copycat_cleanup_on_leader_change(scenario: type[GameScenario]):
    """
    Copycat copies HugeBaby (placing blocker), then switches to Centaur.
    Verify the old blocker is removed immediately.
    """
    game = scenario(
        [
            RacerConfig(0, "HugeBaby", start_pos=10),
            RacerConfig(1, "Copycat", start_pos=0),
            RacerConfig(2, "Mastermind", start_pos=4), 
            RacerConfig(3, "Centaur", start_pos=10),
        ],
        dice_rolls=[
            1,   # Baby 10 -> 11 (Leader)
            5,   # Copycat 0 -> 5 (Copies Baby, Blocker at 5)
            1,   # Mastermind 4 -> 5 (Blocked -> 4)
            2,   # Centaur 10 -> 12 (New Leader) -> Copycat switches
        ],
    )

    game.run_turn() # Baby
    
    game.run_turn() # Copycat
    assert game.get_racer(1).position == 5
    assert any(m.name == "HugeBabyBlocker" for m in game.engine.state.board.get_modifiers_at(5))

    game.run_turn() # Mastermind
    assert game.get_racer(2).position == 4

    game.run_turn() # Centaur
    assert game.get_racer(3).position == 12

    # Verify Cleanup
    mods_after = game.engine.state.board.get_modifiers_at(5)
    ghosts = [m for m in mods_after if m.name == "HugeBabyBlocker"]
    assert not ghosts, f"Ghost Blocker remains! {ghosts}"


def test_copycat_bounce_preserves_blocker(scenario: type[GameScenario]):
    """
    Copycat copies HugeBaby, bounces off a wall (Baby), and lands back on its start.
    Verify the blocker is preserved/restored at the landing position.
    """
    game = scenario(
        [
            RacerConfig(0, "HugeBaby", start_pos=6),
            RacerConfig(1, "Copycat", start_pos=5),
        ],
        dice_rolls=[0, 1]
    )
    
    game.run_turn() # Baby
    
    game.run_turn() # Copycat (5 -> 6 -> 5)
    assert game.get_racer(1).position == 5
    
    mods = game.engine.state.board.get_modifiers_at(5)
    copycat_blocker = [
        m for m in mods 
        if m.name == "HugeBabyBlocker" and m.owner_idx == 1
    ]
    assert copycat_blocker, "Copycat lost their blocker after bouncing back!"


def test_copycat_zombie_blocker_on_overtake(scenario: type[GameScenario]):
    """
    Race condition check: Copycat overtakes leader (losing ability).
    Verify no 'zombie' blocker is placed at the new position by the ability logic 
    firing out of order.
    """
    game = scenario(
        [
            RacerConfig(0, "HugeBaby", start_pos=6),
            RacerConfig(1, "Copycat", start_pos=5),
        ],
        dice_rolls=[0, 2] # Copycat 5 -> 7
    )

    game.run_turn() # Baby
    
    game.run_turn() # Copycat
    assert game.get_racer(1).position == 7
    assert "HugeBabyPush" not in game.get_racer(1).active_abilities

    # Verify No Blocker at 7
    mods = game.engine.state.board.get_modifiers_at(7)
    assert not any(m.name == "HugeBabyBlocker" for m in mods)
    
    # Verify Old Blocker at 5 is gone
    mods_old = game.engine.state.board.get_modifiers_at(5)
    assert not any(m.name == "HugeBabyBlocker" for m in mods_old)


def test_copycat_start_line_warning_fix(scenario: type[GameScenario], caplog: pytest.LogCaptureFixture):
    """
    Copycat loses HugeBaby ability after moving from Start (0).
    Verify no warnings are logged about failing to unregister a non-existent blocker.
    """
    caplog.clear()
    
    game = scenario(
        [
            RacerConfig(0, "HugeBaby", start_pos=2),
            RacerConfig(1, "Copycat", start_pos=0),
        ],
        dice_rolls=[0, 3]
    )

    game.run_turn() # Baby
    
    with caplog.at_level(logging.WARNING, logger="magical_athlete"):
        game.run_turn() # Copycat
    
    warnings = [
        r.message for r in caplog.records 
        if "BOARD: Failed to unregister HugeBabyBlocker" in r.message
    ]
    assert not warnings
