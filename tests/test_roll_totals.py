from magsim.engine.scenario import GameScenario, RacerConfig
from tests.test_reroll_telemetry import dummy, play_turns


def test_show_off_records_the_total_of_its_dice(scenario: type[GameScenario]) -> None:
    game = scenario(
        [dummy(0, 20), RacerConfig(1, "ShowOff", start_pos=0)],
        dice_rolls=[1, 2, 5],
    )

    show_off = play_turns(game, 2)[1]

    assert show_off.main_roll_totals == [7]


def test_other_racers_record_no_roll_totals(scenario: type[GameScenario]) -> None:
    game = scenario([dummy(0, 0), dummy(1, 5)], dice_rolls=[4])

    assert play_turns(game, 1)[0].main_roll_totals is None


def test_magician_records_the_roll_it_kept_after_rerolling(scenario: type[GameScenario]) -> None:
    game = scenario(
        [dummy(0, 20), RacerConfig(1, "Magician", start_pos=0)],
        dice_rolls=[1, 1, 6],
    )

    magician = play_turns(game, 2)[1]

    assert magician.main_roll_totals == [6]


def finalized(game: GameScenario, turns: int):
    """Play turns and return the results the way the batch writes them."""
    from magsim.simulation.telemetry import MetricsAggregator

    engine = game.engine
    aggregator = MetricsAggregator(config_hash="test")
    aggregator.initialize_racers(engine)
    engine.on_event_processed = lambda eng, event: aggregator.on_event(event=event, engine=eng)
    for turn_index in range(turns):
        racer_idx = engine.state.current_racer_idx
        engine.run_turn()
        aggregator.on_turn_end(engine, turn_index=turn_index, active_racer_idx=racer_idx)
        engine.advance_turn()
    return aggregator.finalize_metrics(engine)


def test_mastermind_records_who_it_predicted(scenario: type[GameScenario]) -> None:
    game = scenario(
        [RacerConfig(0, "Mastermind", start_pos=0), dummy(1, 5), dummy(2, 8)],
        dice_rolls=[1, 1, 1],
    )

    results = finalized(game, 1)

    assert results[0].predicted_racer_id in {1, 2}
    assert results[1].predicted_racer_id is None


def test_mush_records_the_powers_it_drew(scenario: type[GameScenario]) -> None:
    game = scenario([RacerConfig(0, "Mush", start_pos=0), dummy(1, 20)], dice_rolls=[1, 1, 1])

    results = finalized(game, 1)

    assert results[0].copied_racers is not None
    assert len(results[0].copied_racers) == 1
    assert results[1].copied_racers is None


def test_cheatah_records_every_number_it_set_as_played_or_guessed(scenario: type[GameScenario]) -> None:
    from magsim.ai.baseline_agent import BaselineAgent

    game = scenario(
        [
            RacerConfig(0, "Cheatah", start_pos=0, agent=BaselineAgent()),  # pyright: ignore[reportArgumentType]
            dummy(1, 0),
        ],
        dice_rolls=[1] * 40,
    )

    cheatah = play_turns(game, 12)[0]

    played = cheatah.main_roll_totals or []
    guessed = cheatah.guessed_rolls or []
    assert len(played) + len(guessed) == 6
    assert set(played + guessed) == {6}


def test_every_die_a_racer_rolls_is_counted_including_the_ones_it_rerolls_away(scenario: type[GameScenario]) -> None:
    from magsim.simulation.telemetry import MetricsAggregator

    game = scenario(
        [dummy(0, 20), RacerConfig(1, "Magician", start_pos=0)],
        dice_rolls=[3, 1, 1, 6],
    )
    engine = game.engine
    aggregator = MetricsAggregator(config_hash="test")
    aggregator.initialize_racers(engine)
    engine.on_event_processed = lambda eng, event: aggregator.on_event(event=event, engine=eng)
    engine.on_die_rolled = aggregator.on_die_rolled
    for turn_index in range(2):
        racer_idx = engine.state.current_racer_idx
        engine.run_turn()
        aggregator.on_turn_end(engine, turn_index=turn_index, active_racer_idx=racer_idx)
        engine.advance_turn()

    magician = aggregator.results[1]

    assert (magician.dice_1, magician.dice_6) == (2, 1)
    assert aggregator.results[0].dice_3 == 1
