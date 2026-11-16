from magsim.core.abilities import CopyAbilityProtocol
from magsim.core.agent import SelectionDecisionContext
from magsim.core.types import RacerStat
from magsim.engine.scenario import GameScenario, RacerConfig
from magsim.racers.egg import EggCopyAbility


def test_egg_basic_copy(scenario: type[GameScenario]):
    """
    Egg draws 3 racers in setup and picks one.
    Gains that racer's abilities permanently.
    """
    game = scenario(
        [
            RacerConfig(0, "Egg", start_pos=0),
            RacerConfig(1, "Banana", start_pos=0),
        ],
        dice_rolls=None,
        seed=42,
    )

    egg = game.get_racer(0)

    assert egg.abilities != {"EggCopy"}
    assert "EggCopy" in egg.abilities
    assert len(egg.abilities) >= 2


def test_egg_copied_racer_removed_from_pool(scenario: type[GameScenario]):
    """
    After Egg picks a racer, that racer cannot be drawn again.
    Verify the racer is removed from the available pool.
    """
    game = scenario(
        [
            RacerConfig(0, "Egg", start_pos=0),
            RacerConfig(1, "Banana", start_pos=0),
        ],
        dice_rolls=None,
        seed=40,
    )

    egg = game.get_racer(0)
    copied_racer_name = next(
        (a.copied_racer for a in egg.active_abilities if isinstance(a, CopyAbilityProtocol)),
        None,
    )

    assert copied_racer_name is not None
    assert copied_racer_name not in game.engine.state.available_racers


def test_egg_auto_selection_picks_highest_avg_vp(scenario: type[GameScenario]):
    """
    Auto-agent selects the offered racer with the highest average VP.
    """
    game = scenario(
        [
            RacerConfig(0, "Egg", start_pos=0),
            RacerConfig(1, "Banana", start_pos=0),
        ],
        dice_rolls=None,
        seed=10,
    )
    ability = EggCopyAbility()
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

