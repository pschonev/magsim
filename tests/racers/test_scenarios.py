from collections.abc import Callable

import pytest

from magsim.ai.baseline_agent import BaselineAgent
from magsim.engine.scenario import GameScenario, RacerConfig

MIN_RACERS = 4
MAX_RACERS = 6


@pytest.fixture(name="scenario")
def scenario_with_racer_limits(
    scenario: Callable[..., GameScenario],
) -> Callable[..., GameScenario]:
    def build(
        racers: list[RacerConfig], *args: object, **kwargs: object
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
    game = scenario(
        [r(0, "Tail"), r(1, "Banana", 6), r(2, "Centaur", 10), r(3, "Coach", 15)],
        dice_rolls=[2],
    )

    game.run_turn()

    assert positions(game) == [7, 6, 10, 15]
    assert tripped(game) == {0}


def test_tail_landing_on_hotel_without_vp_is_tripped(scenario: type[GameScenario]):
    game = scenario(
        [r(0, "Tail"), r(1, "Hotel", 8), r(2, "Hare", 12), r(3, "Duelist", 15)],
        dice_rolls=[1],
    )

    game.run_turn()

    assert positions(game) == [8, 8, 12, 15]
    assert tripped(game) == {0}


def test_tail_landing_on_hotel_with_vp_pays_the_toll(scenario: type[GameScenario]):
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
    game = scenario(
        [r(0, "Diva"), r(1, "Centaur", 5), r(2, "Banana", 8), r(3, "Gloth", 6)],
        dice_rolls=[1],
    )

    game.run_turn()

    assert positions(game) == [9, 5, 0, 6]


def test_diva_in_the_middle_swaps_with_last_and_banana_trips_it(
    scenario: type[GameScenario],
):
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
    game = scenario(
        [r(0, "Mole"), r(1, "Hotel", 6), r(2, "Suckerfish", 12), r(3, "Alchemist", 20)],
        dice_rolls=[1],
    )

    game.run_turn()

    assert positions(game) == [6, 6, 12, 20]
    assert tripped(game) == {0}


# --- Kraken ---


def test_kraken_pulls_banana_and_centaur_who_recover_one_after_another(
    scenario: type[GameScenario],
):
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
    game = scenario(
        [r(0, "Centaur"), r(1, "Nemesis", smart=True), r(2, "Legs"), r(3, "Mouth")],
        dice_rolls=[3, 3, 3],
    )

    game.run_turn()

    assert positions(game) == [3, 3, 0, 0]


def test_nemesis_stays_put_when_its_roll_differs(scenario: type[GameScenario]):
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
    game = scenario(
        [r(0, "TheHose"), r(1, "Centaur", 3), r(2, "Banana", 9), r(3, "Duelist", 20)],
        dice_rolls=[2, 4],
    )

    game.run_turn()

    assert positions(game) == [2, 3, 9, 20]
    assert tripped(game) == {1}


def test_hose_trips_every_racer_inside_its_reach(scenario: type[GameScenario]):
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
    game = scenario(
        [r(0, "Icarus"), r(1, "Centaur", 3), r(2, "Leaptoad", 20), r(3, "Gloth", 25)],
        dice_rolls=[6, 1],
    )

    game.run_turn()

    assert game.get_racer(0).eliminated
    assert game.engine.state.race_active


def test_icarus_is_tripped_passing_banana(scenario: type[GameScenario]):
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
    game = scenario(
        [r(0, "Streaker"), r(1, "Centaur", 2), r(2, "Lackey", 3), r(3, "Blimp", 20)],
        dice_rolls=[5],
    )

    game.run_turn()

    assert positions(game) == [5, 2, 3, 20]
    assert game.get_racer(0).victory_points == 1


def test_streaker_passing_nobody_scores_nothing(scenario: type[GameScenario]):
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
    game = scenario(
        [r(0, "Spoilsport"), r(1, "Centaur", 4), r(2, "Banana", 8), r(3, "Skipper", 9)],
        dice_rolls=[3],
    )

    game.run_turn()

    assert game.engine.state.race_active
    assert positions(game) == [3, 4, 8, 9]


# --- Gloth ---


def test_gloth_moves_one_less_and_banana_still_trips_it(scenario: type[GameScenario]):
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
