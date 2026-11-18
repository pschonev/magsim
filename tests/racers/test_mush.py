from magsim.core.types import RacerName
from magsim.engine.scenario import GameScenario, RacerConfig


def plain(idx: int, start_pos: int = 0) -> RacerConfig:
    return RacerConfig(idx, "Centaur", abilities=set(), start_pos=start_pos)


def leave_only(game: GameScenario, *names: RacerName) -> None:
    game.state.remove_racers(
        [n for n in game.state.available_racers if n not in names],
    )


def ability_names(game: GameScenario, idx: int) -> set[str]:
    return {a.name for a in game.get_racer(idx).active_abilities}


def test_mush_gains_drawn_power_on_roll_of_one(scenario: type[GameScenario]):
    game = scenario([RacerConfig(0, "Mush"), plain(1)], dice_rolls=[1])
    leave_only(game, "Banana")

    game.run_turn()

    assert ability_names(game, 0) == {"MushGlobsterMash", "BananaTrip"}


def test_mush_gains_drawn_power_on_roll_of_two(scenario: type[GameScenario]):
    game = scenario([RacerConfig(0, "Mush"), plain(1)], dice_rolls=[2])
    leave_only(game, "Banana")

    game.run_turn()

    assert ability_names(game, 0) == {"MushGlobsterMash", "BananaTrip"}


def test_mush_gains_nothing_on_roll_of_three(scenario: type[GameScenario]):
    game = scenario([RacerConfig(0, "Mush"), plain(1)], dice_rolls=[3])
    leave_only(game, "Banana")

    game.run_turn()

    assert ability_names(game, 0) == {"MushGlobsterMash"}


def test_mush_ignores_other_racers_low_rolls(scenario: type[GameScenario]):
    """Mush's power only reacts to its own roll, so another racer rolling a 1 draws
    nothing.
    """
    game = scenario([plain(0), RacerConfig(1, "Mush")], dice_rolls=[1, 6])
    leave_only(game, "Banana")

    game.run_turn()

    assert ability_names(game, 1) == {"MushGlobsterMash"}


def test_mush_power_is_active_before_the_main_move(scenario: type[GameScenario]):
    """The drawn power must be live when the same roll resolves, so a drawn Gloth
    already cuts this move to 1 (Mush rolled 2).
    """
    game = scenario([RacerConfig(0, "Mush"), plain(1)], dice_rolls=[2])
    leave_only(game, "Gloth")

    game.run_turn()

    assert game.get_racer(0).position == 1


def test_mush_powers_stack_over_repeated_low_rolls(scenario: type[GameScenario]):
    """Each low roll adds another power without removing earlier ones."""
    game = scenario([RacerConfig(0, "Mush"), plain(1)], dice_rolls=[1])
    leave_only(game, "Banana", "Gloth")

    game.run_turns(3)

    assert ability_names(game, 0) == {
        "MushGlobsterMash",
        "BananaTrip",
        "GlothModifierManager",
        "GlothRaceEndBonus",
    }


def test_mush_granted_power_survives_core_replacement(
    scenario: type[GameScenario],
):
    """Replacing a racer's core abilities (as copiers do) must not strip drawn powers,
    which are marked as granted.
    """
    game = scenario([RacerConfig(0, "Mush"), plain(1)], dice_rolls=[1])
    leave_only(game, "Banana")
    game.run_turn()

    game.engine.replace_core_abilities(0, [])

    assert ability_names(game, 0) == {"BananaTrip"}


def test_mush_copier_does_not_inherit_granted_powers(
    scenario: type[GameScenario],
):
    """A Copycat copying Mush gets only Mush's core power, not the powers Mush drew.
    Those belong to Mush alone.
    """
    game = scenario(
        [RacerConfig(0, "Mush"), RacerConfig(1, "Copycat"), plain(2)],
        dice_rolls=[1],
    )
    leave_only(game, "Banana")

    game.run_turn()

    assert ability_names(game, 1) == {"CopyLead", "MushGlobsterMash"}


def test_mush_reshuffles_when_pile_is_empty(scenario: type[GameScenario]):
    """With an empty racer pile Mush still draws, because the pile reshuffles instead
    of failing.
    """
    game = scenario([RacerConfig(0, "Mush"), plain(1)], dice_rolls=[1])
    game.state.draw_racers(len(game.state.available_racers), rng=game.engine.rng)

    game.run_turn()

    assert len(ability_names(game, 0)) > 1


def test_mush_setup_power_is_granted_but_inert(scenario: type[GameScenario]):
    """Twin's setup ability is granted but never ran its setup, so it copies nobody.
    Checks setup-phase powers do not crash or act when drawn mid-race.
    """
    game = scenario([RacerConfig(0, "Mush"), plain(1)], dice_rolls=[1])
    leave_only(game, "Twin")

    game.run_turn()

    twin_copy = next(
        a for a in game.get_racer(0).active_abilities if a.name == "TwinCopy"
    )
    assert twin_copy.copied_racer is None
    assert ability_names(game, 0) == {"MushGlobsterMash", "TwinCopy"}


def test_mush_drawn_racer_is_not_drawn_again_before_reshuffle(
    scenario: type[GameScenario],
):
    """Drawn racers leave the pile, so three draws from a pile of two empty it instead
    of repeating a racer.
    """
    game = scenario([RacerConfig(0, "Mush"), plain(1)], dice_rolls=[1])
    leave_only(game, "Banana", "Gloth")

    game.run_turns(3)

    assert len(game.state.available_racers) == 0
