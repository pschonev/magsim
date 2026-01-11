from magical_athlete_simulator.engine.scenario import GameScenario, RacerConfig


def test_coach_applies_boost_to_group(scenario: type[GameScenario]):
    """Coach gives +1 to everyone on his space, including self."""
    game = scenario(
        [
            RacerConfig(0, "Coach", start_pos=5),
            RacerConfig(1, "Banana", start_pos=5),
        ],
        dice_rolls=[2, 3],
    )
    
    # Turn 1: Coach rolls. Both at 5 -> both get +1. Coach: 2+1=3 -> 8
    game.run_turn()
    coach = game.get_racer(0)
    assert coach.position == 8, "Coach: 2 + 1 = 3"
    
    
def test_coach_aura_updates_on_move(scenario: type[GameScenario]):
    """Coach aura updates when he moves (others lose boost)."""
    game = scenario(
        [
            RacerConfig(0, "Coach", start_pos=5),
            RacerConfig(1, "Banana", start_pos=5),
        ],
        dice_rolls=[1, 2],
    )
    
    # Turn 1: Coach rolls 1+1=2 -> moves to 7
    game.run_turns(2)
    coach = game.get_racer(0)
    banana = game.get_racer(1)
    assert coach.position == 7
    assert banana.position == 7
    

def test_coach_aura_lifecycle(scenario: type[GameScenario]):
    """CoachAura on_gain correctly applies boost to group."""
    game = scenario(
        [
            RacerConfig(0, "Coach", start_pos=5),
            RacerConfig(1, "Banana", start_pos=5),
        ],
        dice_rolls=[2],
    )
    
    # Check that CoachBoost was applied to both during on_gain
    coach = game.get_racer(0)
    banana = game.get_racer(1)
    
    assert any(m.name == "CoachBoost" for m in coach.modifiers)
    assert any(m.name == "CoachBoost" for m in banana.modifiers)

    game.run_turn()

    assert any(m.name == "CoachBoost" for m in coach.modifiers)
    assert not any(m.name == "CoachBoost" for m in banana.modifiers)
