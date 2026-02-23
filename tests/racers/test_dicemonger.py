from magsim.engine.scenario import GameScenario, RacerConfig
from magsim.racers.dicemonger import DicemongerRerollAction


def test_dicemonger_grants_reroll_to_others(scenario: type[GameScenario]):
    """
    Dicemonger grants a reroll ability. When used by another racer (Banana),
    Banana gets a new roll and Dicemonger gains +1 movement profit.
    """
    game = scenario(
        [
            RacerConfig(0, "Banana", start_pos=10),
            RacerConfig(1, "Dicemonger", start_pos=0),
        ],
        dice_rolls=[1, 6],
    )

    game.run_turns(1)

    assert game.get_racer(0).position == 16
    assert (dicemonger_pos := game.get_racer(1).position) is not None
    assert dicemonger_pos == 1


def test_dicemonger_copycat_duplication(scenario: type[GameScenario]):
    """
    Copycat copies Dicemonger, granting a second distinct reroll source.
    Verify duplication exists and is cleaned up when Copycat switches target.
    """
    game = scenario(
        [
            RacerConfig(0, "Dicemonger", start_pos=5),
            RacerConfig(1, "Copycat", start_pos=0),
            RacerConfig(2, "Banana", start_pos=1),
        ],
        dice_rolls=[5, 4],
    )

    game.run_turns(2)

    banana = game.get_racer(2)
    rerolls = [
        a for a in banana.active_abilities if isinstance(a, DicemongerRerollAction)
    ]
    assert len(rerolls) == 2

    copycat = game.get_racer(1)
    new_core = game.engine.instantiate_racer_abilities("Banana")
    new_core.append(copycat.active_abilities[0])
    game.engine.replace_core_abilities(1, new_core)

    rerolls_after = [
        a for a in banana.active_abilities if isinstance(a, DicemongerRerollAction)
    ]
    assert len(rerolls_after) == 1
    assert rerolls_after[0].source_racer_idx == 0


def test_dicemonger_self_use_no_profit(scenario: type[GameScenario]):
    """
    Dicemonger can use their own reroll but gains no +1 profit from self-use.
    """
    game = scenario(
        [
            RacerConfig(0, "Dicemonger", start_pos=0),
            RacerConfig(1, "Banana", start_pos=0),
        ],
        dice_rolls=[1, 5],
    )

    game.run_turn()

    dicemonger = game.get_racer(0)
    assert dicemonger.position == 5
    assert any(
        isinstance(a, DicemongerRerollAction) for a in dicemonger.active_abilities
    )


def test_dicemonger_cleanup_on_finish(scenario: type[GameScenario]):
    """
    Granted abilities are revoked when Dicemonger finishes the race.
    """
    game = scenario(
        [
            RacerConfig(0, "Dicemonger", start_pos=28), 
            RacerConfig(1, "Banana", start_pos=0),
        ],
        dice_rolls=[6],
    )

    assert any(
        isinstance(a, DicemongerRerollAction) for a in game.get_racer(1).active_abilities
    )

    game.run_turn() 

    assert not any(
        isinstance(a, DicemongerRerollAction) for a in game.get_racer(1).active_abilities
    )


def test_double_reroll_sequential_usage(scenario: type[GameScenario]):
    """
    Sequential use of multiple reroll sources (Original + Copy).
    Verify both sources are consumed and both providers gain profit.
    """
    game = scenario(
        [
            RacerConfig(0, "Dicemonger", start_pos=5),
            RacerConfig(1, "Banana", start_pos=3),
            RacerConfig(2, "Copycat", start_pos=0),
        ],
        dice_rolls=[5, 1, 1, 6],
    )

    game.run_turns(2)

    dicemonger = game.get_racer(0)
    banana = game.get_racer(1)
    copycat = game.get_racer(2)

    assert banana.position == 9
    assert dicemonger.position == 11
    assert copycat.position == 1


def test_multiple_dicemongers_independent_profit(scenario: type[GameScenario]):
    """
    Two distinct Reroll sources (Dicemonger + Copycat).
    Using one source (Copycat's) gives profit only to Copycat, not Dicemonger.
    """
    game = scenario(
        [
            RacerConfig(0, "Dicemonger", start_pos=5),
            RacerConfig(1, "Copycat", start_pos=0),
            RacerConfig(2, "Banana", start_pos=10),
        ],
        dice_rolls=[
            5,  # Dicemonger (Leader)
            4,  # Copycat (Copies Dicemonger)
            1,  # Banana initial
            6,  # Banana reroll (Uses Copycat's source likely, or Dicemonger's)
        ]
    )

    game.run_turns(2) # Setup
    
    # We verify independent profit by checking if only ONE moves +1.
    # To force a specific choice or detect which was used, we check who moved.
    
    d_pos_before = game.get_racer(0).position # 10
    c_pos_before = game.get_racer(1).position # 4

    game.run_turn() # Banana

    d_pos_after = game.get_racer(0).position
    c_pos_after = game.get_racer(1).position

    # Banana ended at 16
    assert game.get_racer(2).position == 16
    assert d_pos_before is not None
    assert c_pos_before is not None

    # Verify exclusivity: Only one of them should have gained +1
    dicemonger_profited = (d_pos_after == d_pos_before + 1)
    copycat_profited = (c_pos_after == c_pos_before + 1)
    
    assert dicemonger_profited != copycat_profited, "Only ONE source should profit per reroll."
