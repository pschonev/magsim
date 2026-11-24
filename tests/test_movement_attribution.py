from magsim.ai.baseline_agent import BaselineAgent
from magsim.core.events import RollResultEvent
from magsim.engine.scenario import GameScenario, RacerConfig
from magsim.simulation.db.models import RacerResult
from magsim.simulation.telemetry import MetricsAggregator


def dummy(idx: int, pos: int = 0) -> RacerConfig:
    return RacerConfig(idx, "Centaur", abilities=set(), start_pos=pos)


def play_turns(game: GameScenario, turns: int) -> dict[int, RacerResult]:
    engine = game.engine
    aggregator = MetricsAggregator(config_hash="test")
    aggregator.initialize_racers(engine)
    engine.on_event_processed = lambda eng, event: aggregator.on_event(
        event=event,
        engine=eng,
    )
    for turn_index in range(turns):
        racer_idx = engine.state.current_racer_idx
        engine.run_turn()
        aggregator.on_turn_end(engine, turn_index=turn_index, active_racer_idx=racer_idx)
        engine.advance_turn()
    return aggregator.results


def test_nemesis_match_counts_the_move_once(scenario: type[GameScenario]):
    game = scenario([dummy(0), RacerConfig(1, "Nemesis")], dice_rolls=[3])

    nemesis = play_turns(game, 1)[1]

    assert game.get_racer(1).position == 3
    assert nemesis.pos_self_ability_movement == 3


def test_hog_bonus_and_triggers_belong_to_hog_knight_not_the_rider(
    scenario: type[GameScenario],
):
    game = scenario(
        [dummy(0), RacerConfig(1, "HogKnight", start_pos=5)],
        dice_rolls=[5, 6, 1],
    )

    results = play_turns(game, 3)

    hog_knight, rider = results[1], results[0]
    assert hog_knight.pos_other_ability_movement == 2
    assert hog_knight.pos_self_ability_movement == 0
    assert hog_knight.ability_trigger_count == 2
    assert rider.pos_self_ability_movement == 0
    assert rider.ability_trigger_count == 0


def test_hog_credit_goes_to_hog_knight_in_the_first_seat(scenario: type[GameScenario]):
    game = scenario(
        [RacerConfig(0, "HogKnight", start_pos=5), dummy(1, 8)],
        dice_rolls=[6, 5, 6, 1],
    )

    results = play_turns(game, 4)

    assert results[0].ability_trigger_count == 3
    assert results[0].pos_self_ability_movement == 2
    assert results[0].pos_other_ability_movement == 2
    assert results[1].ability_trigger_count == 0
    assert results[1].pos_self_ability_movement == 0


def test_hog_knight_riding_his_own_hog_counts_as_self_movement(
    scenario: type[GameScenario],
):
    game = scenario([RacerConfig(0, "HogKnight"), dummy(1)], dice_rolls=[2])

    results = play_turns(game, 1)

    assert results[0].pos_self_ability_movement == 2
    assert results[0].pos_other_ability_movement == 0


def test_nepo_baby_head_start_counts_as_self_movement(scenario: type[GameScenario]):
    game = scenario([RacerConfig(0, "NepoBaby"), dummy(1)], dice_rolls=[3])

    nepo = play_turns(game, 0)[0]

    assert nepo.pos_self_ability_movement == game.get_racer(0).position
    assert nepo.pos_self_ability_movement > 0


def test_show_off_extra_dice_count_as_self_movement(scenario: type[GameScenario]):
    game = scenario(
        [RacerConfig(0, "ShowOff", agent=BaselineAgent()), dummy(1)],
        dice_rolls=[2, 5],
    )

    show_off = play_turns(game, 1)[0]

    assert game.get_racer(0).position == 7
    assert show_off.pos_self_ability_movement == 5


def test_mr_dice_guy_is_credited_the_difference_to_an_average_die(
    scenario: type[GameScenario],
):
    game = scenario(
        [RacerConfig(0, "MrDiceGuy"), dummy(1)],
        dice_rolls=[6, 6, 2, 3, 4, 5],
    )

    mr_dice_guy = play_turns(game, 1)[0]

    assert game.get_racer(0).position == 6
    assert mr_dice_guy.pos_self_ability_movement == 2.5


def test_stunner_is_credited_with_the_roll_it_takes_from_a_neighbour(
    scenario: type[GameScenario],
):
    game = scenario(
        [dummy(0, 5), RacerConfig(1, "Stunner", start_pos=6)],
        dice_rolls=[6],
    )

    stunner = play_turns(game, 1)[1]

    assert game.get_racer(0).position == 6
    assert stunner.neg_other_ability_movement == 2.5


def test_stunner_does_not_affect_far_away_rolls(scenario: type[GameScenario]):
    game = scenario(
        [dummy(0, 0), RacerConfig(1, "Stunner", start_pos=10)],
        dice_rolls=[1],
    )

    stunner = play_turns(game, 1)[1]

    assert stunner.neg_other_ability_movement == 0


def test_eliminated_roller_next_to_nobody_does_not_crash_the_stunner_check(
    scenario: type[GameScenario],
):
    game = scenario([dummy(0, 5), RacerConfig(1, "Stunner", start_pos=6)], dice_rolls=[1])
    engine = game.engine
    aggregator = MetricsAggregator(config_hash="test")
    aggregator.initialize_racers(engine)
    engine.get_racer(0).eliminate()

    aggregator.on_event(
        RollResultEvent(
            target_racer_idx=0,
            responsible_racer_idx=0,
            source="System",
            dice_value=1,
            dice_values=(1,),
            base_value=1,
            final_value=1,
        ),
        engine,
    )

    assert aggregator.results[1].neg_other_ability_movement == 0


def test_show_off_bust_costs_the_first_die_not_an_average_roll(scenario: type[GameScenario]):
    game = scenario(
        [RacerConfig(0, "ShowOff", agent=BaselineAgent()), dummy(1)],
        dice_rolls=[2, 1],
    )

    show_off = play_turns(game, 1)[0]

    assert game.get_racer(0).position == 0
    assert show_off.neg_self_ability_movement == 2
    assert show_off.skipped_self_main_move == 0


def test_hog_credit_survives_hog_knight_losing_his_abilities(scenario: type[GameScenario]):
    game = scenario(
        [dummy(0, 4), RacerConfig(1, "HogKnight", start_pos=5), RacerConfig(2, "Null", start_pos=0)],
        dice_rolls=[2],
    )
    assert not game.get_racer(1).active_abilities

    results = play_turns(game, 1)

    assert game.get_racer(0).position == 5
    assert results[0].ability_trigger_count == 0
    assert results[1].ability_trigger_count == 1


def test_hog_of_a_copied_hog_knight_belongs_to_the_copier(scenario: type[GameScenario]):
    game = scenario(
        [RacerConfig(0, "Understudy", start_pos=0), RacerConfig(1, "HogKnight", start_pos=10)],
        dice_rolls=[1],
    )

    results = play_turns(game, 1)

    assert game.get_racer(0).position == 3
    assert results[0].pos_self_ability_movement == 2
    assert results[0].ability_trigger_count == 1
    assert results[1].pos_other_ability_movement == 0
    assert results[1].ability_trigger_count == 0


def test_mr_dice_guy_counts_one_trigger_per_main_roll(scenario: type[GameScenario]):
    game = scenario([RacerConfig(0, "MrDiceGuy"), dummy(1)], dice_rolls=[6, 6, 2, 3, 4, 5, 1])

    mr_dice_guy = play_turns(game, 3)[0]

    assert mr_dice_guy.ability_trigger_count == 2
    assert mr_dice_guy.ability_self_target_count == 2


def test_show_off_counts_a_trigger_only_when_rolling_extra_dice(scenario: type[GameScenario]):
    game = scenario(
        [RacerConfig(0, "ShowOff", agent=BaselineAgent()), dummy(1)],
        dice_rolls=[2, 5, 1, 6, 3],
    )

    show_off = play_turns(game, 3)[0]

    assert show_off.ability_trigger_count == 1


def test_stunner_counts_a_trigger_per_forced_roll(scenario: type[GameScenario]):
    game = scenario(
        [dummy(0, 5), RacerConfig(1, "Stunner", start_pos=6)],
        dice_rolls=[6],
    )

    stunner = play_turns(game, 1)[1]

    assert stunner.ability_trigger_count == 1
    assert stunner.ability_self_target_count == 0


def test_reversed_hog_bonus_still_belongs_to_hog_knight(scenario: type[GameScenario]):
    """Le Saboteur reverses a rolled 3, which turns the hog's +2 into -2; the rider is not charged."""
    game = scenario(
        [dummy(0, 4), RacerConfig(1, "HogKnight", start_pos=5), RacerConfig(2, "LeSaboteur", start_pos=20)],
        dice_rolls=[1, 1, 1, 3],
    )

    results = play_turns(game, 4)

    rider = results[0]
    assert rider.neg_self_ability_movement == 0
    assert results[1].neg_other_ability_movement == 2
