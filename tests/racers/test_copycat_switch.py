from magsim.engine.scenario import GameScenario, RacerConfig
from magsim.simulation.telemetry import MetricsAggregator


def test_copycat_switching_who_it_copies_is_not_a_power_use(scenario: type[GameScenario]):
    """Copycat copies the new leader without triggering; Scoocher only reacts to real power uses."""
    game = scenario(
        [
            RacerConfig(0, "Copycat", start_pos=0),
            RacerConfig(1, "Scoocher", start_pos=20),
            RacerConfig(2, "Legs", start_pos=10),
        ],
        dice_rolls=[1],
    )
    aggregator = MetricsAggregator(config_hash="test")
    aggregator.initialize_racers(game.engine)
    game.engine.on_event_processed = lambda eng, event: aggregator.on_event(event=event, engine=eng)

    game.run_turn()

    assert game.get_racer(1).position == 20
    assert aggregator.results[0].ability_trigger_count == 0
