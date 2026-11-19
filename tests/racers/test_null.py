from magsim.core.events import Phase, WarpCmdEvent, WarpData
from magsim.engine.elimination import eliminate_racer
from magsim.engine.flow import mark_finished
from magsim.engine.movement import push_simultaneous_warp
from magsim.engine.scenario import GameScenario, RacerConfig
from magsim.racers.kraken import KrakenPull
from magsim.racers.null import NullVoid


def cfg(idx: int, name: str, start_pos: int = 0) -> RacerConfig:
    return RacerConfig(idx, name, start_pos=start_pos)  # pyright: ignore[reportArgumentType]


def abilities(game: GameScenario, idx: int) -> set[str]:
    return {a.name for a in game.get_racer(idx).active_abilities}


def penalized(game: GameScenario, idx: int) -> bool:
    return any(m.name == "NullVoidPenalty" for m in game.get_racer(idx).modifiers)


def null_ability(game: GameScenario, idx: int = 0) -> NullVoid:
    ability = next(
        a for a in game.get_racer(idx).active_abilities if isinstance(a, NullVoid)
    )
    return ability


def warp(game: GameScenario, idx: int, tile: int) -> None:
    game.engine.push_event(
        WarpCmdEvent(
            target_racer_idx=idx,
            target_tile=tile,
            source="System",
            phase=Phase.PRE_MAIN,
            responsible_racer_idx=None,
        ),
    )


def eliminate(game: GameScenario, idx: int) -> None:
    victim = game.engine.get_active_racer(idx)
    assert victim is not None
    eliminate_racer(
        game.engine,
        victim,
        responsible_racer_idx=idx,
        source="System",
        phase=Phase.PRE_MAIN,
    )


def test_racers_ahead_are_stripped_from_the_start(scenario: type[GameScenario]):
    game = scenario([cfg(0, "Null"), cfg(1, "Centaur", 10)], dice_rolls=[1])

    assert abilities(game, 1) == set()
    assert penalized(game, 1)
    assert abilities(game, 0) == {"NullVoid"}
    assert not penalized(game, 0)


def test_racers_on_the_same_space_or_behind_keep_their_powers(
    scenario: type[GameScenario],
):
    game = scenario(
        [cfg(0, "Null", 5), cfg(1, "Centaur", 5), cfg(2, "Legs", 3)],
        dice_rolls=[1],
    )

    assert abilities(game, 1) == {"CentaurTrample"}
    assert abilities(game, 2) == {"LongLegs"}
    assert not penalized(game, 1)
    assert not penalized(game, 2)


def test_racers_ahead_roll_one_less_and_null_does_not(scenario: type[GameScenario]):
    game = scenario([cfg(0, "Null"), cfg(1, "Centaur", 10)], dice_rolls=[3, 4])

    game.run_turns(2)

    assert game.get_racer(0).position == 3
    assert game.get_racer(1).position == 13


def test_passing_null_restores_the_exact_same_powers(scenario: type[GameScenario]):
    game = scenario([cfg(0, "Null", 5), cfg(1, "Kraken", 7)], dice_rolls=[3])
    stashed = null_ability(game).stash[1][0]
    assert isinstance(stashed, KrakenPull)
    stashed.used = True
    assert abilities(game, 1) == set()

    game.run_turn()

    restored = game.get_racer(1).active_abilities
    assert len(restored) == 1
    assert restored[0] is stashed
    assert isinstance(restored[0], KrakenPull)
    assert restored[0].used
    assert not penalized(game, 1)


def test_landing_on_null_restores_powers(scenario: type[GameScenario]):
    game = scenario([cfg(0, "Null", 5), cfg(1, "Centaur", 8)], dice_rolls=[3])

    game.run_turn()

    assert game.get_racer(0).position == 8
    assert abilities(game, 1) == {"CentaurTrample"}


def test_a_racer_passing_null_is_stripped_before_its_own_power(
    scenario: type[GameScenario],
):
    """Centaur would kick Null back for passing it, but is stripped on landing first.
    Passing Null also gives no -1: Centaur still moves the full 4.
    """
    game = scenario([cfg(0, "Null", 5), cfg(1, "Centaur", 3)], dice_rolls=[1, 4])

    game.run_turns(2)

    assert game.get_racer(1).position == 7
    assert game.get_racer(0).position == 6
    assert abilities(game, 1) == set()
    assert penalized(game, 1)


def test_mover_is_stripped_before_mouth_can_eat(scenario: type[GameScenario]):
    """Mouth lands ahead of Null on Centaur's space, but has lost its power by then."""
    game = scenario(
        [cfg(0, "Null", 5), cfg(1, "Mouth", 3), cfg(2, "Centaur", 7)],
        dice_rolls=[1, 4],
    )

    game.run_turns(2)

    assert game.get_racer(1).position == 7
    assert not game.get_racer(2).eliminated
    assert not game.get_racer(1).eliminated


def test_mouth_landing_on_null_eliminates_it_and_restores_everyone(
    scenario: type[GameScenario],
):
    game = scenario(
        [cfg(0, "Null", 6), cfg(1, "Mouth", 3), cfg(2, "Centaur", 10)],
        dice_rolls=[1, 4],
    )
    assert abilities(game, 2) == set()

    game.run_turn()
    game.run_turn()

    assert game.get_racer(0).eliminated
    assert abilities(game, 2) == {"CentaurTrample"}
    assert not penalized(game, 2)


def test_finished_racer_is_dropped_from_the_stash(scenario: type[GameScenario]):
    game = scenario(
        [cfg(0, "Null"), cfg(1, "Centaur", 29), cfg(2, "Legs", 20)],
        dice_rolls=[1, 2, 1, 1],
    )
    stash = null_ability(game).stash
    assert 1 in stash

    game.run_turns(4)

    assert game.get_racer(1).finished
    assert 1 not in stash
    assert abilities(game, 1) == set()


def test_eliminated_racer_is_dropped_from_the_stash(scenario: type[GameScenario]):
    game = scenario(
        [cfg(0, "Null"), cfg(1, "Centaur", 10), cfg(2, "Legs", 20)],
        dice_rolls=[1],
    )
    stash = null_ability(game).stash
    eliminate(game, 1)

    game.run_turn()

    assert 1 not in stash
    assert game.get_racer(1).eliminated


def test_null_eliminated_restores_everyone(scenario: type[GameScenario]):
    game = scenario(
        [cfg(0, "Null"), cfg(1, "Centaur", 10), cfg(2, "Legs", 20)],
        dice_rolls=[1],
    )

    eliminate(game, 0)

    assert abilities(game, 1) == {"CentaurTrample"}
    assert abilities(game, 2) == {"LongLegs"}
    assert not penalized(game, 1)
    assert not penalized(game, 2)


def test_null_finished_restores_everyone(scenario: type[GameScenario]):
    game = scenario(
        [cfg(0, "Null"), cfg(1, "Centaur", 10), cfg(2, "Legs", 20)],
        dice_rolls=[1],
    )

    mark_finished(game.engine, game.get_racer(0), rank=1)

    assert abilities(game, 1) == {"CentaurTrample"}
    assert abilities(game, 2) == {"LongLegs"}
    assert not penalized(game, 1)


def test_tripped_racer_ahead_is_stripped_and_recovers_without_powers(
    scenario: type[GameScenario],
):
    game = scenario([cfg(0, "Null"), cfg(1, "Centaur", 10)], dice_rolls=[1, 4])
    game.engine.get_racer(1).tripped = True

    game.run_turns(3)

    assert not game.get_racer(1).tripped
    assert abilities(game, 1) == set()


def test_warping_null_past_a_racer_restores_it(scenario: type[GameScenario]):
    game = scenario([cfg(0, "Null"), cfg(1, "Centaur", 5)], dice_rolls=[1])
    assert abilities(game, 1) == set()
    warp(game, 0, 10)

    game.run_turn()

    assert abilities(game, 1) == {"CentaurTrample"}


def test_warping_ahead_of_null_strips_the_racer(scenario: type[GameScenario]):
    game = scenario([cfg(0, "Null", 5), cfg(1, "Centaur", 3)], dice_rolls=[1])
    assert abilities(game, 1) == {"CentaurTrample"}
    warp(game, 1, 9)

    game.run_turn()

    assert abilities(game, 1) == set()
    assert penalized(game, 1)


def test_simultaneous_warp_ahead_strips_every_warper(scenario: type[GameScenario]):
    game = scenario(
        [cfg(0, "Null", 5), cfg(1, "Centaur", 3), cfg(2, "Legs", 4)],
        dice_rolls=[1],
    )
    push_simultaneous_warp(
        game.engine,
        [
            WarpData(warping_racer_idx=1, target_tile=9),
            WarpData(warping_racer_idx=2, target_tile=10),
        ],
        Phase.PRE_MAIN,
        source="System",
        responsible_racer_idx=None,
        emit_ability_triggered="never",
    )

    game.run_turn()

    assert abilities(game, 1) == set()
    assert abilities(game, 2) == set()


def test_second_null_is_stripped_and_returns_when_the_first_is_gone(
    scenario: type[GameScenario],
):
    game = scenario(
        [cfg(0, "Null"), cfg(1, "Null", 5), cfg(2, "Centaur", 10)],
        dice_rolls=[1],
    )
    assert abilities(game, 1) == set()
    assert abilities(game, 2) == set()

    eliminate(game, 0)

    assert abilities(game, 1) == {"NullVoid"}
    assert abilities(game, 2) == set()


def test_stripped_hog_knight_keeps_its_hog_bonus(scenario: type[GameScenario]):
    """Roll 1 + hog 2 - Null 1 = 2."""
    game = scenario(
        [cfg(0, "Null"), cfg(1, "HogKnight", 3), cfg(2, "Centaur", 20)],
        dice_rolls=[1, 1],
    )
    assert abilities(game, 1) == set()

    game.run_turns(2)

    assert game.get_racer(1).position == 5


def test_stripped_huge_baby_removes_its_blocker_and_gets_it_back(
    scenario: type[GameScenario],
):
    game = scenario([cfg(0, "Null"), cfg(1, "HugeBaby", 5)], dice_rolls=[6])

    def blocked() -> bool:
        return any(
            m.name == "HugeBabyBlocker"
            for m in game.state.board.dynamic_modifiers.get(5, [])
        )

    assert not blocked()

    game.run_turn()

    assert game.get_racer(0).position == 6
    assert abilities(game, 1) == {"HugeBabyPush"}
    assert blocked()

