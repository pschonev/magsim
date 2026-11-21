import pytest

from magsim.ai.baseline_agent import BaselineAgent
from magsim.core.types import RacerName
from magsim.engine.scenario import GameScenario, RacerConfig


def plain(idx: int, start_pos: int = 0) -> RacerConfig:
    return RacerConfig(idx, "Centaur", abilities=set(), start_pos=start_pos)


def mush(idx: int = 0, start_pos: int = 0) -> RacerConfig:
    return RacerConfig(idx, "Mush", start_pos=start_pos, agent=BaselineAgent())  # type: ignore[arg-type]


def leave_only(game: GameScenario, *names: RacerName) -> None:
    game.state.remove_racers(
        [n for n in game.state.available_racers if n not in names],
    )


def ability_names(game: GameScenario, idx: int) -> set[str]:
    return {a.name for a in game.get_racer(idx).active_abilities}


def position(game: GameScenario, idx: int) -> int | None:
    return game.get_racer(idx).position


# --- Trigger conditions ---


def test_mush_draws_nothing_while_tripped(scenario: type[GameScenario]):
    """A tripped Mush skips its roll entirely, so no low roll happens and nothing is
    drawn.
    """
    game = scenario([mush(), plain(1)], dice_rolls=[1])
    leave_only(game, "Banana")
    game.get_racer(0).tripped = True

    game.run_turn()

    assert ability_names(game, 0) == {"MushGlobsterMash"}


@pytest.mark.parametrize("roll", [3, 4, 5, 6])
def test_mush_draws_nothing_on_high_rolls(scenario: type[GameScenario], roll: int):
    """Only a 1 or 2 triggers the draw, so every high roll leaves the pile and Mush's
    powers untouched.
    """
    game = scenario([mush(), plain(1)], dice_rolls=[roll])
    leave_only(game, "Banana")

    game.run_turn()

    assert ability_names(game, 0) == {"MushGlobsterMash"}
    assert len(game.state.available_racers) == 1


def test_mush_draws_exactly_one_racer_per_low_roll(scenario: type[GameScenario]):
    """A low roll draws a single racer, not more, so the pile shrinks by one."""
    game = scenario([mush(), plain(1)], dice_rolls=[1])
    leave_only(game, "Banana", "Gloth", "Blimp")

    game.run_turn()

    assert len(game.state.available_racers) == 2


def test_mush_draws_nothing_when_the_roll_is_replaced_by_a_reroll_to_a_high_value(
    scenario: type[GameScenario],
):
    """Dicemonger re-rolls Mush's 2 into a 5. The trigger uses the final roll, so
    nothing is drawn.
    """
    game = scenario(
        [mush(), RacerConfig(1, "Dicemonger"), plain(2)],
        dice_rolls=[2, 5],
    )
    leave_only(game, "Banana")

    game.run_turn()

    assert not ability_names(game, 0) & {"BananaTrip"}
    assert len(game.state.available_racers) == 1


def test_mush_draws_when_a_reroll_lands_on_a_low_value(scenario: type[GameScenario]):
    """A high first roll re-rolled into a 1 draws, because the trigger uses the final
    roll rather than the first.
    """
    game = scenario(
        [mush(), RacerConfig(1, "Dicemonger"), plain(2)],
        dice_rolls=[5, 1],
    )
    leave_only(game, "Banana")

    game.run_turn()

    assert "BananaTrip" in ability_names(game, 0)


def test_mush_does_not_draw_when_a_drawn_legs_replaces_the_roll(
    scenario: type[GameScenario],
):
    """A drawn Legs replaces the main roll on later turns, so there is no roll for Mush
    to trigger on. This follows from the one-main-roll-trade-per-turn rule.
    """
    game = scenario([mush(), plain(1)], dice_rolls=[1, 1])
    leave_only(game, "Legs")
    game.run_turn()
    assert "LongLegs" in ability_names(game, 0)
    pile_before = len(game.state.available_racers)

    game.run_turn()
    game.run_turn()

    assert len(game.state.available_racers) == pile_before


def test_two_mush_draw_independently_on_their_own_rolls(
    scenario: type[GameScenario],
):
    """Each Mush only reacts to its own roll, so only the one that rolled a 1 draws."""
    game = scenario([mush(0), mush(1), plain(2)], dice_rolls=[1, 6, 6])
    leave_only(game, "Banana", "Gloth")

    game.run_turn()

    assert len(ability_names(game, 0)) > 1
    assert ability_names(game, 1) == {"MushGlobsterMash"}


def test_two_mush_never_draw_the_same_racer_before_a_reshuffle(
    scenario: type[GameScenario],
):
    """Both Mush draw from one shared pile, so after two draws they hold different
    racers and between them have both.
    """
    game = scenario([mush(0), mush(1), plain(2)], dice_rolls=[1])
    leave_only(game, "Banana", "Gloth")

    game.run_turns(2)

    drawn = ability_names(game, 0) | ability_names(game, 1)
    assert "BananaTrip" in drawn
    assert "GlothModifierManager" in drawn
    assert not (
        "BananaTrip" in ability_names(game, 0)
        and "BananaTrip" in ability_names(game, 1)
    )


def test_mush_never_draws_a_racer_already_in_the_game(
    scenario: type[GameScenario],
):
    """Racers in the starting lineup are not in the pile, so Mush cannot draw a
    duplicate of Banana and gets Gloth instead.
    """
    game = scenario(
        [mush(), RacerConfig(1, "Banana"), plain(2)],
        dice_rolls=[1],
    )
    leave_only(game, "Banana", "Gloth")

    game.run_turn()

    assert "BananaTrip" not in ability_names(game, 0)
    assert "GlothModifierManager" in ability_names(game, 0)


# --- Same-turn modifiers ---


@pytest.mark.parametrize(("roll", "expected"), [(1, 4), (2, 5)])
def test_mush_drawn_icarus_boost_applies_to_the_same_move(
    scenario: type[GameScenario],
    roll: int,
    expected: int,
):
    """Roll modifiers granted by the draw apply to the move of the same roll. A drawn
    Icarus adds 2 to that move.
    """
    game = scenario([mush(), plain(1)], dice_rolls=[roll])
    leave_only(game, "Icarus")

    game.run_turn()

    assert position(game, 0) == expected


def test_mush_drawn_gloth_penalty_applies_to_the_same_move_from_the_start_line(
    scenario: type[GameScenario],
):
    """A drawn Gloth subtracts 1 from the same move, so a roll of 1 leaves Mush on the
    start line instead of moving it backwards.
    """
    game = scenario([mush(), plain(1)], dice_rolls=[1])
    leave_only(game, "Gloth")

    game.run_turn()

    assert position(game, 0) == 0


def test_mush_drawn_blunderdog_triples_the_same_move_when_last(
    scenario: type[GameScenario],
):
    """Blunderdog's tripling checks the current standings, and Mush is last, so the
    roll of 2 moves 6.
    """
    game = scenario([mush(), plain(1, 3)], dice_rolls=[2])
    leave_only(game, "Blunderdog")

    game.run_turn()

    assert position(game, 0) == 6


def test_mush_drawn_blunderdog_does_not_triple_when_not_last(
    scenario: type[GameScenario],
):
    """Mush is ahead of the other racer, so a drawn Blunderdog must not triple the
    move.
    """
    game = scenario([mush(0, 5), plain(1, 0)], dice_rolls=[2])
    leave_only(game, "Blunderdog")

    game.run_turn()

    assert position(game, 0) != 11
    assert position(game, 0) is not None


def test_mush_drawn_modifier_stacks_with_a_second_draw_on_the_next_turn(
    scenario: type[GameScenario],
):
    """Modifiers from different draws coexist, so Mush ends up with both Gloth and
    Icarus.
    """
    game = scenario([mush(), plain(1)], dice_rolls=[1, 6, 1, 6])
    leave_only(game, "Icarus", "Gloth")

    game.run_turns(4)

    assert {"GlothModifierManager", "IcarusFlightRisk"} <= ability_names(game, 0)


# --- Later-turn powers ---


def test_mush_drawn_icarus_eliminates_mush_on_a_later_six(
    scenario: type[GameScenario],
):
    """A granted Icarus keeps working on later turns, so a later roll of 6 eliminates
    Mush.
    """
    game = scenario([mush(), plain(1)], dice_rolls=[1, 3, 6])
    leave_only(game, "Icarus")

    game.run_turns(3)

    assert game.get_racer(0).eliminated
    assert position(game, 0) is None


def test_mush_drawn_icarus_does_not_eliminate_on_the_turn_it_is_drawn(
    scenario: type[GameScenario],
):
    """Mush rolled 2 to draw Icarus and the draw cannot retroactively cause
    elimination, since no 6 was rolled.
    """
    game = scenario([mush(), plain(1)], dice_rolls=[2])
    leave_only(game, "Icarus")

    game.run_turn()

    assert not game.get_racer(0).eliminated


def test_mush_drawn_legs_moves_five_on_the_next_main_move(
    scenario: type[GameScenario],
):
    """A drawn Legs replaces the main roll with a move of 5 on later turns."""
    game = scenario([mush(), plain(1)], dice_rolls=[1, 3, 3])
    leave_only(game, "Legs")
    game.get_racer(1).position = 20

    game.run_turns(3)

    assert position(game, 0) == 6


def test_mush_drawn_banana_trips_a_racer_that_passes_mush(
    scenario: type[GameScenario],
):
    """Drawn Banana acts as a hazard on Mush's space, so a racer that passes Mush is
    tripped.
    """
    game = scenario([mush(0, 3), plain(1, 0)], dice_rolls=[1, 6])
    leave_only(game, "Banana")

    game.run_turns(2)

    assert game.get_racer(1).tripped


def test_mush_drawn_centaur_kicks_back_a_passed_racer(scenario: type[GameScenario]):
    """A drawn Centaur kicks a racer that Mush passes back 2 spaces during the same
    move.
    """
    game = scenario(
        [mush(0, 3), RacerConfig(1, "Skipper", abilities=set(), start_pos=4)],
        dice_rolls=[2],
    )
    leave_only(game, "Centaur")

    game.run_turn()

    assert position(game, 0) == 5
    assert position(game, 1) == 2


def test_mush_drawn_inchworm_reacts_to_other_racers_main_moves(
    scenario: type[GameScenario],
):
    """Inchworm reacts to other racers' main moves instead of replacing Mush's own, so
    Mush moves on the next turn even though it did not roll.
    """
    game = scenario([mush(), plain(1, 4)], dice_rolls=[2, 1])
    leave_only(game, "Inchworm")

    game.run_turn()
    before = position(game, 0)
    game.run_turn()

    assert position(game, 0) != before


def test_mush_drawn_copycat_copies_the_leader_on_the_next_turn(
    scenario: type[GameScenario],
):
    """A drawn Copycat is a mid-game copy ability and should still copy the leader on
    the following turn.
    """
    game = scenario(
        [mush(), RacerConfig(1, "Banana", start_pos=8)],
        dice_rolls=[1, 3],
    )
    leave_only(game, "Copycat")

    game.run_turns(2)

    assert "CopyLead" in ability_names(game, 0)


def test_mush_drawn_twin_stays_inert_with_no_one_to_copy(
    scenario: type[GameScenario],
):
    """Twin copies at setup only, so a drawn Twin never copies anything and never
    changes Mush's powers even over later turns.
    """
    game = scenario([mush(), plain(1)], dice_rolls=[1, 3, 3])
    leave_only(game, "Twin")

    game.run_turns(3)

    assert ability_names(game, 0) == {"MushGlobsterMash", "TwinCopy"}


# --- Persistence ---


def test_mush_keeps_drawn_powers_after_being_tripped(scenario: type[GameScenario]):
    """Being tripped skips a turn but must not remove granted powers."""
    game = scenario([mush(), plain(1)], dice_rolls=[1, 3])
    leave_only(game, "Banana")
    game.run_turn()

    game.get_racer(0).tripped = True
    game.run_turns(2)

    assert "BananaTrip" in ability_names(game, 0)


def test_mush_keeps_drawn_powers_when_warped(scenario: type[GameScenario]):
    """Moving Mush by a warp must not remove granted powers."""
    game = scenario([mush(), plain(1)], dice_rolls=[1])
    leave_only(game, "Banana")
    game.run_turn()

    game.engine.state.racers[0].position = 20

    assert "BananaTrip" in ability_names(game, 0)


def test_mush_drawn_ability_is_flagged_as_granted(scenario: type[GameScenario]):
    """Drawn powers carry the granted flag, which copiers use to ignore them."""
    game = scenario([mush(), plain(1)], dice_rolls=[1])
    leave_only(game, "Banana")

    game.run_turn()

    granted = {a.name for a in game.get_racer(0).active_abilities if a.granted}
    assert granted == {"BananaTrip"}


def test_mush_core_power_is_not_flagged_as_granted(scenario: type[GameScenario]):
    """Mush's own power is core, not granted, so replacing core abilities swaps it
    normally.
    """
    game = scenario([mush(), plain(1)], dice_rolls=[3])

    game.run_turn()

    assert not any(a.granted for a in game.get_racer(0).active_abilities)


# --- Race end ---


@pytest.mark.parametrize(("mush_pos", "expected_vp"), [(10, 3), (20, 0)])
def test_mush_drawn_gloth_end_bonus_depends_on_final_position(
    scenario: type[GameScenario],
    mush_pos: int,
    expected_vp: int,
):
    """A drawn Gloth's end-of-race VP bonus works for Mush too. It is awarded only when
    Mush finishes at or before the second corner.
    """
    game = scenario(
        [mush(0, mush_pos), plain(1, 28), plain(2, 28), plain(3, 5)],
        dice_rolls=[1, 3, 3, 3],
    )
    leave_only(game, "Gloth")

    game.run_turns(3)

    assert not game.engine.state.race_active
    assert game.get_racer(0).victory_points == expected_vp


# --- Copiers ---


def test_copycat_of_mush_draws_on_its_own_low_rolls(scenario: type[GameScenario]):
    """A Copycat that copied Mush draws from its own low rolls, and Mush's draws stay
    with Mush.
    """
    game = scenario(
        [mush(0, 5), RacerConfig(1, "Copycat", agent=BaselineAgent()), plain(2)],  # type: ignore[arg-type]
        dice_rolls=[6, 1],
    )
    leave_only(game, "Banana")

    game.run_turns(2)

    assert "MushGlobsterMash" in ability_names(game, 1)
    assert "BananaTrip" in ability_names(game, 1)
    assert ability_names(game, 0) == {"MushGlobsterMash"}


def test_understudy_copy_of_mush_and_mush_draw_different_racers(
    scenario: type[GameScenario],
):
    """An Understudy copying Mush draws from the same pile as Mush, so they never end
    up with the same drawn racer.
    """
    game = scenario(
        [mush(0, 5), RacerConfig(1, "Understudy"), plain(2), plain(3)],
        dice_rolls=[1],
    )
    leave_only(game, "Banana", "Gloth")

    game.run_turns(2)

    mush_draws = ability_names(game, 0) - {"MushGlobsterMash"}
    copier_draws = ability_names(game, 1) - {
        "MushGlobsterMash",
        "UnderstudyMethod",
    }
    assert mush_draws
    assert not (mush_draws & copier_draws) or not copier_draws


def test_mush_with_copycat_power_does_not_duplicate_it_on_core_swap(
    scenario: type[GameScenario],
):
    """A drawn Copycat is a granted ability. Copycat's own core swap re-submits that
    same instance, which must not be listed twice (it multiplied every trigger).
    """
    game = scenario([mush(), plain(1)], dice_rolls=[1])
    leave_only(game, "Copycat")

    game.run_turn()

    abilities = game.get_racer(0).active_abilities
    assert len({id(a) for a in abilities}) == len(abilities)
    copy_lead = [a for a in abilities if a.name == "CopyLead"]
    game.engine.replace_core_abilities(0, [*copy_lead])
    game.engine.replace_core_abilities(0, [*copy_lead])
    assert [a.name for a in game.get_racer(0).active_abilities].count("CopyLead") == 1
