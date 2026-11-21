from magsim.core.events import GameEvent
from magsim.engine.game_engine import GameEngine
from magsim.engine.scenario import RacerConfig
from magsim.simulation.telemetry import MetricsAggregator

TURNS = 6


def _run(scenario, racers: list[RacerConfig], rolls: list[int]):
    game = scenario(racers, dice_rolls=rolls)
    aggregator = MetricsAggregator(config_hash="test")
    aggregator.initialize_racers(game.engine)

    def on_event(engine: GameEngine, event: GameEvent):
        aggregator.on_event(event=event, engine=engine)

    game.engine.on_event_processed = on_event
    for turn in range(TURNS):
        if not game.engine.state.race_active:
            break
        idx = game.engine.state.current_racer_idx
        game.engine.run_turn()
        aggregator.on_turn_end(game.engine, turn_index=turn, active_racer_idx=idx)
        game.engine.advance_turn()
    return aggregator.results


def test_magical_athlete_trade_is_not_a_lost_main_move(scenario):
    results = _run(
        scenario,
        [RacerConfig(0, "MagicalAthlete"), RacerConfig(1, "Banana")],
        rolls=[1],
    )

    assert results[0].skipped_main_moves == 0
    assert results[0].turns_taken > 0


def test_hare_skip_is_a_lost_main_move(scenario):
    results = _run(
        scenario,
        [RacerConfig(0, "Hare", start_pos=10), RacerConfig(1, "Banana")],
        rolls=[1],
    )

    assert results[0].skipped_main_moves > 0


def test_skipper_turn_skip_is_not_subtracted_from_turns(scenario):
    results = _run(
        scenario,
        [
            RacerConfig(0, "Banana"),
            RacerConfig(1, "Banana"),
            RacerConfig(2, "Skipper"),
        ],
        rolls=[1],
    )

    assert results[1].skipped_main_moves == 0
    assert results[2].skipped_other_main_move > 0
