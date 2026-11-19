from magsim.engine.scenario import GameScenario, RacerConfig
from magsim.racers.le_saboteur import LeSaboteurTroisRevoir


def dummy(idx: int, pos: int = 0) -> RacerConfig:
    return RacerConfig(idx, "Centaur", abilities=set(), start_pos=pos)


def saboteur(idx: int, pos: int = 0) -> RacerConfig:
    return RacerConfig(idx, "LeSaboteur", start_pos=pos)


def test_a_rolled_3_moves_the_other_racer_backwards(scenario: type[GameScenario]):
    game = scenario([dummy(0, 10), saboteur(1)], dice_rolls=[3])

    game.run_turn()

    assert game.get_racer(0).position == 7


def test_other_rolls_move_forward_normally(scenario: type[GameScenario]):
    game = scenario([dummy(0, 10), saboteur(1)], dice_rolls=[4])

    game.run_turn()

    assert game.get_racer(0).position == 14


def test_the_saboteur_himself_is_not_reversed(scenario: type[GameScenario]):
    game = scenario([saboteur(0, 10), dummy(1)], dice_rolls=[3])

    game.run_turn()

    assert game.get_racer(0).position == 13


def test_reversal_applies_to_the_full_modified_distance(
    scenario: type[GameScenario],
):
    """Gunk's -1 is applied first, then the whole 3-1=2 goes backwards."""
    game = scenario(
        [dummy(0, 10), saboteur(1), RacerConfig(2, "Gunk", start_pos=0)],
        dice_rolls=[3],
    )

    game.run_turn()

    assert game.get_racer(0).position == 8


def test_reversal_is_applied_to_a_boosted_roll(scenario: type[GameScenario]):
    """Coach's +1 on a 3 gives 4, all moved backwards."""
    game = scenario(
        [dummy(0, 10), saboteur(1), RacerConfig(2, "Coach", start_pos=10)],
        dice_rolls=[3],
    )

    game.run_turn()

    assert game.get_racer(0).position == 6


def test_backwards_move_clamps_at_the_start(scenario: type[GameScenario]):
    game = scenario([dummy(0, 1), saboteur(1)], dice_rolls=[3])

    game.run_turn()

    assert game.get_racer(0).position == 0


def test_two_reversals_cancel_into_a_forward_move(scenario: type[GameScenario]):
    """A Blunderdog in front of the pack is not last, so he reverses too; 3 twice is forward."""
    game = scenario(
        [
            RacerConfig(0, "Blunderdog", start_pos=10),
            saboteur(1),
            dummy(2, 2),
        ],
        dice_rolls=[3],
    )

    game.run_turn()

    assert game.get_racer(0).position == 13


def test_two_saboteurs_cancel_each_other(scenario: type[GameScenario]):
    game = scenario(
        [dummy(0, 10), saboteur(1), saboteur(2)],
        dice_rolls=[3],
    )

    game.run_turn()

    assert game.get_racer(0).position == 13


def test_a_granted_saboteur_reverses_too(scenario: type[GameScenario]):
    game = scenario([dummy(0, 10), dummy(1)], dice_rolls=[3])
    game.engine.grant_ability(1, LeSaboteurTroisRevoir())

    game.run_turn()

    assert game.get_racer(0).position == 7


def test_reversal_stops_when_the_saboteur_loses_the_ability(
    scenario: type[GameScenario],
):
    """The aura is removed from everyone when the ability is lost."""
    game = scenario([dummy(0, 10), dummy(1)], dice_rolls=[3])
    ability = LeSaboteurTroisRevoir()
    game.engine.grant_ability(1, ability)
    game.engine.get_racer(1).active_abilities.remove(ability)
    ability.on_loss(game.engine, 1)

    game.run_turn()

    assert game.get_racer(0).position == 13


def test_a_reversed_move_passes_banana_backwards_and_trips(
    scenario: type[GameScenario],
):
    game = scenario(
        [dummy(0, 10), saboteur(1), RacerConfig(2, "Banana", start_pos=8)],
        dice_rolls=[3],
    )

    game.run_turn()

    racer = game.get_racer(0)
    assert racer.position == 7
    assert racer.tripped is True


def test_sabotage_triggers_scoocher(scenario: type[GameScenario]):
    """Scoocher reacts to the Saboteur's ability trigger by moving 1."""
    game = scenario(
        [dummy(0, 10), saboteur(1), RacerConfig(2, "Scoocher", start_pos=0)],
        dice_rolls=[3],
    )

    game.run_turn()

    assert game.get_racer(2).position == 1


def test_no_trigger_when_no_3_is_rolled(scenario: type[GameScenario]):
    game = scenario(
        [dummy(0, 10), saboteur(1), RacerConfig(2, "Scoocher", start_pos=0)],
        dice_rolls=[5],
    )

    game.run_turn()

    assert game.get_racer(2).position == 0


def test_mr_dice_guy_without_a_3_moves_forward(scenario: type[GameScenario]):
    game = scenario(
        [RacerConfig(0, "MrDiceGuy", start_pos=10), saboteur(1)],
        dice_rolls=[4, 5, 5, 1, 2, 6],
    )

    game.run_turn()

    assert game.get_racer(0).position == 15
