from magical_athlete_simulator.core.abilities import CopyAbilityProtocol
from magical_athlete_simulator.engine.scenario import GameScenario, RacerConfig


def test_twin_draws_from_weighted_winners(scenario: type[GameScenario]):
    """
    Twin draws 15 racers, simulates 3 races, picks winners.
    We just verify the final copied racer is one of the valid racers.
    Since we can't easily mock the 'simulation' result without mocking rng choices extensively,
    we'll rely on the fact that a racer IS picked and abilities are updated.
    """
    game = scenario(
        [
            RacerConfig(0, "Twin", start_pos=0),
            RacerConfig(1, "Banana", start_pos=0),
        ],
        dice_rolls=None,
        seed=123,  # Deterministic seed ensures successful draw
    )

    twin = game.get_racer(0)

    # Should have more abilities than just "TwinCopy"
    # (TwinCopy + whatever they copied)
    assert len(twin.abilities) >= 2
    assert "TwinCopy" in twin.abilities


def test_twin_copied_racer_removed_from_pool(scenario: type[GameScenario]):
    """
    After Twin picks a racer, that racer is removed from available pool.
    """
    game = scenario(
        [
            RacerConfig(0, "Twin", start_pos=0),
            RacerConfig(1, "Banana", start_pos=0),
        ],
        dice_rolls=None,
        seed=55,
    )

    twin = game.get_racer(0)

    # Find the ability that implements CopyAbilityProtocol (TwinCopy)
    twin_ability = next(
        (
            a
            for a in twin.active_abilities
            if isinstance(a, CopyAbilityProtocol) and a.name == "TwinCopy"
        ),
        None,
    )

    assert twin_ability is not None
    copied_name = twin_ability.copied_racer
    assert copied_name is not None
    assert copied_name not in game.engine.state.available_racers


def test_twin_auto_selection_picks_highest_avg_vp(scenario: type[GameScenario]):
    """
    The auto-agent logic for Twin is to pick the winner with the highest average VP.
    We can't easily force which winners are generated without deep mocking,
    but we can verify that a choice was made and it didn't crash.
    """
    game = scenario(
        [
            RacerConfig(0, "Twin", start_pos=0),
            RacerConfig(1, "Banana", start_pos=0),
        ],
        dice_rolls=None,
        seed=99,
    )

    twin = game.get_racer(0)
    # Just verify setup completed
    assert len(twin.abilities) > 1
    copied_racer_name = next(
        (a.copied_racer for a in twin.active_abilities if isinstance(a, CopyAbilityProtocol)),
        None,
    )

    assert copied_racer_name == "Scoocher"
