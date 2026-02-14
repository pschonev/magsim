from typing import cast
from magical_athlete_simulator.engine.scenario import GameScenario, RacerConfig
from magical_athlete_simulator.racers.copycat import AbilityCopyLead


def test_copycat_basic_ability_gain(scenario: type[GameScenario]):
    """
    Scenario: Copycat is behind a single leader (Centaur).
    Verify: Copycat gains Trample and uses it on its turn.
    """
    game = scenario(
        [
            RacerConfig(0, "Copycat", start_pos=5),
            RacerConfig(1, "Scoocher", start_pos=7),  # Victim
            RacerConfig(2, "Centaur", start_pos=10),
        ],
        dice_rolls=[4],  # Copycat moves 5 -> 9, passing Scoocher
    )

    game.run_turn()  # Copycat's turn

    # Verify Copycat moved and trampled Scoocher
    assert game.get_racer(0).position == 9
    assert (
        game.get_racer(1).position == 7
    )  # Scoocer first moved +1, then Trampled from 8 -> 6, then +1 again


def test_copycat_deterministic_tie_break(scenario: type[GameScenario]):
    """
    Scenario: Centaur (idx 1) and Gunk (idx 2) are tied for the lead.
    Verify: Copycat copies Centaur because he has the lower index.
    """
    game = scenario(
        [
            RacerConfig(0, "Copycat", start_pos=0),
            RacerConfig(1, "Centaur", start_pos=10),
            RacerConfig(2, "Gunk", start_pos=10),
        ],
        dice_rolls=[4],  # Copycat rolls 4
    )

    game.run_turn()  # Copycat's turn

    # Gunk's Slime would reduce the roll to 3. Centaur's Trample does nothing to the roll.
    # If Copycat copies Centaur, it moves 4. If it copies Gunk, it moves 4.
    # The proof is in the abilities set.
    copycat_abilities = game.get_racer(0).abilities
    assert "CentaurTrample" in copycat_abilities
    assert "GunkSlime" not in copycat_abilities


def test_copycat_ability_loss_and_modifier_cleanup(scenario: type[GameScenario]):
    """
    Scenario: Copycat copies HugeBaby, placing a blocker. Next turn, a new leader appears.
    Verify: Copycat loses the HugeBabyPush ability AND the blocker is removed from the board.
    """
    game = scenario(
        [
            RacerConfig(0, "HugeBaby", start_pos=5),
            RacerConfig(1, "Copycat", start_pos=0),
            RacerConfig(2, "Centaur", start_pos=0),  # Will take the lead
        ],
        dice_rolls=[
            1,  # Turn 1 (Baby): 5 -> 6
            4,  # Turn 2 (Copycat): Copies Baby, moves 0 -> 4. Places blocker at 4.
            8,  # Turn 3 (Centaur): Moves 0 -> 8, becoming the new leader.
            1,  # Turn 4 (Copycat): Copies Centaur now. Should clean up old blocker.
            1,  # Turn 5 (Baby): Moves to test if the old blocker is gone.
        ],
    )

    # Turns 1-3: Setup the scenario
    game.run_turn()  # Baby moves
    game.run_turn()  # Copycat copies Baby and moves, places blocker at 4
    game.run_turn()  # Centaur takes the lead

    # Turn 4: Copycat's turn. It should now copy Centaur and lose HugeBabyPush.
    # The on_loss hook for HugeBabyPush should unregister the blocker at tile 4.
    game.run_turn()

    # We can verify by checking the board state directly.
    assert game.get_racer(1).position == 2
    blocker_found = any(
        mod.name == "HugeBabyBlocker"
        for mod in game.engine.state.board.get_modifiers_at(4)
    )
    assert not blocker_found, "Copycat's old HugeBabyBlocker was not cleaned up!"


def test_copycat_copies_nothing_when_leading(scenario: type[GameScenario]):
    """
    Scenario: Copycat is in the lead.
    Verify: It reverts to base Copycat ability (losing previous copy).
    """
    game = scenario(
        [
            RacerConfig(0, "Copycat", start_pos=10),
            RacerConfig(1, "Centaur", start_pos=5),
            RacerConfig(2, "Gunk", start_pos=11),
        ],
        dice_rolls=[4],
    )
    
    initial_copycat_identity = game.engine.instantiate_racer_abilities("Copycat") # [CopycatAbility]
    previous_copy = game.engine.instantiate_racer_abilities("Gunk") # [GunkSlime]
    
    # Combine them (Copycat + Gunk)
    game.engine.replace_core_abilities(0, initial_copycat_identity + previous_copy)
    next(a for a in game.get_racer(0).active_abilities if isinstance(a, AbilityCopyLead)).current_copied_racer = game.engine.get_racer(2)
    # Verify initial state
    assert "GunkSlime" in game.get_racer(0).abilities

    # 2. Run Turn
    game.run_turn()  # Copycat's turn. He is leading.

    # 3. Verify Logic
    # Copycat logic says: "If leading, lose copied abilities."
    # So GunkSlime should be GONE. Only CopycatAbility remains.
    
    current_abilities = game.get_racer(0).abilities
    assert "CopyLead" in current_abilities # Base ability
    assert "GunkSlime" not in current_abilities   # Lost because leading
    assert "CentaurTrample" not in current_abilities # Not copied



def test_copycat_copies_party_pull_and_triggers_scoocher(scenario: type[GameScenario]):
    """
    Scenario: Copycat copies PartyAnimal's PartyPull and uses it in the same turn.
    Verify: Scoocher sees the dynamically gained PartyPull ability fire and reacts.
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
    scoocher = game.get_racer(2)
    copycat = game.get_racer(1)

    # Advance to Copycat's turn
    game.run_turn()
    assert "ScoochStep" not in copycat.abilities, "Race has ended, Copycat lost all his abilities"

    game.run_turn()

    assert scoocher.position >= 30, (
        "Scoocher should have gotten into loop with Copycat and won."
    )
    assert copycat.position >= 10, "Copycat should have gotten into loop with Scoocher and come second."
    assert "PartyPull" not in copycat.abilities, "Race has ended, Copycat lost all his abilities"
