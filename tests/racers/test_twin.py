from magsim.core.abilities import CopyAbilityProtocol
from magsim.core.agent import SelectionDecisionContext
from magsim.core.types import RacerStat
from magsim.engine.scenario import GameScenario, RacerConfig
from magsim.racers.twin import TwinCopyAbility


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
        seed=56,
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
    Auto-agent selects the offered winner with the highest average VP.
    """
    game = scenario(
        [
            RacerConfig(0, "Twin", start_pos=0),
            RacerConfig(1, "Banana", start_pos=0),
        ],
        dice_rolls=None,
        seed=99,
    )
    ability = TwinCopyAbility()
    options = [
        RacerStat("Banana", avg_vp=1.0),
        RacerStat("Centaur", avg_vp=3.0),
        RacerStat("Mouth", avg_vp=2.0),
    ]

    picked = ability.get_auto_selection_decision(
        game.engine,
        SelectionDecisionContext(
            source=ability,
            event=None,
            game_state=game.state,
            source_racer_idx=0,
            options=options,
        ),
    )

    assert picked is not None
    assert picked.racer_name == "Centaur"
