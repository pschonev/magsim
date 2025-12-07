from unittest.mock import MagicMock
from magical_athlete_simulator.game import GameEngine, GameState, RacerName, RacerState


class GameScenario:
    """
    A reusable harness that wraps the GameEngine for testing.
    """

    def __init__(self, racers_config: list[tuple[int, RacerName, set[str], int]]):
        """
        config format: [(idx, name, {abilities}, start_pos), ...]
        """
        racers = []
        for idx, name, _, pos in racers_config:
            # Create racer
            r = RacerState(idx, name, position=pos)
            racers.append(r)

        # Mock the RNG
        self.mock_rng = MagicMock()

        # Initialize Engine with Mock RNG
        self.state = GameState(racers)
        self.engine = GameEngine(self.state, self.mock_rng)

        # Register Abilities manually since we aren't using the main block
        for r in racers:
            abilities_set = racers_config[r.idx][2]
            self.engine.update_racer_abilities(r.idx, abilities_set)

    def set_dice_rolls(self, rolls: list[int]):
        """
        Script the dice rolls.
        Example: game.set_dice_rolls([1, 6])
        """
        self.mock_rng.randint.side_effect = rolls

    def run_turn(self):
        self.engine.run_turn()

    def get_racer(self, idx: int) -> RacerState:
        return self.engine.get_racer(idx)
