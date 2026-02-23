from typing import Callable
import pytest
from magsim.core.state import GameRules
from magsim.engine.board import Board
from magsim.engine.scenario import GameScenario, RacerConfig


@pytest.fixture
def scenario() -> Callable[..., GameScenario]:
    """Factory fixture to create scenarios."""

    def _builder(racers_config: list[RacerConfig], dice_rolls: list[int], board: Board | None = None, rules: GameRules | None = None, seed: int | None = None) -> GameScenario:
        return GameScenario(racers_config, dice_rolls, board, rules, seed)

    return _builder
