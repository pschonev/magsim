from collections.abc import Callable

import pytest

from magsim.ai.baseline_agent import BaselineAgent
from magsim.core.agent import Agent, SelectionDecisionContext, SelectionInteractive
from magsim.engine.board import BOARD_DEFINITIONS
from magsim.engine.scenario import GameScenario, RacerConfig

MIN_RACERS = 4
MAX_RACERS = 6


@pytest.fixture(name="scenario")
def scenario_with_racer_limits(
    scenario: Callable[..., GameScenario],
) -> Callable[..., GameScenario]:
    def build(
        racers: list[RacerConfig],
        *args: object,
        **kwargs: object,
    ) -> GameScenario:
        assert MIN_RACERS <= len(racers) <= MAX_RACERS, (
            f"scenario tests need {MIN_RACERS}-{MAX_RACERS} racers, got {len(racers)}"
        )
        names = [racer.name for racer in racers]
        assert len(set(names)) == len(names), f"duplicate racers: {names}"
        return scenario(racers, *args, **kwargs)

    return build


def r(idx: int, name: str, start_pos: int = 0, *, smart: bool = False) -> RacerConfig:
    agent = BaselineAgent() if smart else None
    return RacerConfig(idx, name, start_pos=start_pos, agent=agent)  # type: ignore[arg-type]


def positions(game: GameScenario) -> list[int | None]:
    return [racer.position for racer in game.engine.state.racers]


def tripped(game: GameScenario) -> set[int]:
    return {racer.idx for racer in game.engine.state.racers if racer.tripped}


# --- Overtaker ---


def test_overtaker_is_kicked_back_by_centaur_then_gains_one_for_the_racer_ahead(
    scenario: type[GameScenario],
):
    """Centaur passes Overtaker and kicks it back to the start. On its own turn
    Overtaker then gets +1 for the one racer ahead, so the bonus must use the post-
    kick position.
    """
    game = scenario(
        [r(0, "Centaur"), r(1, "Overtaker", 2), r(2, "Blimp"), r(3, "Stickler")],
        dice_rolls=[3, 4],
    )

    game.run_turn()
    assert positions(game) == [3, 0, 0, 0]

    game.run_turn()
    assert positions(game) == [3, 5, 0, 0]


def test_overtaker_bonus_counts_both_racers_ahead_and_banana_trips_it(
    scenario: type[GameScenario],
):
    """Overtaker gets +1 per racer ahead (two here), and the extra distance carries it
    past Banana, which trips it. Checks bonus counting together with a trip hazard.
    """
    game = scenario(
        [r(0, "Overtaker"), r(1, "Banana", 3), r(2, "Centaur", 6), r(3, "Legs")],
        dice_rolls=[3],
    )

    game.run_turn()

    assert positions(game) == [5, 3, 6, 0]
    assert tripped(game) == {0}


# --- Tail ---


def test_tail_warps_behind_the_next_racer_and_is_tripped_passing_banana(
    scenario: type[GameScenario],
):
    """Tail warps to the space behind the nearest racer ahead, then its roll carries it
    past Banana, which trips it. Checks the warp does not bypass hazards.
    """
    game = scenario(
        [r(0, "Tail"), r(1, "Banana", 6), r(2, "Centaur", 10), r(3, "Coach", 15)],
        dice_rolls=[2],
    )

    game.run_turn()

    assert positions(game) == [7, 6, 10, 15]
    assert tripped(game) == {0}


def test_tail_landing_on_hotel_without_vp_is_tripped(scenario: type[GameScenario]):
    """Tail warps behind Hare and its roll lands exactly on Hotel's space with no VP to
    pay the toll, so it is tripped.
    """
    game = scenario(
        [r(0, "Tail"), r(1, "Hotel", 8), r(2, "Hare", 12), r(3, "Duelist", 15)],
        dice_rolls=[1],
    )

    game.run_turn()

    assert positions(game) == [8, 8, 12, 15]
    assert tripped(game) == {0}


def test_tail_landing_on_hotel_with_vp_pays_the_toll(scenario: type[GameScenario]):
    """Same landing as the no-VP case, but Tail has 1 VP and pays it to Hotel instead
    of being tripped.
    """
    game = scenario(
        [r(0, "Tail"), r(1, "Hotel", 8), r(2, "Heckler", 12), r(3, "Cheerleader", 15)],
        dice_rolls=[1],
    )
    game.get_racer(0).victory_points = 1

    game.run_turn()

    assert tripped(game) == set()
    assert (game.get_racer(0).victory_points, game.get_racer(1).victory_points) == (
        0,
        1,
    )


# --- Kingtripper ---


def test_kingtripper_trips_the_leader_who_recovers_two_turns_later(
    scenario: type[GameScenario],
):
    """Kingtripper trips the lead racer, and the trip is cleared once that racer's next
    turn is spent recovering. Checks the tripped state lasts exactly one turn.
    """
    game = scenario(
        [
            r(0, "Centaur", 4),
            r(1, "Kingtripper", smart=True),
            r(2, "Lackey", 10),
            r(3, "Hare"),
        ],
        dice_rolls=[6, 2, 3],
    )

    game.run_turns(2)
    assert positions(game) == [10, 2, 12, 0]
    assert tripped(game) == {2}

    game.run_turn()
    assert tripped(game) == set()


def test_kingtripper_trips_leader_then_is_tripped_passing_banana(
    scenario: type[GameScenario],
):
    """Kingtripper trips the leader and then passes Banana, so two racers are tripped
    by different sources in the same round.
    """
    game = scenario(
        [
            r(0, "Kingtripper", smart=True),
            r(1, "Banana", 3),
            r(2, "Centaur", 8),
            r(3, "Leaptoad"),
        ],
        dice_rolls=[4, 2],
    )

    game.run_turns(2)

    assert positions(game) == [4, 5, 8, 0]
    assert tripped(game) == {0, 2}


# --- Diva ---


def test_diva_in_last_swaps_with_the_leader_then_moves_from_there(
    scenario: type[GameScenario],
):
    """Diva in last place swaps with the leader before rolling, so its main move starts
    from the leader's old space. The leader ends up on the start line.
    """
    game = scenario(
        [r(0, "Diva"), r(1, "Centaur", 5), r(2, "Banana", 8), r(3, "Gloth", 6)],
        dice_rolls=[1],
    )

    game.run_turn()

    assert positions(game) == [9, 5, 0, 6]


def test_diva_in_the_middle_swaps_with_last_and_banana_trips_it(
    scenario: type[GameScenario],
):
    """Diva in the middle swaps with last place (Banana), and its roll then carries it
    past Banana, now on Diva's old space. Checks the swap target choice and that
    hazards still apply afterwards.
    """
    game = scenario(
        [r(0, "Diva", 5), r(1, "Banana"), r(2, "Centaur", 8), r(3, "Hypnotist", 10)],
        dice_rolls=[6],
    )

    game.run_turn()

    assert positions(game) == [6, 5, 8, 10]
    assert tripped(game) == {0}


# --- Hopfrog ---


def test_hopfrog_landing_one_behind_banana_takes_an_extra_turn_and_is_tripped_passing(
    scenario: type[GameScenario],
):
    """Hopfrog lands one space behind Banana and gets an extra turn, whose move passes
    Banana and trips it. Checks the extra turn chains into a hazard.
    """
    game = scenario(
        [r(0, "Hopfrog"), r(1, "Banana", 3), r(2, "FlipFlop", 20), r(3, "Mouth", 25)],
        dice_rolls=[2, 3],
    )

    game.run_turns(2)

    assert positions(game) == [5, 3, 20, 25]
    assert tripped(game) == {0}


def test_hopfrog_landing_far_from_others_gets_no_extra_turn(
    scenario: type[GameScenario],
):
    """Hopfrog lands nowhere near another racer, so it gets no extra turn. Checks the
    extra turn is conditional on adjacency.
    """
    game = scenario(
        [r(0, "Hopfrog"), r(1, "Banana", 8), r(2, "BabaYaga", 20), r(3, "Copycat", 25)],
        dice_rolls=[2, 3],
    )

    game.run_turns(2)

    assert positions(game) == [2, 11, 20, 25]


# --- Mole ---


def test_mole_tunnels_six_with_nobody_nearby_and_is_tripped_passing_banana(
    scenario: type[GameScenario],
):
    """Mole's tunnel replaces its roll with a 6-space move when nobody is near, and
    passing Banana still trips it. Checks a replaced main move is still subject to
    hazards.
    """
    game = scenario(
        [r(0, "Mole"), r(1, "Banana", 3), r(2, "Centaur", 12), r(3, "Magician", 20)],
        dice_rolls=[1],
    )

    game.run_turn()

    assert positions(game) == [6, 3, 12, 20]
    assert tripped(game) == {0}


def test_mole_tunnelling_onto_hotel_without_vp_is_tripped(
    scenario: type[GameScenario],
):
    """Mole's tunnel lands exactly on Hotel without VP to pay, so it is tripped. Checks
    a replaced main move still triggers landing effects.
    """
    game = scenario(
        [
            r(0, "Mole", smart=True),
            r(1, "Hotel", 6),
            r(2, "Suckerfish", 12),
            r(3, "Alchemist", 20),
        ],
        dice_rolls=[1],
    )

    game.run_turn()

    assert positions(game) == [6, 6, 12, 20]
    assert tripped(game) == {0}


# --- Kraken ---


def test_kraken_pulls_banana_and_centaur_who_recover_one_after_another(
    scenario: type[GameScenario],
):
    """Kraken pulls three racers to its space and trips them. They recover one at a
    time over the following turns, so tripped state is tracked per racer.
    """
    game = scenario(
        [
            r(0, "Kraken", 20, smart=True),
            r(1, "Banana", 25),
            r(2, "Centaur", 2),
            r(3, "Stickler", 5),
        ],
        dice_rolls=[3, 2, 2],
    )

    game.run_turn()
    assert positions(game) == [23, 20, 20, 20]
    assert tripped(game) == {1, 2, 3}

    game.run_turn()
    assert tripped(game) == {2, 3}

    game.run_turn()
    assert tripped(game) == {3}

    game.run_turn()
    assert positions(game) == [23, 20, 20, 20]
    assert tripped(game) == set()


def test_kraken_in_last_pulls_everyone_back_to_itself(scenario: type[GameScenario]):
    """Kraken in last place pulls every racer back to its space, including those ahead.
    Checks the pull works backwards, not only for trailing racers.
    """
    game = scenario(
        [
            r(0, "Kraken", 2, smart=True),
            r(1, "Centaur", 8),
            r(2, "Inchworm", 4),
            r(3, "Skipper", 6),
        ],
        dice_rolls=[3, 2],
    )

    game.run_turn()

    assert positions(game) == [5, 2, 2, 2]
    assert tripped(game) == {1, 2, 3}


# --- Soulmate ---


def test_soulmate_warps_to_a_racer_within_five_and_moves_from_there(
    scenario: type[GameScenario],
):
    """Soulmate warps to a racer within five spaces and then moves from there. Checks
    the warp happens before the main move.
    """
    game = scenario(
        [
            r(0, "Soulmate", smart=True),
            r(1, "Centaur", 4),
            r(2, "Banana", 9),
            r(3, "Egg", 15),
        ],
        dice_rolls=[2],
    )

    game.run_turn()

    assert positions(game) == [6, 4, 9, 15]


def test_soulmate_does_not_warp_when_everyone_is_further_than_five(
    scenario: type[GameScenario],
):
    """Every racer is further than five spaces away, so Soulmate has no valid warp
    target and moves from its own space.
    """
    game = scenario(
        [
            r(0, "Soulmate", smart=True),
            r(1, "Centaur", 7),
            r(2, "Banana", 9),
            r(3, "ThirdWheel", 15),
        ],
        dice_rolls=[2],
    )

    game.run_turn()

    assert positions(game) == [2, 7, 9, 15]


# --- Critic ---


def test_critic_rerolls_a_high_roll_of_the_opponent(scenario: type[GameScenario]):
    """Critic re-rolls an opponent's roll of 4 or more when that opponent is ahead of
    it, so the opponent moves by the second roll.
    """
    game = scenario(
        [
            r(0, "Critic"),
            r(1, "Centaur", 5),
            r(2, "Legs", 20),
            r(3, "RocketScientist", 25),
        ],
        dice_rolls=[1, 5, 2],
    )

    game.run_turns(2)

    assert positions(game) == [1, 7, 20, 25]


def test_critic_keeps_a_low_roll_of_the_opponent(scenario: type[GameScenario]):
    """A roll below 4 is not re-rolled, so Critic leaves it and the opponent moves by
    the first roll.
    """
    game = scenario(
        [
            r(0, "Critic"),
            r(1, "Centaur", 5),
            r(2, "PartyAnimal", 20),
            r(3, "LovableLoser", 25),
        ],
        dice_rolls=[1, 2, 6],
    )

    game.run_turns(2)

    assert positions(game) == [1, 7, 20, 25]


# --- Hotel ---


def test_hotel_collects_a_vp_toll_from_a_guest_with_vp(scenario: type[GameScenario]):
    """A guest landing on Hotel with VP pays 1 VP to Hotel and is not tripped. Checks
    the VP transfer.
    """
    game = scenario(
        [
            r(0, "Centaur", 4),
            r(1, "Hotel", 7),
            r(2, "Genius", 20),
            r(3, "Sisyphus", 25),
        ],
        dice_rolls=[3],
    )
    game.get_racer(0).victory_points = 2

    game.run_turn()

    assert tripped(game) == set()
    assert (game.get_racer(0).victory_points, game.get_racer(1).victory_points) == (
        1,
        1,
    )


def test_hotel_trips_a_guest_without_vp(scenario: type[GameScenario]):
    """A guest landing on Hotel with no VP cannot pay the toll and is tripped."""
    game = scenario(
        [
            r(0, "Stickler", 4),
            r(1, "Hotel", 7),
            r(2, "Kraken", 20),
            r(3, "Cheerleader", 25),
        ],
        dice_rolls=[3],
    )

    game.run_turn()

    assert positions(game) == [7, 7, 20, 25]
    assert tripped(game) == {0}


def test_hotel_ignores_a_guest_who_only_passes(scenario: type[GameScenario]):
    """A guest that passes Hotel without stopping pays nothing and is not tripped.
    Hotel only affects exact landings.
    """
    game = scenario(
        [
            r(0, "Blimp", 4),
            r(1, "Hotel", 7),
            r(2, "Mastermind", 20),
            r(3, "LovableLoser", 25),
        ],
        dice_rolls=[4],
    )

    game.run_turn()

    assert tripped(game) == set()
    assert game.get_racer(1).victory_points == 0


# --- Nemesis ---


def test_nemesis_moves_when_its_roll_matches_the_opponents(
    scenario: type[GameScenario],
):
    """Nemesis rolls its own die against the opponent's roll and moves that distance
    only on a match, which happens here.
    """
    game = scenario(
        [r(0, "Centaur"), r(1, "Nemesis", smart=True), r(2, "Legs"), r(3, "Mouth")],
        dice_rolls=[3, 3, 3],
    )

    game.run_turn()

    assert positions(game) == [3, 3, 0, 0]


def test_nemesis_stays_put_when_its_roll_differs(scenario: type[GameScenario]):
    """Nemesis's own roll differs from the opponent's, so it does not move."""
    game = scenario(
        [
            r(0, "Centaur"),
            r(1, "Nemesis", smart=True),
            r(2, "Leaptoad"),
            r(3, "Hypnotist"),
        ],
        dice_rolls=[3, 2, 3],
    )

    game.run_turn()

    assert positions(game) == [3, 0, 0, 0]


# --- The Hose ---


def test_hose_trips_only_racers_inside_its_reach(scenario: type[GameScenario]):
    """The Hose rolls a reach of 4 at turn end, so only the racer within 4 spaces ahead
    is tripped. Banana and the far racer are beyond it.
    """
    game = scenario(
        [r(0, "TheHose"), r(1, "Centaur", 3), r(2, "Banana", 9), r(3, "Duelist", 20)],
        dice_rolls=[2, 4],
    )

    game.run_turn()

    assert positions(game) == [2, 3, 9, 20]
    assert tripped(game) == {1}


def test_hose_trips_every_racer_inside_its_reach(scenario: type[GameScenario]):
    """The Hose's reach of 6 covers two racers ahead of it, and both are tripped.
    Checks it is not limited to a single target.
    """
    game = scenario(
        [r(0, "TheHose"), r(1, "Centaur", 5), r(2, "Banana", 6), r(3, "Heckler", 20)],
        dice_rolls=[1, 6],
    )

    game.run_turn()

    assert tripped(game) == {1, 2}


# --- Icarus ---


def test_icarus_gains_extra_distance_on_a_normal_roll(scenario: type[GameScenario]):
    game = scenario(
        [r(0, "Icarus"), r(1, "Centaur", 3), r(2, "Cheerleader", 20), r(3, "Hare", 25)],
        dice_rolls=[2, 1],
    )

    game.run_turn()

    assert positions(game) == [5, 3, 20, 25]


def test_icarus_is_eliminated_on_a_six_and_the_race_continues(
    scenario: type[GameScenario],
):
    """Icarus is eliminated when it rolls a 6, but the race continues for the remaining
    racers.
    """
    game = scenario(
        [r(0, "Icarus"), r(1, "Centaur", 3), r(2, "Leaptoad", 20), r(3, "Gloth", 25)],
        dice_rolls=[6, 1],
    )

    game.run_turn()

    assert game.get_racer(0).eliminated
    assert game.engine.state.race_active


def test_icarus_is_tripped_passing_banana(scenario: type[GameScenario]):
    """Icarus's extra distance carries it past Banana, so it is tripped. Checks a roll
    modifier still passes through hazard checks.
    """
    game = scenario(
        [
            r(0, "Icarus"),
            r(1, "Banana", 3),
            r(2, "Hypnotist", 20),
            r(3, "FlipFlop", 25),
        ],
        dice_rolls=[1],
    )

    game.run_turn()

    assert positions(game) == [4, 3, 20, 25]
    assert tripped(game) == {0}


# --- Bite Mark ---


def test_bite_mark_eliminates_banana_when_passing_after_transforming(
    scenario: type[GameScenario],
):
    """Bite Mark transforms when it rolls a 1 or 2 and from then on eliminates any
    racer it passes (Banana here). Checks elimination removes the racer from the
    board.
    """
    game = scenario(
        [r(0, "BiteMark"), r(1, "Banana", 3), r(2, "Centaur", 9), r(3, "Stickler", 20)],
        dice_rolls=[1, 2, 2, 1, 5],
    )

    game.run_turns(5)

    assert positions(game) == [6, None, 11, 21]
    assert game.get_racer(1).eliminated


def test_bite_mark_passing_without_transforming_is_harmless(
    scenario: type[GameScenario],
):
    """Bite Mark rolls a 4, so it has not transformed yet, and passing Centaur does
    nothing.
    """
    game = scenario(
        [
            r(0, "BiteMark"),
            r(1, "Centaur", 2),
            r(2, "BabaYaga", 20),
            r(3, "Copycat", 25),
        ],
        dice_rolls=[4],
    )

    game.run_turn()

    assert positions(game) == [4, 2, 20, 25]
    assert not game.get_racer(1).eliminated


# --- Speed Demon ---


def test_speed_demon_moves_extra_equal_to_vp_and_is_not_tripped_passing_hotel(
    scenario: type[GameScenario],
):
    """Speed Demon moves extra equal to its VP and is not tripped when passing Hotel.
    Checks the bonus and that Hotel only affects exact landings.
    """
    game = scenario(
        [
            r(0, "SpeedDemon", 3),
            r(1, "Hotel", 6),
            r(2, "Magician", 20),
            r(3, "Suckerfish", 25),
        ],
        dice_rolls=[3],
    )
    game.get_racer(0).victory_points = 1

    game.run_turn()

    assert positions(game) == [7, 6, 20, 25]
    assert game.get_racer(0).victory_points == 1


def test_speed_demon_far_ahead_is_eliminated_at_turn_start(
    scenario: type[GameScenario],
):
    """Speed Demon leads by 4 or more at the start of its turn and is eliminated before
    rolling.
    """
    game = scenario(
        [
            r(0, "SpeedDemon", 10),
            r(1, "Centaur", 5),
            r(2, "Alchemist", 5),
            r(3, "Egg", 5),
        ],
        dice_rolls=[1],
    )

    game.run_turn()

    assert game.get_racer(0).eliminated


# --- Nepo Baby ---


def test_nepo_baby_starts_at_twelve_and_landing_on_banana_does_not_trip(
    scenario: type[GameScenario],
):
    """Nepo Baby starts at the first corner (tile 12). Landing on Banana's space rather
    than passing it does not trip it.
    """
    game = scenario(
        [
            r(0, "NepoBaby"),
            r(1, "Banana", 13),
            r(2, "ThirdWheel", 20),
            r(3, "Mastermind", 25),
        ],
        dice_rolls=[1, 2],
    )

    game.run_turn()

    assert positions(game) == [13, 13, 20, 25]
    assert tripped(game) == set()


def test_nepo_baby_passes_centaur_without_being_kicked(scenario: type[GameScenario]):
    """Nepo Baby starts on tile 12 and passes Centaur. Centaur only kicks racers that
    it passes itself, so Nepo Baby is not kicked.
    """
    game = scenario(
        [
            r(0, "NepoBaby"),
            r(1, "Centaur", 14),
            r(2, "RocketScientist", 20),
            r(3, "PartyAnimal", 25),
        ],
        dice_rolls=[3, 1],
    )

    game.run_turn()

    assert positions(game) == [15, 14, 20, 25]


# --- Streaker ---


def test_streaker_passing_two_racers_scores_a_single_vp(scenario: type[GameScenario]):
    """Streaker passes two racers in one move but scores only one VP. Checks the reward
    is per move, not per racer passed.
    """
    game = scenario(
        [r(0, "Streaker"), r(1, "Centaur", 2), r(2, "Lackey", 3), r(3, "Blimp", 20)],
        dice_rolls=[5],
    )

    game.run_turn()

    assert positions(game) == [5, 2, 3, 20]
    assert game.get_racer(0).victory_points == 1


def test_streaker_passing_nobody_scores_nothing(scenario: type[GameScenario]):
    """Streaker passes no one and scores no VP."""
    game = scenario(
        [
            r(0, "Streaker"),
            r(1, "Centaur", 9),
            r(2, "Genius", 20),
            r(3, "Kingtripper", 25),
        ],
        dice_rolls=[5],
    )

    game.run_turn()

    assert positions(game) == [5, 9, 20, 25]
    assert game.get_racer(0).victory_points == 0


# --- Magical Athlete ---


@pytest.mark.parametrize(
    ("ma_roll", "expected_positions", "expected_tripped"),
    [
        (1, [3, 13, 8, 12], {1}),
        (2, [6, 6, 8, 12], set()),
        (3, [3, 12, 8, 12], {3}),
        (4, [3, 10, 8, 12], {1}),
        (5, [3, 6, 8, 7], {3}),
        (6, [3, 12, 8, 14], {1, 2}),
    ],
)
def test_magical_athlete_roll_face_in_a_four_racer_race(
    scenario: type[GameScenario],
    ma_roll: int,
    expected_positions: list[int],
    expected_tripped: set[int],
):
    """Each roll face triggers a different power (1: move 7, 2: warp last place to
    itself, 3: warp to a racer, 4: move 4 and go again, 5: push the leaders back, 6:
    move 6 and trip racers passed). Each case checks positions and trips for one
    face.
    """
    game = scenario(
        [
            r(0, "Centaur", 2),
            r(1, "MagicalAthlete", 6),
            r(2, "Banana", 8),
            r(3, "Lackey", 12),
        ],
        dice_rolls=[1, ma_roll, 1],
    )

    game.run_turns(2)

    assert positions(game) == expected_positions
    assert tripped(game) == expected_tripped


# --- Blunderdog ---


def test_blunderdog_in_last_triples_its_roll_and_banana_trips_it(
    scenario: type[GameScenario],
):
    """Blunderdog in last place triples its roll and passes Banana, which trips it.
    Checks the multiplier and a hazard together.
    """
    game = scenario(
        [r(0, "Blunderdog"), r(1, "Banana", 3), r(2, "Centaur", 5), r(3, "Mole", 10)],
        dice_rolls=[2],
    )

    game.run_turn()

    assert positions(game) == [6, 3, 5, 10]
    assert tripped(game) == {0}


def test_blunderdog_not_in_last_moves_backwards_and_banana_trips_it(
    scenario: type[GameScenario],
):
    """Blunderdog not in last place moves backwards, passing Banana backwards, which
    trips it. Checks hazards apply to backward moves too.
    """
    game = scenario(
        [
            r(0, "Blunderdog", 6),
            r(1, "Centaur", 2),
            r(2, "Banana", 4),
            r(3, "Tail", 10),
        ],
        dice_rolls=[3],
    )

    game.run_turn()

    assert positions(game) == [3, 2, 4, 10]
    assert tripped(game) == {0}


# --- Spoilsport ---


def test_spoilsport_five_behind_everyone_cancels_the_race_for_three_vp(
    scenario: type[GameScenario],
):
    """Spoilsport is at least five behind every other racer, so it cancels the race for
    3 VP and nobody moves. Checks the race ends without a normal finish.
    """
    game = scenario(
        [
            r(0, "Spoilsport"),
            r(1, "Centaur", 5),
            r(2, "Banana", 8),
            r(3, "Inchworm", 9),
        ],
        dice_rolls=[3],
    )

    game.run_turn()

    assert not game.engine.state.race_active
    assert game.get_racer(0).victory_points == 3
    assert positions(game) == [0, 5, 8, 9]


def test_spoilsport_with_a_racer_four_ahead_just_runs(scenario: type[GameScenario]):
    """A racer is only four ahead of Spoilsport, which is not enough to cancel the
    race, so it just moves normally.
    """
    game = scenario(
        [r(0, "Spoilsport"), r(1, "Centaur", 4), r(2, "Banana", 8), r(3, "Skipper", 9)],
        dice_rolls=[3],
    )

    game.run_turn()

    assert game.engine.state.race_active
    assert positions(game) == [3, 4, 8, 9]


# --- Gloth ---


def test_gloth_moves_one_less_and_banana_still_trips_it(scenario: type[GameScenario]):
    """Gloth moves one space less than rolled and still passes Banana, which trips it.
    Checks the penalty does not cancel the hazard.
    """
    game = scenario(
        [r(0, "Gloth"), r(1, "Banana", 2), r(2, "Centaur", 6), r(3, "Hopfrog", 10)],
        dice_rolls=[4],
    )

    game.run_turn()

    assert positions(game) == [3, 2, 6, 10]
    assert tripped(game) == {0}


@pytest.mark.parametrize(("gloth_pos", "expected_vp"), [(15, 3), (16, 0)])
def test_gloth_race_end_bonus_depends_on_its_position(
    scenario: type[GameScenario],
    gloth_pos: int,
    expected_vp: int,
):
    """Gloth earns 3 VP only if it ends the race at or before the second corner (tile
    15). The two cases sit on either side of the threshold.
    """
    game = scenario(
        [
            r(0, "Centaur", 28),
            r(1, "Banana", 28),
            r(2, "Gloth", gloth_pos),
            r(3, "TheHose", 5),
        ],
        dice_rolls=[3, 3, 3],
    )

    game.run_turns(3)

    assert not game.engine.state.race_active
    assert game.get_racer(2).victory_points == expected_vp


# --- Mush ---


def draw_only(game: GameScenario, *names: str) -> None:
    game.state.remove_racers(
        [n for n in game.state.available_racers if n not in names],  # type: ignore[misc]
    )


def abilities(game: GameScenario, idx: int) -> set[str]:
    return {a.name for a in game.get_racer(idx).active_abilities}


def test_mush_drawn_gloth_cancels_the_low_roll_every_turn(
    scenario: type[GameScenario],
):
    """Mush rolls only 1s, so a drawn Gloth reduces each move to 0 on every turn.
    Checks a granted modifier stays active across many turns.
    """
    game = scenario(
        [r(0, "Mush", 3), r(1, "Banana", 4), r(2, "Sisyphus"), r(3, "Hopfrog", 12)],
        dice_rolls=[1, 1, 1, 5],
    )
    draw_only(game, "Gloth")

    game.run_turns(8)

    assert positions(game)[0] == 3
    assert "GlothModifierManager" in abilities(game, 0)


def test_mush_drawn_blimp_adds_one_per_racer_ahead_to_the_same_move(
    scenario: type[GameScenario],
):
    """Blimp is drawn on a low roll and its bonus applies to that same move, since
    Mush's draw happens before the move resolves. Three racers ahead add +3 to the
    roll of 2.
    """
    game = scenario(
        [r(0, "Mush"), r(1, "Coach", 3), r(2, "Scoocher", 5), r(3, "Mastermind", 8)],
        dice_rolls=[2, 3, 3, 3],
    )
    draw_only(game, "Blimp")

    game.run_turn()

    assert positions(game)[0] == 5


def test_mush_drawn_legs_moves_five_on_the_next_main_move(scenario: type[GameScenario]):
    """Legs is drawn on turn one, which moves normally, and only replaces Mush's main
    move from the next turn on. Checks a granted roll-replacer is active but not
    retroactive.
    """
    game = scenario(
        [
            r(0, "Mush", smart=True),
            r(1, "Stickler", 2),
            r(2, "Mastermind", 4),
            r(3, "Coach", 6),
            r(4, "Sisyphus", 1),
        ],
        dice_rolls=[1, 3, 3, 3, 3, 3, 3, 3, 3, 3],
    )
    draw_only(game, "Legs")

    game.run_turns(1)

    assert positions(game)[0] == 1
    game.run_turns(5)

    assert positions(game)[0] == 6
    assert "LongLegs" in abilities(game, 0)


def test_mush_drawn_icarus_eliminates_mush_on_a_later_six(
    scenario: type[GameScenario],
):
    """Icarus's elimination on a 6 is granted persistently, so a later 6 eliminates
    Mush. Checks granted risks are as real as granted bonuses.
    """
    game = scenario(
        [
            r(0, "Mush", 2),
            r(1, "Skipper", 5),
            r(2, "Hopfrog", 7),
            r(3, "Stickler", 9),
        ],
        dice_rolls=[2, 3, 3, 3, 6],
    )
    draw_only(game, "Icarus")

    game.run_turns(5)

    assert game.get_racer(0).eliminated
    assert positions(game)[0] is None


# --- Understudy ---


class PickNamed(Agent):
    def __init__(self, name: str) -> None:
        self.name = name

    def make_selection_decision[R](
        self,
        engine,
        ctx: SelectionDecisionContext[SelectionInteractive[R], R],
    ) -> R | None:
        return next(o for o in ctx.options if o.racer_name == self.name)  # pyright: ignore[reportAttributeAccessIssue]


def test_understudy_copies_banana_and_trips_the_racer_it_passes(
    scenario: type[GameScenario],
):
    """Understudy copies Banana during setup, so it then trips a racer it passes.
    Checks the copied power works from the first turn.
    """
    game = scenario(
        [
            RacerConfig(0, "Understudy", start_pos=2, agent=PickNamed("Banana")),  # type: ignore[arg-type]
            r(1, "Banana", 6),
            r(2, "Scoocher", 3),
            r(3, "Mastermind", 1),
        ],
        dice_rolls=[2, 1, 1, 1],
    )

    game.run_turn()

    assert "BananaTrip" in abilities(game, 0)
    assert positions(game)[0] == 4


def test_understudy_copying_mush_gets_a_drawn_power_on_a_low_roll(
    scenario: type[GameScenario],
):
    """Understudy copies Mush, so its own low roll draws Gloth from the pile. Checks
    the copied Mush power works for the copier, independent of the real Mush.
    """
    game = scenario(
        [
            RacerConfig(0, "Understudy", agent=PickNamed("Mush")),  # type: ignore[arg-type]
            r(1, "Mush", 5),
            r(2, "Sisyphus", 1),
            r(3, "Stickler", 2),
        ],
        dice_rolls=[1, 3, 3, 3],
    )
    draw_only(game, "Gloth")

    game.run_turn()

    assert abilities(game, 0) == {
        "UnderstudyMethod",
        "MushGlobsterMash",
        "GlothModifierManager",
        "GlothRaceEndBonus",
    }


# --- Doppelgangster ---


def test_doppelgangster_takes_banana_from_the_racer_who_would_win(
    scenario: type[GameScenario],
):
    """Banana would have won the race but dives instead, and Doppelgangster gains the
    Banana trip power. Nobody has finished, so the race continues.
    """
    game = scenario(
        [
            r(0, "Doppelgangster"),
            r(1, "Banana", 28),
            r(2, "Hotel", 3),
            r(3, "Inchworm", 5),
        ],
        dice_rolls=[1, 3, 3, 3],
    )

    game.run_turn()
    game.run_turn()

    assert game.get_racer(1).eliminated
    assert game.get_racer(1).victory_points == 0
    assert "BananaTrip" in abilities(game, 0)
    assert game.engine.state.race_active


def test_doppelgangster_dive_lets_the_next_crosser_win(scenario: type[GameScenario]):
    """After the dive is spent, Sisyphus crosses next and takes 1st place (4 VP on top
    of its 4 starting VP) while the race stays open for a second finisher.
    """
    game = scenario(
        [
            r(0, "Doppelgangster"),
            r(1, "Gunk", 28),
            r(2, "Sisyphus", 27),
            r(3, "Heckler", 10),
            r(4, "Mouth", 20),
        ],
        dice_rolls=[1, 4, 5, 1, 1],
    )

    game.run_turns(3)

    assert game.get_racer(1).eliminated
    assert game.get_racer(2).finish_position == 1
    assert game.get_racer(2).victory_points == 8
    assert game.engine.state.race_active


def test_doppelgangster_gains_legs_and_uses_it_on_the_next_turn(
    scenario: type[GameScenario],
):
    """Legs dives on its way over the line and Doppelgangster keeps the power, so its
    next turn skips the roll and moves 5.
    """
    game = scenario(
        [
            r(0, "Doppelgangster"),
            r(1, "Legs", 25),
            r(2, "Alchemist"),
            r(3, "Lackey", 8),
        ],
        dice_rolls=[1, 1, 1, 1, 1],
    )

    game.run_turns(5)

    assert game.get_racer(1).eliminated
    assert positions(game)[0] == 6


def test_doppelgangster_is_eliminated_when_it_crosses_first(
    scenario: type[GameScenario],
):
    """Doppelgangster crossing the line first is eliminated like anyone else, scoring
    nothing, while the rest of the field is untouched.
    """
    game = scenario(
        [
            r(0, "Doppelgangster", 27),
            r(1, "Magician", 5),
            r(2, "Coach", 10),
            r(3, "Kraken", 3),
            r(4, "PartyAnimal", 12),
        ],
        dice_rolls=[4, 1, 1, 1, 1],
    )

    game.run_turn()

    assert game.get_racer(0).eliminated
    assert game.get_racer(0).victory_points == 0
    assert game.get_racer(0).finish_position is None
    assert game.engine.state.race_active


# --- Party Pooper / Stunner ---


def test_party_pooper_rerolls_sixes_across_a_varied_field(
    scenario: type[GameScenario],
):
    """Pooper complains once per rerolled six on any racer's main roll, and the
    reroll is what actually moves the roller.
    """
    game = scenario(
        [
            r(0, "PartyPooper", 10),
            r(1, "Hopfrog", 0),
            r(2, "Stickler", 3),
            r(3, "Romantic", 20),
            r(4, "Tail", 5),
        ],
        dice_rolls=[1, 6, 6, 2],
    )

    game.run_turns(2)

    assert game.get_racer(0).position == 10 + 1 + 2
    assert game.get_racer(1).position == 2


def test_stunner_aura_slows_a_mixed_pack(scenario: type[GameScenario]):
    """Racers within 1 of the Stunner always roll 1, even when the dice say 6, while
    a racer further away rolls freely (Sisyphus rolls the 6 and is sent back).
    """
    game = scenario(
        [
            r(0, "Banana", 9),
            r(1, "Stickler", 11),
            r(2, "Sisyphus", 3),
            r(3, "Stunner", 10),
        ],
        dice_rolls=[6, 3, 4],
    )

    game.run_turns(4)

    assert game.get_racer(0).position == 10
    assert game.get_racer(1).position == 12
    assert game.get_racer(2).position == 0
    assert game.get_racer(3).position == 13


def test_duelist_duel_next_to_stunner_and_party_pooper(
    scenario: type[GameScenario],
):
    """A Duelist duel is made of real dice: Party Pooper rerolls a duel 6 (moving 1)
    while the Stunner is too far away to force anything.
    """
    game = scenario(
        [
            r(0, "Duelist", 5),
            r(1, "Mastermind", 5),
            r(2, "Stunner", 20),
            r(3, "PartyPooper", 25),
            r(4, "Hotel", 15),
        ],
        dice_rolls=[6, 4, 3, 1],
    )

    game.run_turn()

    assert game.get_racer(3).position == 26
    assert game.get_racer(0).position == 5 + 2 + 1


def test_hose_and_nemesis_dice_go_through_central_roll(
    scenario: type[GameScenario],
):
    """Nemesis and The Hose roll their own dice, so Party Pooper rerolls their sixes
    and he gains a move each time.
    """
    game = scenario(
        [
            r(0, "TheHose", 0),
            r(1, "Nemesis", 12),
            r(2, "PartyPooper", 20),
            r(3, "Banana", 8),
        ],
        dice_rolls=[6, 3, 1, 1, 1, 1, 1],
    )

    game.run_turn()

    assert game.get_racer(2).position == 21
    assert game.get_racer(0).position == 3


def test_mr_dice_guy_sixes_feed_lackey_and_gunk_trims_the_pick(
    scenario: type[GameScenario],
):
    """Two sixes among the six dice make Lackey move twice, Mr. Dice Guy moves the
    picked 6 minus Gunk's -1 and lands on Gunk, which pays Romantic.
    """
    game = scenario(
        [
            r(0, "MrDiceGuy", 0),
            r(1, "Lackey", 10),
            r(2, "Gunk", 5),
            r(3, "Romantic", 20),
        ],
        dice_rolls=[6, 6, 1, 2, 3, 4],
    )

    game.run_turn()

    assert game.get_racer(1).position == 14
    assert game.get_racer(0).position == 5
    assert game.get_racer(3).position == 22


def test_show_off_busts_while_inchworm_and_skipper_react_to_the_one(
    scenario: type[GameScenario],
):
    """Show-Off rolls 3, keeps going and rolls a 1 (a bust): he does not move, but the 1
    was rolled, so Inchworm moves 1 and Skipper takes the next turn.
    """
    game = scenario(
        [
            r(0, "ShowOff", 0),
            r(1, "Inchworm", 10),
            r(2, "Skipper", 15),
            r(3, "Coach", 20),
        ],
        dice_rolls=[3, 1, 4],
    )

    game.run_turns(2)

    assert game.get_racer(0).position == 0
    assert game.get_racer(1).position == 11
    assert game.get_racer(2).position == 19


def test_le_saboteur_reverses_boosted_three_over_banana_and_scoocher_follows(
    scenario: type[GameScenario],
):
    """Coach's 3 is a 4 with his own boost, Le Saboteur sends all of it backwards over
    Banana (tripping Coach), and Scoocher steps once each for the boost, the sabotage
    and the trip.
    """
    game = scenario(
        [
            r(0, "Coach", 10),
            r(1, "LeSaboteur", 15),
            r(2, "Banana", 8),
            r(3, "Scoocher", 0),
        ],
        dice_rolls=[3],
    )

    game.run_turn()

    assert game.get_racer(0).position == 6
    assert game.get_racer(0).tripped is True
    assert game.get_racer(3).position == 3


def test_penguin_tripped_by_inchworm_rolls_double_through_gunk_and_recovers(
    scenario: type[GameScenario],
):
    """Inchworm's 6 (-1 Gunk, Lackey moves 2 first) passes Penguin, who trips and then
    rolls his 3 doubled to 6, minus Gunk's 1, instead of skipping, and is up again.
    """
    game = scenario(
        [
            r(0, "Inchworm", 0),
            r(1, "Penguin", 3),
            r(2, "Lackey", 10),
            r(3, "Gunk", 20),
        ],
        dice_rolls=[6, 3],
    )

    game.run_turns(2)

    assert game.get_racer(0).position == 5
    assert game.get_racer(2).position == 12
    assert game.get_racer(1).position == 8
    assert game.get_racer(1).tripped is False


def test_hog_knight_rides_boosted_and_loses_the_hog_to_a_racer_stopping_on_him(
    scenario: type[GameScenario],
):
    """HogKnight's 2 plus the hog's +2 reaches 7. Legs (4 + 1) stops on him and takes
    the hog, leaving HogKnight with no modifiers.
    """
    game = scenario(
        [
            r(0, "HogKnight", 3),
            r(1, "Legs", 2),
            r(2, "Banana", 15),
            r(3, "Coach", 20),
        ],
        dice_rolls=[2, 4, 1, 1],
    )

    game.run_turn()
    assert game.get_racer(0).position == 7

    game.run_turns(1)
    assert game.get_racer(1).position == 7
    assert [m.name for m in game.get_racer(0).modifiers] == []
    assert [m.name for m in game.get_racer(1).modifiers] == ["HogKnightHog"]


# --- Null ---


def test_null_strips_the_pack_ahead_until_it_is_passed(scenario: type[GameScenario]):
    """Null (2 -> 7) strips Banana and Coach ahead. Centaur (3 + 5 = 8) passes Null
    with a full roll, loses its power on landing and never kicks Null back. Banana
    (3 - 1) and Coach (4 - 1) move one less and trip and boost nobody.
    """
    game = scenario(
        [r(0, "Null", 5), r(1, "Centaur", 3), r(2, "Banana", 10), r(3, "Coach", 12)],
        dice_rolls=[2, 5, 3, 4],
    )

    game.run_turns(4)

    assert positions(game) == [7, 8, 12, 15]
    assert tripped(game) == set()
    assert abilities(game, 1) == set()
    assert abilities(game, 0) == {"NullVoid"}


# --- Stepdad ---


def test_stepdad_boosts_the_next_racer_and_collects_when_it_wins(
    scenario: type[GameScenario],
):
    """Stepdad's stepkid Stickler gets +2 on its main move. Stickler finishes 1st
    from 28 (4 + 2), so Stepdad gains 3 VP on top of nothing from his own run.
    """
    game = scenario(
        [r(0, "Stepdad"), r(1, "Stickler", 28), r(2, "Banana"), r(3, "Coach")],
        dice_rolls=[1, 4, 1, 1],
    )

    game.run_turns(2)

    assert game.get_racer(1).finish_position == 1
    assert game.get_racer(0).victory_points == 3


def test_stepdad_as_last_racer_boosts_racer_zero_and_coach_stacks(
    scenario: type[GameScenario],
):
    """Stepdad is last in turn order, so racer 0 is his stepkid. Stickler rolls
    3 + 2 (Stepdad) + 1 (Coach) while Banana only gets Coach's +1.
    """
    game = scenario(
        [r(0, "Stickler"), r(1, "Banana"), r(2, "Coach"), r(3, "Stepdad")],
        dice_rolls=[3, 3, 1, 1],
    )

    game.run_turns(2)

    assert positions(game)[:2] == [3 + 2 + 1, 3 + 1]


# --- Cheatah ---


@pytest.mark.parametrize(
    ("seed", "cheatah_position"),
    [(1, 0), (0, 7)],
    ids=["guessed", "unguessed"],
)
def test_baseline_cheatah_sets_six_and_moves_only_if_it_is_not_guessed(
    scenario: type[GameScenario],
    seed: int,
    cheatah_position: int,
):
    """The baseline Cheatah always sets 6. If the guess hits, his main move is
    skipped; otherwise he moves 6 + 1 from Coach. The others move normally.
    """
    game = scenario(
        [r(0, "Cheatah", smart=True), r(1, "Stickler"), r(2, "Banana"), r(3, "Coach")],
        dice_rolls=[4, 3, 2, 1],
        seed=seed,
    )

    game.run_turns(4)

    assert positions(game) == [cheatah_position, 5, 4, 3]


# --- Re-Runner ---


def test_re_runner_gets_only_the_coach_boost_and_no_power_of_her_own(
    scenario: type[GameScenario],
):
    """Re-Runner has no powers: she only gets Coach's +1, like Coach himself."""
    game = scenario(
        [r(0, "ReRunner"), r(1, "Coach"), r(2, "Banana"), r(3, "Stickler")],
        dice_rolls=[4, 3, 2, 1],
    )

    game.run_turns(4)

    assert positions(game) == [4 + 1, 3 + 1, 2, 1]


# --- Whirly World ---


def test_whirly_world_tail_warping_onto_a_whirl_is_carried_past_banana_untripped(
    scenario: type[GameScenario],
):
    """Tail warps behind Banana onto whirl 4, which sends it to 6, beyond Banana. A
    warp does not pass, so it is not tripped, and its roll then moves it on.
    """
    game = scenario(
        [r(0, "Tail"), r(1, "Banana", 5), r(2, "Centaur", 10), r(3, "Genius", 15)],
        dice_rolls=[1],
        board=BOARD_DEFINITIONS["WhirlyWorld"](),
    )

    game.run_turn()

    assert positions(game) == [7, 5, 10, 15]
    assert tripped(game) == set()


def test_whirly_world_banana_trips_the_mover_who_still_whirls_to_the_pair(
    scenario: type[GameScenario],
):
    """Stickler passes Banana and lands on whirl 4, so it is tripped and still warps to
    6. Checks the whirl fires for a moved racer even when tripped en route.
    """
    game = scenario(
        [r(0, "Stickler", 2), r(1, "Banana", 3), r(2, "Centaur", 10), r(3, "Genius", 15)],
        dice_rolls=[2],
        board=BOARD_DEFINITIONS["WhirlyWorld"](),
    )

    game.run_turn()

    assert positions(game) == [6, 3, 10, 15]
    assert tripped(game) == {0}


def test_whirly_world_hotel_at_the_exit_tile_trips_the_whirled_racer(
    scenario: type[GameScenario],
):
    """Stickler lands on whirl 4 and exits on 6 where Hotel sits, with no VP to pay the
    toll. Checks Hotel reacts to the whirl's warp.
    """
    game = scenario(
        [r(0, "Stickler", 2), r(1, "Hotel", 6), r(2, "Centaur", 10), r(3, "Genius", 15)],
        dice_rolls=[2],
        board=BOARD_DEFINITIONS["WhirlyWorld"](),
    )

    game.run_turn()

    assert positions(game) == [6, 6, 10, 15]
    assert tripped(game) == {0}


def test_whirly_world_racer_whirls_on_consecutive_turns(scenario: type[GameScenario]):
    """Stickler whirls from 4 to 6, then next turn from 8 to 12. Checks the exit tile
    does not trap it and later whirls still fire.
    """
    game = scenario(
        [r(0, "Stickler"), r(1, "Banana", 13), r(2, "Centaur", 20), r(3, "Lackey", 25)],
        dice_rolls=[4, 1, 1, 1, 2],
        board=BOARD_DEFINITIONS["WhirlyWorld"](),
    )

    game.run_turns(1)
    assert game.get_racer(0).position == 6

    game.run_turns(4)

    assert positions(game) == [12, 14, 21, 26]
