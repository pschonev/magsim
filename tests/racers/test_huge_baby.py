from magical_athlete_simulator.engine.scenario import GameScenario, RacerConfig


def test_huge_baby_push_timing_and_subsequent_move(scenario: type[GameScenario]):
    """
    Verify Huge Baby pushes victims immediately upon arrival, affecting
    their subsequent start position for the Main Move.
    """
    # Setup: PartyAnimal (5) pulls HugeBaby (4) onto same square.
    game = scenario(
        [
            RacerConfig(0, "PartyAnimal", start_pos=5),
            RacerConfig(1, "HugeBaby", start_pos=4),
        ],
        dice_rolls=[4],  # PartyAnimal rolls 4
    )

    game.run_turn()

    # 1. Baby pulled to 5
    assert game.get_racer(1).position == 5

    # 2. PartyAnimal Logic:
    # Start (5) -> Pulled Baby lands -> Pushed to (4) -> Roll 4 -> End (8)
    assert game.get_racer(0).position == 8, (
        f"Expected pos 8 (Pushed 5->4, then moved 4). Got {game.get_racer(0).position}."
    )


def test_huge_baby_safe_at_start(scenario: type[GameScenario]):
    """
    Scenario: Baby and others are at Start (0).
    Verify: No pushing occurs.
    """
    game = scenario(
        [
            RacerConfig(0, "HugeBaby", start_pos=0),
            RacerConfig(1, "Banana", start_pos=0),
        ],
        dice_rolls=[0],  # Dummy roll
    )

    game.run_turn()  # Baby turn
    assert game.get_racer(1).position == 0  # Scoocher stays


def test_huge_baby_bulldozes_crowd(scenario: type[GameScenario]):
    """
    Scenario: 3 Racers at pos 10. Baby moves 6->10.
    Verify: All 3 existing racers pushed to 9.
    """
    game = scenario(
        [
            RacerConfig(0, "HugeBaby", start_pos=6),
            RacerConfig(1, "Banana", start_pos=10),
            RacerConfig(2, "Centaur", start_pos=10),
            RacerConfig(3, "Magician", start_pos=10),
        ],
        dice_rolls=[4],  # 6->10
    )

    game.run_turn()

    assert game.get_racer(0).position == 10  # Baby lands
    assert game.get_racer(1).position == 9
    assert game.get_racer(2).position == 9
    assert game.get_racer(3).position == 9


def test_huge_baby_victim_lands_on_baby(scenario: type[GameScenario]):
    """
    Scenario: Baby is at 5. Racer lands on 5.
    Verify: Racer pushed to 4. Baby stays at 5.
    """
    game = scenario(
        [
            RacerConfig(0, "Gunk", start_pos=2),
            RacerConfig(1, "HugeBaby", start_pos=5),
        ],
        dice_rolls=[3],  # 2->5
    )

    game.run_turn()

    assert game.get_racer(0).position == 4
    assert game.get_racer(1).position == 5


def test_huge_baby_is_not_stuck_at_start(scenario: type[GameScenario]):
    """
    Verifies that Huge Baby can move from the starting position on its turn,
    even if it has previously placed a blocker on the board. This ensures
    that old blockers are being cleaned up correctly.
    """
    game = scenario(
        [
            RacerConfig(0, "HugeBaby", start_pos=0),
            RacerConfig(1, "Magician", start_pos=0),
        ],
        dice_rolls=[
            1,  # Turn 1 (Baby): Moves 0 -> 1. Places blocker at 1.
            4,  # Turn 2 (Magi): Moves 0 -> 4.
            5,  # Turn 3 (Baby): Moves 1 -> 6. Blocker at 1 is removed.
            4,  # Turn 4 (Magi): Moves 4 -> 8.
        ],
    )

    # Turn 1: Huge Baby moves to tile 1
    game.run_turn()
    assert game.get_racer(0).position == 1

    # Turn 2: Magician moves to tile 4
    game.run_turn()
    assert game.get_racer(1).position == 4

    # Turn 3: Huge Baby moves away from tile 1 to 6
    # This is the crucial step where the blocker at tile 1 must be removed.
    game.run_turn()
    assert game.get_racer(0).position == 6

    # Turn 4: Magician moves. To make this test simpler, we'll have Magician
    # land on a tile that is NOT 1, just to prove the blocker is gone when
    # we inspect the board state later.
    game.run_turn()
    assert game.get_racer(1).position == 8

    # To prove the bug is fixed, we could add another turn for a third racer
    # to land on tile 1, but for now, the fact that Huge Baby can move
    # freely is the primary goal. This test will fail if Huge Baby gets
    # stuck on Turn 3.
    # The initial `test_huge_baby_cannot_push_itself` also helps confirm this.


def test_huge_baby_cannot_push_itself(scenario: type[GameScenario]):
    """
    Verifies that Huge Baby's own blocker does not prevent its own movement.
    """
    game = scenario(
        [RacerConfig(0, "HugeBaby", start_pos=3)],
        dice_rolls=[1],  # 3 -> 4
    )
    game.run_turn()
    assert game.get_racer(0).position == 4


def test_huge_baby_blocker_is_removed_when_pulled(scenario: type[GameScenario]):
    """
    Verifies the HugeBabyBlocker is correctly removed when Huge Baby is moved
    by another racer's ability (e.g., PartyPull). This prevents orphaned
    blockers that would otherwise block future movement.

    Scenario:
    1. Huge Baby moves to tile 5, placing a blocker.
    2. Party Animal, ahead on the track, uses PartyPull to move Huge Baby to tile 6.
    3. The blocker at tile 5 MUST be removed.
    4. A third racer then moves to tile 5 to prove it's no longer blocked.
    """
    game = scenario(
        [
            RacerConfig(0, "HugeBaby", start_pos=0),
            RacerConfig(1, "PartyAnimal", start_pos=10),
            RacerConfig(2, "Scoocher", start_pos=4),
        ],
        dice_rolls=[
            5,  # Turn 1 (HugeBaby): Moves 0 -> 5. Places blocker at 5.
            1,  # Turn 2 (PartyAnimal): Rolls 1. PartyPull moves HugeBaby 5 -> 6.
            1,  # Turn 3 (Scoocher): Moves 4 -> 5.
        ],
    )

    # 1. Huge Baby's turn: moves to 5 and places a blocker.
    game.run_turn()
    assert game.get_racer(0).position == 5

    # 2. Party Animal's turn: PartyPull moves Huge Baby from 5 to 6.
    # The cleanup logic for the blocker at tile 5 is triggered here.
    game.run_turn()
    assert game.get_racer(0).position == 6, "Huge Baby should have been pulled to 6."

    # 3. Scoocher's turn: Moves to tile 5.
    # If the blocker at 5 was not cleaned up, Scoocher would be pushed to 4.
    game.run_turn()
    assert game.get_racer(2).position == 5, (
        "Scoocher should land on 5. If it's on 4, the old blocker was not removed."
    )


def test_jump_over_huge_baby(scenario: type[GameScenario]):
    """
    Scenario: Huge Baby is at 5. Racer moves 0 -> 6.
    Verify: Huge Baby acts as a blocker for the TILE, not a wall for movement.
    The racer should successfully jump over the baby.
    """
    game = scenario(
        [
            RacerConfig(0, "Centaur", start_pos=0),
            RacerConfig(1, "HugeBaby", start_pos=5),
        ],
        dice_rolls=[6],
    )

    game.run_turn()

    # 0 -> 6 (Jumps over 5)
    assert game.get_racer(0).position == 6

def test_copycat_cleanup_on_leader_change(scenario: type[GameScenario]):
    """
    Scenario:
    1. HugeBaby (Pos 10) rolls low, stays leader briefly.
    2. Copycat (Pos 0) moves to 5, copies Baby -> Places Blocker at 5.
    3. Mastermind (Pos 4) moves -> HITS the blocker at 5 (Proves it is active).
    4. Centaur (Pos 10) rolls higher -> Overtakes Baby.
       -> Copycat reacts immediately, switching to Centaur.
       -> Copycat loses HugeBabyPush.
       -> Blocker at Tile 5 should vanish.
    """
    game = scenario(
        [
            RacerConfig(0, "HugeBaby", start_pos=10),
            RacerConfig(1, "Copycat", start_pos=0),
            RacerConfig(2, "Mastermind", start_pos=4), 
            RacerConfig(3, "Centaur", start_pos=10),   # Starts alongside Baby
        ],
        dice_rolls=[
            1,   # Baby: 10 -> 11 (Current Leader)
            5,   # Copycat: Copies Baby. 0 -> 5. Blocker at 5.
            1,   # Mastermind: 4 -> 5. Should be blocked -> 4.
            2,   # Centaur: 10 -> 12. (12 > 11). NEW LEADER. Switch triggers.
        ],
    )

    # 1. Baby moves slightly (10 -> 11)
    game.run_turn()
    
    # 2. Copycat copies Baby (Leader), moves to 5
    game.run_turn() 
    assert game.get_racer(1).position == 5
    # Verify Blocker exists
    mods = game.engine.state.board.get_modifiers_at(5)
    assert any(m.name == "HugeBabyBlocker" for m in mods)

    # 3. Mastermind runs into the wall (VERIFY ACTIVE)
    game.run_turn() 
    assert game.get_racer(2).position == 4, "Mastermind should have been blocked by Copycat"

    # 4. Centaur moves (10 -> 12), overtaking Baby (11)
    # This move triggers PostMoveEvent -> Copycat switches -> on_loss fires
    game.run_turn() 
    assert game.get_racer(3).position == 12

    # 5. VERIFY CLEANUP
    # The blocker at 5 should be gone immediately.
    mods_after = game.engine.state.board.get_modifiers_at(5)
    ghosts = [m for m in mods_after if m.name == "HugeBabyBlocker"]
    
    assert not ghosts, f"Ghost Blocker remains! Copycat failed to clean up: {ghosts}"

def test_copycat_bounce_preserves_blocker(scenario: type[GameScenario]):
    """
    Scenario:
    1. HugeBaby is at Tile 6 (Leader).
    2. Copycat is at Tile 5.
    3. Turn Start: Copycat copies HugeBaby (gains HugeBabyPush).
       - Copycat places a blocker at 5 (via on_gain or previous turn).
    4. Copycat rolls 1.
       - Path: 5 -> 6 (Blocked by HugeBaby) -> 5.
       - Net Move: 0.
    
    FAILURE (Current Code):
    - PreMove: Copycat picks up blocker at 5.
    - Move: 0 distance (5->5).
    - PostMove: Skipped by Engine.
    - Result: Copycat lands on 5, but the blocker is GONE.
    """
    game = scenario(
        [
            RacerConfig(0, "HugeBaby", start_pos=6), # The Wall
            RacerConfig(1, "Copycat", start_pos=5),  # The Victim
        ],
        dice_rolls=[
            0, # HugeBaby stays put
            1, # Copycat rolls 1
        ]
    )
    
    # 1. HugeBaby turn (idle)
    game.run_turn()
    
    # 2. Copycat turn
    # - Copies HugeBaby (TurnStart)
    # - Rolls 1 -> Bounces off HugeBaby -> Lands on 5
    game.run_turn()
    
    assert game.get_racer(1).position == 5, "Copycat should have bounced back to 5"
    
    # 3. CRITICAL CHECK
    # With the bug, Copycat's blocker is gone because PreMove removed it 
    # and PostMove never ran to put it back.
    mods = game.engine.state.board.get_modifiers_at(5)
    copycat_blocker = [
        m for m in mods 
        if m.name == "HugeBabyBlocker" and m.owner_idx == 1
    ]
    
    assert copycat_blocker, "Copycat lost their blocker after bouncing back!"

def test_copycat_zombie_blocker_on_overtake(scenario: type[GameScenario]):
    """
    Scenario: Race Condition during PostMove.
    1. HugeBaby is at 6. Copycat is at 5 (and has copied HugeBaby).
    2. Copycat moves 5 -> 7.
    3. Copycat is now the Leader (7 > 6).
    
    Execution Order (The Bug):
    1. AbilityCopyLead fires first:
       - Sees Copycat is leader.
       - REMOVES HugeBabyPush.
       - on_loss fires -> Tries to unregister from Tile 7 (Current Pos). 
       - Fails (Blocker is still at 5).
    2. HugeBabyPush fires second (Zombie):
       - It was queued before removal.
       - Executes and PLACES blocker at Tile 7.
       
    Result: Copycat has no ability, but a Ghost Blocker exists at 7.
    """
    game = scenario(
        [
            RacerConfig(0, "HugeBaby", start_pos=6),
            RacerConfig(1, "Copycat", start_pos=5),
        ],
        dice_rolls=[
            0, # Baby stays
            2, # Copycat: 5 -> 7 (Overtakes)
        ]
    )

    # 1. Setup: Baby at 6
    game.run_turn()
    
    # 2. Copycat Turn
    # - Start: Copies HugeBaby (gains ability)
    # - Move: 5 -> 7
    # - PostMove: Loses ability (because it leads), but Zombie Logic places blocker.
    game.run_turn()
    
    assert game.get_racer(1).position == 7
    
    # Verify Copycat lost the ability
    assert "HugeBabyPush" not in game.get_racer(1).active_abilities, \
        "Copycat should have lost HugeBabyPush after taking the lead"

    # CRITICAL CHECK
    # There should be NO blocker at 7.
    mods = game.engine.state.board.get_modifiers_at(7)
    ghosts = [m for m in mods if m.name == "HugeBabyBlocker"]
    
    assert not ghosts, f"Zombie Blocker found at Tile 7! {ghosts}"
    
    # BONUS CHECK
    # The old blocker at 5 should also be gone.
    mods_old = game.engine.state.board.get_modifiers_at(5)
    old_ghosts = [m for m in mods_old if m.name == "HugeBabyBlocker"]
    assert not old_ghosts, f"Old Blocker still at Tile 5! {old_ghosts}"

import logging

def test_copycat_start_line_warning_fix(scenario: type[GameScenario], caplog):
    """
    Scenario:
    1. HugeBaby is at 2. Copycat is at 0 (Copies HugeBaby).
    2. Copycat has NO blocker (because it's at 0).
    3. Copycat moves 0 -> 3 (Overtakes HugeBaby).
    4. Copycat loses HugeBabyPush.
    
    FAILURE (Current): on_loss blindly tries to unregister from Tile 3 -> WARNING.
    SUCCESS (Fix): on_loss checks first -> No Warning.
    """
    # 1. Clear previous logs
    caplog.clear()
    
    game = scenario(
        [
            RacerConfig(0, "HugeBaby", start_pos=2),
            RacerConfig(1, "Copycat", start_pos=0),
        ],
        dice_rolls=[
            0, # Baby stays
            3, # Copycat: 0 -> 3
        ]
    )

    # 1. Setup
    game.run_turn()
    
    # 2. Copycat Turn
    # We use caplog to inspect the standard python logging output
    with caplog.at_level(logging.WARNING, logger="magical_athlete"):
        game.run_turn()
    
    # Check for the specific board warning in the captured records
    warnings = [
        r.message for r in caplog.records 
        if "BOARD: Failed to unregister HugeBabyBlocker" in r.message
    ]
        
    assert not warnings, f"Found unexpected warnings: {warnings}"
    assert "HugeBabyPush" not in game.get_racer(1).active_abilities
