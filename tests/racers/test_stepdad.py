from magsim.core.events import Phase
from magsim.engine.elimination import eliminate_racer
from magsim.engine.flow import mark_finished
from magsim.engine.scenario import GameScenario, RacerConfig
from magsim.racers.stepdad import StepdadStepUp


def cfg(idx: int, name: str, start_pos: int = 0) -> RacerConfig:
    return RacerConfig(idx, name, start_pos=start_pos)  # pyright: ignore[reportArgumentType]


def boosted(game: GameScenario) -> set[int]:
    return {
        racer.idx
        for racer in game.engine.state.racers
        if any(m.name == "StepdadBoost" for m in racer.modifiers)
    }


def stepkid(game: GameScenario, idx: int = 0) -> int | None:
    ability = next(
        a for a in game.get_racer(idx).active_abilities if isinstance(a, StepdadStepUp)
    )
    return ability.stepkid_idx


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


def finish(game: GameScenario, idx: int, rank: int) -> None:
    racer = game.engine.get_active_racer(idx)
    assert racer is not None
    mark_finished(game.engine, racer, rank)


def test_stepkid_is_the_next_racer_and_only_it_is_boosted(
    scenario: type[GameScenario],
):
    game = scenario([cfg(0, "Stepdad"), cfg(1, "Stickler"), cfg(2, "Banana")], [3, 3, 3])

    assert stepkid(game) == 1
    assert boosted(game) == {1}

    game.run_turns(3)

    assert game.get_racer(1).position == 3 + 2
    assert game.get_racer(2).position == 3
    assert game.get_racer(0).position == 3


def test_stepkid_wraps_around_to_the_first_racer(scenario: type[GameScenario]):
    game = scenario([cfg(0, "Banana"), cfg(1, "Legs"), cfg(2, "Stepdad")], [3])

    assert stepkid(game, 2) == 0
    assert boosted(game) == {0}


def test_stepkid_skips_inactive_racers(scenario: type[GameScenario]):
    game = scenario(
        [cfg(0, "Stepdad"), cfg(1, "Legs"), cfg(2, "Banana"), cfg(3, "Coach")],
        [3],
    )
    eliminate(game, 1)
    game.run_turn()

    assert stepkid(game) == 2
    assert boosted(game) == {2}


def test_stepkid_is_retargeted_when_eliminated(scenario: type[GameScenario]):
    game = scenario([cfg(0, "Stepdad"), cfg(1, "Legs"), cfg(2, "Banana")], [3])

    eliminate(game, 1)
    game.run_turn()

    assert stepkid(game) == 2
    assert boosted(game) == {2}


def test_stepdad_gains_vp_when_stepkid_finishes_first(scenario: type[GameScenario]):
    game = scenario([cfg(0, "Stepdad"), cfg(1, "Legs"), cfg(2, "Banana")], [3])
    before = game.get_racer(0).victory_points

    finish(game, 1, 1)
    game.run_turn()

    assert game.get_racer(0).victory_points == before + 3


def test_stepdad_gains_nothing_when_stepkid_finishes_second(
    scenario: type[GameScenario],
):
    game = scenario([cfg(0, "Stepdad"), cfg(1, "Legs"), cfg(2, "Banana")], [3])
    before = game.get_racer(0).victory_points

    finish(game, 1, 2)
    game.run_turn()

    assert game.get_racer(0).victory_points == before
    assert stepkid(game) == 1


def test_boost_is_removed_when_stepdad_is_eliminated(scenario: type[GameScenario]):
    game = scenario([cfg(0, "Stepdad"), cfg(1, "Legs"), cfg(2, "Banana")], [3])

    eliminate(game, 0)

    assert boosted(game) == set()
