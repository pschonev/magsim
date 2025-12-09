import pytest
from tests.test_utils import GameScenario


@pytest.fixture
def scenario():
    """Factory fixture to create scenarios."""

    def _builder(racers_config, dice_rolls):
        return GameScenario(racers_config, dice_rolls)

    return _builder
