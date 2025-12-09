from dataclasses import dataclass, field
from unittest.mock import MagicMock
from magical_athlete_simulator.game import (
    GameEngine,
    GameState,
    RacerName,
    RacerState,
    AbilityName,
)


@dataclass
class RacerConfig:
    idx: int
    name: RacerName
    abilities: set[AbilityName]
    start_pos: int = 0  # Default to 0, so we don't always have to type it


class GameScenario:
    """
    A reusable harness that wraps the GameEngine for testing.
    """

    def __init__(
        self,
        racers_config: list[RacerConfig],
        dice_rolls: list[int] | None = None,
    ):
        racers = []

        # 1. Setup Racers from Config
        for cfg in racers_config:
            r = RacerState(cfg.idx, cfg.name, position=cfg.start_pos)
            racers.append(r)

        # 2. Mock the RNG
        self.mock_rng = MagicMock()

        # 3. Initialize Engine
        self.state = GameState(racers)
        self.engine = GameEngine(self.state, self.mock_rng)

        # 4. Register Abilities
        for cfg in racers_config:
            self.engine.update_racer_abilities(cfg.idx, cfg.abilities)

        if dice_rolls:
            self.set_dice_rolls(dice_rolls)

    def set_dice_rolls(self, rolls: list[int]):
        """Script the dice rolls (e.g., [1, 6])."""
        self.mock_rng.randint.side_effect = rolls

    def run_turn(self):
        self.engine.run_turn()
        self.engine.advance_turn()

    def get_racer(self, idx: int) -> RacerState:
        return self.engine.get_racer(idx)
