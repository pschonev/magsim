import pytest
from tests.test_utils import GameScenario


@pytest.fixture
def scenario():
    """Factory fixture to create scenarios easily in tests."""

    def _builder(racers_config):
        return GameScenario(racers_config)

    return _builder
