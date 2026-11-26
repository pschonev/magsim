"""Mush keeps his own ability while holding other powers; real Copycat is unaffected."""

import pytest

from magsim.core.state import GameRules
from magsim.core.types import RacerName
from magsim.engine.board import BOARD_DEFINITIONS
from magsim.engine.game_engine import GameEngine
from magsim.engine.scenario import GameScenario, RacerConfig

SEEDS = [0, 1, 2]
TURNS = 6
MIN_TURNS = 2
MUSH_IDX = 0


def build_engine(first: RacerName, seed: int) -> GameEngine:
    scenario = GameScenario(
        racers_config=[
            RacerConfig(0, first),
            RacerConfig(1, "Banana"),
            RacerConfig(2, "Hare"),
        ],
        seed=seed,
        board=BOARD_DEFINITIONS["Standard"](),
        rules=GameRules.for_play({}),
    )
    return scenario.engine


def ability_names(engine: GameEngine, idx: int) -> set[str]:
    return {a.name for a in engine.get_racer(idx).active_abilities}


def grant_persistently(engine: GameEngine, idx: int, racer_name: RacerName) -> None:
    for ability in engine.instantiate_racer_abilities(racer_name):
        engine.grant_ability(idx, ability, persistent=True)


def play_turns(engine: GameEngine) -> None:
    played = 0
    for _ in range(TURNS):
        if not engine.state.race_active:
            break
        engine.run_turn()
        engine.advance_turn()
        played += 1
    assert played >= MIN_TURNS, f"race ended after {played} turns"


@pytest.mark.parametrize("seed", SEEDS)
def test_mush_keeps_own_power_after_gaining_copycat(seed: int) -> None:
    engine = build_engine("Mush", seed)
    grant_persistently(engine, MUSH_IDX, "Copycat")
    assert {"CopyLead", "MushGlobsterMash"} <= ability_names(engine, MUSH_IDX)

    play_turns(engine)

    assert "MushGlobsterMash" in ability_names(engine, MUSH_IDX)


@pytest.mark.parametrize("seed", SEEDS)
def test_mush_keeps_granted_and_own_powers_with_copycat(seed: int) -> None:
    engine = build_engine("Mush", seed)
    grant_persistently(engine, MUSH_IDX, "Banana")
    grant_persistently(engine, MUSH_IDX, "Copycat")
    assert {"BananaTrip", "CopyLead", "MushGlobsterMash"} <= ability_names(
        engine,
        MUSH_IDX,
    )

    play_turns(engine)

    names = ability_names(engine, MUSH_IDX)
    assert "BananaTrip" in names
    assert "MushGlobsterMash" in names


@pytest.mark.parametrize("seed", SEEDS)
def test_real_copycat_keeps_copylead_and_never_gains_mush_power(seed: int) -> None:
    engine = build_engine("Copycat", seed)
    assert "CopyLead" in ability_names(engine, MUSH_IDX)

    play_turns(engine)

    names = ability_names(engine, MUSH_IDX)
    assert "CopyLead" in names
    assert "MushGlobsterMash" not in names
