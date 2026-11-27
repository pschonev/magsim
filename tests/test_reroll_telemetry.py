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


def test_critic_reroll_counts_as_negative_movement_for_the_target(
    scenario: type[GameScenario],
):
    game = scenario(
        [dummy(0, 10), RacerConfig(1, "Critic", start_pos=0)],
        dice_rolls=[6, 2],
    )

    critic = play_turns(game, 1)[1]

    assert critic.neg_other_ability_movement == 4
    assert critic.pos_other_ability_movement == 0


def test_critic_reroll_to_a_higher_roll_counts_as_positive_movement(
    scenario: type[GameScenario],
):
    game = scenario(
        [dummy(0, 10), RacerConfig(1, "Critic", start_pos=0)],
        dice_rolls=[4, 6],
    )

    critic = play_turns(game, 1)[1]

    assert critic.pos_other_ability_movement == 2
    assert critic.neg_other_ability_movement == 0


def test_no_reroll_records_no_reroll_movement(scenario: type[GameScenario]):
    game = scenario(
        [dummy(0, 0), RacerConfig(1, "Critic", start_pos=5)],
        dice_rolls=[6, 2],
    )

    critic = play_turns(game, 1)[1]

    assert critic.neg_other_ability_movement == 0
    assert critic.pos_other_ability_movement == 0


def test_party_pooper_rejection_costs_the_roller_the_difference_to_six(
    scenario: type[GameScenario],
):
    game = scenario(
        [RacerConfig(0, "PartyPooper", start_pos=10), dummy(1, 0)],
        dice_rolls=[1, 6, 3],
    )

    pooper = play_turns(game, 2)[0]

    assert pooper.neg_other_ability_movement == 3
    assert pooper.pos_self_ability_movement == 1


def test_party_pooper_chain_of_sixes_counts_the_loss_once(
    scenario: type[GameScenario],
):
    game = scenario(
        [RacerConfig(0, "PartyPooper", start_pos=10), dummy(1, 0)],
        dice_rolls=[1, 6, 6, 4],
    )

    pooper = play_turns(game, 2)[0]

    assert pooper.neg_other_ability_movement == 2
    assert pooper.pos_self_ability_movement == 2
