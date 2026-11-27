from magsim.engine.scenario import GameScenario, RacerConfig
from magsim.simulation.telemetry import MetricsAggregator


def test_spoilsport_cancel_is_recorded_as_a_trigger(scenario: type[GameScenario]):
    game = scenario(
        [RacerConfig(0, "Spoilsport", start_pos=0), RacerConfig(1, "Centaur", start_pos=10)],
        dice_rolls=[3],
    )
    aggregator = MetricsAggregator(config_hash="test")
    aggregator.initialize_racers(game.engine)
    game.engine.on_event_processed = lambda eng, event: aggregator.on_event(event=event, engine=eng)

    game.run_turn()

    assert not game.state.race_active
    assert game.get_racer(0).victory_points == 3
    assert aggregator.results[0].ability_trigger_count == 1
