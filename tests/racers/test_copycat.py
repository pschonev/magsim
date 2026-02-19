from magical_athlete_simulator.ai.baseline_agent import BaselineAgent
from magical_athlete_simulator.engine.scenario import GameScenario, RacerConfig
from magical_athlete_simulator.racers.copycat import AbilityCopyLead


def test_copycat_basic_ability_gain(scenario: type[GameScenario]):
    """
    Copycat copies the leader (Centaur) and uses the gained ability (Trample).
    """
    game = scenario(
        [
            RacerConfig(0, "Copycat", start_pos=5),
            RacerConfig(1, "Scoocher", start_pos=7),  # Victim
            RacerConfig(2, "Centaur", start_pos=10),
        ],
        dice_rolls=[4],  # Copycat moves 5 -> 9, passing Scoocher
    )

    game.run_turn()

    # Copycat trampling logic: 5 -> 9. Scoocher pushed back.
    assert game.get_racer(0).position == 9
    assert game.get_racer(1).position == 7


def test_copycat_deterministic_tie_break(scenario: type[GameScenario]):
    """
    When leaders are tied, Copycat copies the racer with the lower index.
    Centaur (idx 1) vs Gunk (idx 2) -> Copies Centaur.
    """
    game = scenario(
        [
            RacerConfig(0, "Copycat", start_pos=0),
            RacerConfig(1, "Centaur", start_pos=10),
            RacerConfig(2, "Gunk", start_pos=10),
        ],
        dice_rolls=[4],
    )

    game.engine.agents[0] = BaselineAgent()
    game.run_turn()

    # CentaurTrample should be present, GunkSlime should not.
    copycat_abilities = game.get_racer(0).abilities
    assert "CentaurTrample" in copycat_abilities
    assert "GunkSlime" not in copycat_abilities


def test_copycat_ability_loss_and_modifier_cleanup(scenario: type[GameScenario]):
    """
    Copycat copies HugeBaby (places blocker), then next turn copies Centaur.
    Verifies that the old HugeBaby blocker is removed upon ability loss.
    """
    game = scenario(
        [
            RacerConfig(0, "HugeBaby", start_pos=5),
            RacerConfig(1, "Copycat", start_pos=0),
            RacerConfig(2, "Centaur", start_pos=0),
        ],
        dice_rolls=[1, 4, 8, 1, 1],
    )

    game.run_turns(3)  # Baby moves, Copycat copies/places blocker, Centaur takes lead

    # Turn 4: Copycat copies Centaur, losing HugeBabyPush -> Blocker removed.
    game.run_turn()

    assert game.get_racer(1).position == 2
    
    modifiers_at_4 = game.engine.state.board.get_modifiers_at(4)
    blocker_exists = any(m.name == "HugeBabyBlocker" for m in modifiers_at_4)
    assert not blocker_exists, "Old HugeBabyBlocker should be cleaned up."


def test_copycat_copies_nothing_when_leading(scenario: type[GameScenario]):
    """
    When Copycat is in the lead, it should revert to its base state
    and lose any previously copied abilities.
    """
    game = scenario(
        [
            RacerConfig(0, "Copycat", start_pos=10),
            RacerConfig(1, "Centaur", start_pos=5),
            RacerConfig(2, "Gunk", start_pos=5),
        ],
        dice_rolls=[4],
    )
    game.run_turn()

    # Should lose GunkSlime because Copycat is leading
    current_abilities = game.get_racer(0).abilities
    assert "CopyLead" in current_abilities
    assert "GunkSlime" not in current_abilities


def test_copycat_copies_party_pull_and_triggers_scoocher(scenario: type[GameScenario]):
    """
    Copycat copies PartyAnimal, gaining PartyPull which triggers immediately.
    Scoocher observes this gained ability trigger and reacts.
    """
    game = scenario(
        [
            RacerConfig(0, "Magician", start_pos=0),
            RacerConfig(1, "Copycat", start_pos=5),
            RacerConfig(2, "Scoocher", start_pos=8),
            RacerConfig(3, "PartyAnimal", start_pos=10),
        ],
        dice_rolls=[5, 4],
    )

    game.run_turns(2)  # Magician, then Copycat

    scoocher = game.get_racer(2)
    copycat = game.get_racer(1)

    # Scoocher reacted to the copied PartyPull
    assert scoocher.position is not None
    assert scoocher.position >= 30
    assert copycat.position is not None 
    assert copycat.position >= 10
    assert "PartyPull" not in copycat.abilities
