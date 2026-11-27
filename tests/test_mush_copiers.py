"""Mush keeps his own power when he holds a copier's power; copies of Mush never keep it."""

import itertools
import random
from collections.abc import Sequence
from dataclasses import dataclass
from typing import override

import pytest

from magsim.core.agent import Agent, SelectionDecisionContext, SelectionInteractive
from magsim.core.types import RacerName, RacerStat
from magsim.engine.game_engine import GameEngine
from magsim.engine.scenario import GameScenario, RacerConfig
from magsim.racers.mush import MushGlobsterMashAbility

MUSH: RacerName = "Mush"
OWN_POWER = "MushGlobsterMash"
MUSH_IDX = 0
LEAD_POS = 8
COPYCAT_LEAD_POS = 20
COPIERS: list[RacerName] = ["Copycat", "Egg", "Twin", "Understudy"]
SETUP_COPIERS: list[RacerName] = ["Egg", "Twin", "Understudy"]
COPIER_ABILITY = {
    "Egg": "EggCopy",
    "Twin": "TwinCopy",
    "Understudy": "UnderstudyMethod",
}
# Exactly 15 racers (Twin's draw size) that neither replace nor cancel Mush's main roll.
SAFE_PILE: tuple[RacerName, ...] = (
    "BabaYaga",
    "Blimp",
    "Blunderdog",
    "Gloth",
    "Hotel",
    "Hopfrog",
    "HugeBaby",
    "Kingtripper",
    "Leaptoad",
    "LovableLoser",
    "Overtaker",
    "PartyPooper",
    "Scoocher",
    "Stepdad",
    "SpeedDemon",
)


class ScriptedRandom(random.Random):
    """Real seeded RNG with scripted dice; draws put the preferred racer first and it wins every lottery."""

    def __init__(self, rolls: Sequence[int], preferred: RacerName) -> None:
        super().__init__(0)
        self._rolls = itertools.cycle(rolls)
        self._preferred = preferred

    @override
    def randint(self, a: int, b: int) -> int:
        _ = a, b
        return next(self._rolls)

    @override
    def sample(  # type: ignore[override]
        self,
        population: Sequence[RacerName],
        k: int,
        *,
        counts: Sequence[int] | None = None,
    ) -> list[RacerName]:
        _ = counts
        if k > len(population):
            msg = "Sample larger than population"
            raise ValueError(msg)
        return sorted(population, key=lambda name: name != self._preferred)[:k]

    @override
    def choices(  # type: ignore[override]
        self,
        population: Sequence[RacerStat],
        weights: Sequence[float] | None = None,
        *,
        cum_weights: Sequence[float] | None = None,
        k: int = 1,
    ) -> list[RacerStat]:
        _ = weights, cum_weights
        preferred = [p for p in population if p.racer_name == self._preferred]
        return (preferred or list(population))[:k]


@dataclass
class PickByName(Agent):
    """Picks `target` when offered, otherwise the first option that is not Mush."""

    target: RacerName | None = None

    @override
    def make_selection_decision[R](
        self,
        engine: GameEngine,
        ctx: SelectionDecisionContext[SelectionInteractive[R], R],
    ) -> R | None:
        options = list(ctx.options)
        names = [getattr(o, "racer_name", None) or getattr(o, "name") for o in options]  # noqa: B009
        wanted = self.target if self.target in names else next(n for n in names if n != MUSH)
        return options[names.index(wanted)]


def leave_only(game: GameScenario, *names: RacerName) -> None:
    game.state.remove_racers(
        [n for n in game.state.available_racers if n not in names],
    )


def ability_names(game: GameScenario, idx: int) -> set[str]:
    return {a.name for a in game.get_racer(idx).active_abilities}


def copied_power_names(game: GameScenario, idx: int) -> set[str]:
    """Non-granted abilities other than Mush's own: the core a copier swapped in."""
    return {
        a.name for a in game.get_racer(idx).active_abilities if not a.granted
    } - {OWN_POWER}


def own_power(game: GameScenario, idx: int) -> MushGlobsterMashAbility:
    return next(
        a
        for a in game.get_racer(idx).active_abilities
        if isinstance(a, MushGlobsterMashAbility)
    )


def grant_persistently(game: GameScenario, idx: int, racer_name: RacerName) -> None:
    for ability in game.engine.instantiate_racer_abilities(racer_name):
        game.engine.grant_ability(idx, ability, persistent=True)


def mush_after_copier_swap(
    scenario: type[GameScenario],
    copier: RacerName,
) -> GameScenario:
    """Mush holds Banana and the copier's power, then the copier's core swap and his own low-roll turn run."""
    game = scenario(
        [
            RacerConfig(MUSH_IDX, MUSH),
            RacerConfig(1, "Centaur", start_pos=LEAD_POS),
        ],
        dice_rolls=[1],
    )
    leave_only(game, *SAFE_PILE)
    grant_persistently(game, MUSH_IDX, "Banana")
    grant_persistently(game, MUSH_IDX, copier)

    # Copycat swaps on Mush's own turn start; the others swap when setup re-runs, as in the finale.
    if copier != "Copycat":
        game.engine.setup_racers()
    game.run_turn()
    return game


def build_copier_game(
    scenario: type[GameScenario],
    copier: RacerName,
) -> tuple[GameScenario, PickByName]:
    """Copier at idx 0 holds some other racer; Mush is only in the lineup for Understudy."""
    agent = PickByName()
    lineup = [RacerConfig(0, copier, agent=agent), RacerConfig(1, "Centaur")]
    if copier == "Understudy":
        lineup.append(RacerConfig(2, MUSH))
    return scenario(lineup, dice_rolls=[1]), agent


def copy_mush(game: GameScenario, agent: PickByName) -> None:
    """Re-runs setup (as in the finale) so the copier picks Mush; Mush's roll is a 1."""
    game.engine.rng = ScriptedRandom([1], preferred=MUSH)
    game.state.shuffle()
    agent.target = MUSH
    game.engine.setup_racers()


def copy_someone_else(game: GameScenario, agent: PickByName) -> None:
    game.state.shuffle()
    agent.target = None
    game.engine.setup_racers()


# --- A. Mush holds a copier's power ---


@pytest.mark.parametrize("copier", COPIERS)
def test_mush_keeps_own_and_earlier_powers_after_a_copier_swap(
    scenario: type[GameScenario],
    copier: RacerName,
):
    game = mush_after_copier_swap(scenario, copier)

    names = ability_names(game, MUSH_IDX)
    assert copied_power_names(game, MUSH_IDX), "the copier swap did not run"
    assert OWN_POWER in names
    assert "BananaTrip" in names
    assert not own_power(game, MUSH_IDX).granted


@pytest.mark.parametrize("copier", COPIERS)
def test_mush_still_draws_a_power_on_a_low_roll_after_a_copier_swap(
    scenario: type[GameScenario],
    copier: RacerName,
):
    game = mush_after_copier_swap(scenario, copier)

    assert OWN_POWER in ability_names(game, MUSH_IDX)
    assert len(own_power(game, MUSH_IDX).copied_racers) == 1


# --- B. Mush is copied ---


def test_copycat_copying_mush_draws_then_loses_his_power_when_the_lead_changes(
    scenario: type[GameScenario],
):
    game = scenario(
        [
            RacerConfig(0, MUSH, start_pos=5),
            RacerConfig(1, "Copycat"),
            RacerConfig(2, "Centaur"),
        ],
        dice_rolls=[6, 1, 3],
    )
    leave_only(game, "Banana")

    game.run_turns(2)

    copy = own_power(game, 1)
    assert not copy.granted
    assert copy.copied_racers == ["Banana"]
    assert ability_names(game, 0) == {OWN_POWER}

    game.get_racer(2).position = COPYCAT_LEAD_POS
    game.run_turn()

    assert OWN_POWER not in ability_names(game, 1)
    assert "CentaurTrample" in ability_names(game, 1)
    assert not own_power(game, 0).granted
    assert own_power(game, 0).copied_racers == []


@pytest.mark.parametrize("copier", SETUP_COPIERS)
def test_copier_of_mush_draws_a_power_on_a_low_roll(
    scenario: type[GameScenario],
    copier: RacerName,
):
    game, agent = build_copier_game(scenario, copier)
    copy_mush(game, agent)
    assert OWN_POWER in ability_names(game, 0)

    game.run_turn()

    copy = own_power(game, 0)
    assert not copy.granted
    assert len(copy.copied_racers) == 1


@pytest.mark.parametrize("copier", SETUP_COPIERS)
def test_copier_loses_mush_power_when_it_copies_someone_else(
    scenario: type[GameScenario],
    copier: RacerName,
):
    game, agent = build_copier_game(scenario, copier)
    copy_mush(game, agent)
    assert OWN_POWER in ability_names(game, 0)

    copy_someone_else(game, agent)

    assert OWN_POWER not in ability_names(game, 0)
    assert COPIER_ABILITY[copier] in ability_names(game, 0)
    if copier == "Understudy":
        assert OWN_POWER in ability_names(game, 2)
        assert not own_power(game, 2).granted
