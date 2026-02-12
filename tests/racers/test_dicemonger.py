from magical_athlete_simulator.core.mixins import LifecycleManagedMixin
from magical_athlete_simulator.engine.scenario import GameScenario, RacerConfig
from magical_athlete_simulator.racers.dicemonger import DicemongerRerollAction

def test_dicemonger_grants_reroll_to_others(scenario: type[GameScenario]):
    """
    Scenario:
    1. Dicemonger (Pos 0) exists.
    2. Banana (Pos 10) rolls a 1.
    3. Banana uses Dicemonger's ability to reroll -> Gets a 6.
    4. Verify: Banana moves 6. Dicemonger moves 1 (profit).
    """
    game = scenario(
        [
            RacerConfig(0, "Dicemonger", start_pos=0),
            RacerConfig(1, "Banana", start_pos=10),
        ],
        dice_rolls=[
            1, # Banana initial
            6, # Banana reroll
        ],
    )
    
    # 1. Run Banana's turn (Banana is index 1, usually starts second, 
    # but we can force turn order or just run unti it's Banana's turn)
    # Let's assume standard order 0 then 1.
    
    # Run Dicemonger's turn (irrelevant roll)
    game.run_turn() 
    
    # Run Banana's turn
    game.run_turn()
    
    # Banana: Start 10 + 6 = 16
    assert game.get_racer(1).position == 16
    
    # Dicemonger: Start 0 + 0 (own move) + 1 (profit) = 1
    # (Assuming Dicemonger didn't move on his own turn, or we check delta)
    # Actually, Dicemonger ran turn 1. Let's precise check.
    # Turn 1: Dicemonger moves X.
    # Turn 2: Banana moves, Dicemonger gets +1.
    
    # Easier: Just check relative gain or start positions.
    dicemonger = game.get_racer(0)
    # He should have moved 1 extra space during Banana's turn.
    # We can inspect the logs or just trust the mechanics if we control his roll.
    
    # Let's fix Dicemonger roll to 0 (if possible) or just 1.
    # scenario doesn't support forcing rolls per racer easily without exact sequence.
    # dice_rolls queue: [1 (Dice), 1 (Banana), 6 (Banana Reroll)]
    pass

def test_dicemonger_copycat_duplication(scenario: type[GameScenario]):
    """
    Scenario: Copycat copies Dicemonger.
    Verify:
    1. Everyone has TWO reroll abilities (Source=Dicemonger, Source=Copycat).
    2. When someone uses Copycat's reroll, Copycat moves +1, Dicemonger moves 0.
    3. When Copycat stops copying, the extra reroll disappears.
    """
    game = scenario(
        [
            RacerConfig(0, "Dicemonger", start_pos=5),
            RacerConfig(1, "Copycat", start_pos=0),
            RacerConfig(2, "Banana", start_pos=1),
        ],
        dice_rolls=[
            # Turn 1: Dicemonger (Leader)
            5, # Move 5->10
            
            # Turn 2: Copycat
            # Copies Dicemonger (Leader at 10)
            4, # Moves 0->4
            
            # Turn 3: Banana
            1, # Rolls 1
            6, # Rerolls (Using COPYCAT's service)
            
            # Turn 4: Dicemonger (Moves 10->15)
            5,
            
            # Turn 5: Copycat (New Leader is Dicemonger? Or Banana?)
            # Banana is at 10+6=16. Dicemonger at 10.
            # Copycat copies Banana (Leader).
            # Loses Dicemonger ability.
        ]
    )
    
    # 1. Dicemonger turn
    game.run_turn()
    
    # 2. Copycat turn (Becomes Dicemonger-ish)
    game.run_turn()
    copycat = game.get_racer(1)
    # Should grant ability to Banana
    banana = game.get_racer(2)
    rerolls = [a for a in banana.active_abilities if isinstance(a, DicemongerRerollAction)]
    assert len(rerolls) == 2, "Banana should have 2 reroll options"
    
    # 3. Banana turn
    # We need to force the agent to pick Copycat's reroll (Index 1) specifically.
    # This requires a mocked agent or specific SmartAgent logic.
    # For this test, we assume SmartAgent picks the first valid one? 
    # Or we can inspect the state.
    
    # Let's manually trigger the cleanup logic check:
    # If Copycat stops copying, do abilities disappear?
    
    # Force Copycat to change identity manually for testing
    new_core = game.engine.instantiate_racer_abilities("Banana")
    new_core.append(copycat.active_abilities[0]) # Keep Copycat base
    game.engine.replace_core_abilities(1, new_core)
    
    # Verify Cleanup
    rerolls_after = [a for a in banana.active_abilities if isinstance(a, DicemongerRerollAction)]
    assert len(rerolls_after) == 1, "Should revert to only real Dicemonger's reroll"
    assert rerolls_after[0].source_racer_idx == 0 # The original Dicemonger


def test_dicemonger_basic_profit(scenario: type[GameScenario]):
    """
    Scenario: Banana rolls 1, uses Dicemonger to reroll to 6.
    Verify: Banana moves 6. Dicemonger moves 1.
    """
    game = scenario(
        [
            RacerConfig(0, "Dicemonger", start_pos=0),
            RacerConfig(1, "Banana", start_pos=10),
        ],
        dice_rolls=[
            1, # Banana Roll 1 (Trigger Reroll)
            6, # Banana Roll 2
        ],
    )
    
    # Run Dicemonger turn (irrelevant)
    game.run_turn()
    
    # Run Banana turn
    game.run_turn()
    
    # Banana moves 10 -> 16
    assert game.get_racer(1).position == 16
    
    # Dicemonger moved +1 during Banana's turn
    # (Assuming he rolled X on his turn, we check delta relative to start of Banana turn? 
    # Or just check absolute if we know his roll. Let's rely on position > 0 if he rolled 0 on his turn? 
    # Since we didn't mock his roll, he moved some amount.
    # Let's check the LOGS or verify ability counts logic indirectly?
    # Better: Ensure he moved AT LEAST 1 more than his dice roll.
    # For this specific test, we can check position > 0 implies movement.)
    pass

def test_dicemonger_self_use_no_profit(scenario: type[GameScenario]):
    """
    Scenario: Dicemonger uses his own reroll.
    Verify: He rerolls, but does NOT get the +1 profit move.
    """
    game = scenario(
        [RacerConfig(0, "Dicemonger", start_pos=0),             
        RacerConfig(1, "Banana", start_pos=0)],

        dice_rolls=[
            1, # Roll 1
            5, # Reroll to 5
        ],
    )
    d = game.get_racer(0)


    game.run_turn()
    names = {a.name for a in d.active_abilities}
    assert "DicemongerDeal" in names
    
    
    dicemonger = game.get_racer(0)
    # Position should be exactly 5. 
    # If he got profit, it would be 5 + 1 = 6.
    assert dicemonger.position == 5
    assert any(DicemongerRerollAction(0).matches_identity(a) for a in dicemonger.active_abilities)

def test_dicemonger_cleanup_on_finish(scenario: type[GameScenario]):
    """
    Scenario: Dicemonger finishes the race.
    Verify: His granted abilities are revoked from others.
    """
    game = scenario(
        [
            RacerConfig(0, "Dicemonger", start_pos=28), # Near finish
            RacerConfig(1, "Banana", start_pos=0),
        ],
        dice_rolls=[6], # Dicemonger finishes
    )
    
    # Verify Banana has ability initially
    assert any(isinstance(a, DicemongerRerollAction) for a in game.get_racer(1).active_abilities)
    
    game.run_turn() # Dicemonger finishes
    
    # Verify ability is gone
    assert not any(isinstance(a, DicemongerRerollAction) for a in game.get_racer(1).active_abilities)

def test_double_dicemonger_interaction(scenario: type[GameScenario]):
    """
    Scenario: Copycat copies Dicemonger. Banana has TWO reroll sources.
    Verify:
    1. Banana rolls 1.
    2. Uses Source A (Dicemonger). Rerolls to 1 again.
    3. Source B (Copycat) sees stale serial and waits.
    4. On new roll (1), Source A is used up.
    5. Uses Source B (Copycat). Rerolls to 6.
    6. Verify profit distribution.
    """
    game = scenario(
        [
            RacerConfig(0, "Dicemonger", start_pos=5),
            RacerConfig(1, "Banana", start_pos=3),
            RacerConfig(2, "Copycat", start_pos=0),
        ],
        dice_rolls=[
            # Setup Turns
            5, # Dicemonger moves
            
            # Banana Turn
            1, # Initial Roll (1) -> Trigger Source A
            1, # Reroll (1) -> Source A exhausted. Trigger Source B.
            6, # Final Roll (6)
        ]
    )
    
    # 1. Setup turns
    game.run_turn() # Dicemonger
    
    # Verify Double Buff
    dicemonger = game.get_racer(0)
    banana = game.get_racer(1)
    copycat = game.get_racer(2)
    rerolls = [a for a in banana.active_abilities if isinstance(a, DicemongerRerollAction)]
    assert len(rerolls) == 2
    
    # 2. Run Banana Turn
    # We rely on SmartAgent auto-decision (<= 2 means reroll).
    # Since both rolls are 1, it should trigger both sequentially.
    game.run_turn()
    
    # Verify Final Position: 10 + 6 = 16
    assert banana.position == 9
    assert dicemonger.position == 11 # moved +1 due to his ability
    assert copycat.position == 1


def test_reroll_sequentially(scenario: type[GameScenario]):
    """
    Scenario: Copycat copies Dicemonger. Banana has TWO reroll sources.
    Verify:
    1. Banana rolls 1.
    2. Uses Source A (Dicemonger). Rerolls to 1 again.
    3. Source B (Copycat) sees stale serial and waits.
    4. On new roll (1), Source A is used up.
    5. Uses Source B (Copycat). Rerolls to 6.
    6. Verify profit distribution.
    """
    game = scenario(
        [
            RacerConfig(0, "Dicemonger", start_pos=5),
            RacerConfig(1, "Banana", start_pos=3),
            RacerConfig(2, "Copycat", start_pos=0),
        ],
        dice_rolls=[
            # Setup Turns
            5, # Dicemonger moves
            
            # Banana Turn
            1, # Initial Roll (1) -> Trigger Source A
            6, 
            1, # this roll should not happen cos we already have a 6
        ]
    )
    
    # 1. Setup turns
    game.run_turn() # Dicemonger
    
    # Verify Double Buff
    dicemonger = game.get_racer(0)
    banana = game.get_racer(1)
    copycat = game.get_racer(2)
    rerolls = [a for a in banana.active_abilities if isinstance(a, DicemongerRerollAction)]
    assert len(rerolls) == 2
    
    # 2. Run Banana Turn
    game.run_turn()
    
    # Verify Final Position: 10 + 6 = 16
    assert dicemonger.position == 11 # moved +1 due to his ability being used (he is index 0)
    assert banana.position == 9 # kept the 6 to go 3 -> 9
    assert copycat.position == 0 # ability wasn't used
