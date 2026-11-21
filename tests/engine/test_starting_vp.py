from magsim.core.state import GameRules
from magsim.engine.scenario import GameScenario, RacerConfig
from magsim.simulation.telemetry import MetricsAggregator

MAX_PLAUSIBLE_VP = 40
SEEDS = range(30)


def _racers() -> list[RacerConfig]:
    return [
        RacerConfig(0, "Centaur", abilities=set()),
        RacerConfig(1, "Banana"),
        RacerConfig(2, "Mouth"),
        RacerConfig(3, "Hotel", abilities=set()),
    ]


def test_starting_vp_off_by_default(scenario: type[GameScenario]):
    game = scenario(_racers(), dice_rolls=[1], seed=1)

    for racer in game.state.racers:
        assert racer.victory_points == 0
        assert racer.starting_vp == 0


def test_starting_vp_recorded_and_bounded(scenario: type[GameScenario]):
    for seed in SEEDS:
        game = scenario(
            _racers(),
            dice_rolls=[1],
            rules=GameRules(starting_vp=True),
            seed=seed,
        )
        for racer in game.state.racers:
            assert racer.starting_vp == racer.victory_points
            assert 0 <= racer.starting_vp <= MAX_PLAUSIBLE_VP


def test_starting_vp_is_assigned_for_some_seeds(scenario: type[GameScenario]):
    totals = [
        sum(
            r.victory_points
            for r in scenario(
                _racers(),
                dice_rolls=[1],
                rules=GameRules(starting_vp=True),
                seed=seed,
            ).state.racers
        )
        for seed in SEEDS
    ]

    assert any(t > 0 for t in totals)
    assert any(t == 0 for t in totals)


def test_starting_vp_does_not_consume_dice_values(scenario: type[GameScenario]):
    game = scenario(
        _racers(),
        dice_rolls=[4],
        rules=GameRules(starting_vp=True),
        seed=3,
    )

    game.run_turn()

    assert game.get_racer(0).position == 4


def test_starting_vp_not_reassigned_in_sandbox_engine(scenario: type[GameScenario]):
    game = scenario(
        _racers(),
        dice_rolls=[1],
        rules=GameRules(starting_vp=True),
        seed=3,
    )
    before = [r.victory_points for r in game.state.racers]

    game.run_turn()

    after = [r.victory_points for r in game.state.racers]
    assert all(a >= b for a, b in zip(after, before, strict=True))


def test_for_play_enables_starting_vp():
    assert GameRules.for_play({}).starting_vp


def test_for_play_applies_overrides():
    rules = GameRules.for_play({"winner_vp": (7, 3)})

    assert rules.starting_vp
    assert rules.winner_vp == (7, 3)


def test_for_play_override_can_disable_starting_vp():
    assert not GameRules.for_play({"starting_vp": False}).starting_vp


def test_reported_final_vp_excludes_starting_vp(scenario: type[GameScenario]):
    seen_nonzero_start = False

    for seed in SEEDS:
        game = scenario(
            _racers(),
            dice_rolls=None,
            rules=GameRules.for_play({}),
            seed=seed,
        )
        aggregator = MetricsAggregator(config_hash="test")
        aggregator.initialize_racers(game.engine)
        starts = {r.idx: r.starting_vp for r in game.state.racers}

        game.engine.run_race()
        results = aggregator.finalize_metrics(game.engine)

        for result in results:
            racer = game.get_racer(result.racer_id)
            assert result.final_vp == racer.victory_points - starts[racer.idx]
            assert result.final_vp >= -starts[racer.idx]
        seen_nonzero_start |= any(starts.values())

    assert seen_nonzero_start


def test_generic_starting_vp_only_with_hotel_or_copier(scenario: type[GameScenario]):
    no_hotel = [r for r in _racers() if r.name != "Hotel"]

    for seed in SEEDS:
        game = scenario(
            no_hotel,
            dice_rolls=[1],
            rules=GameRules(starting_vp=True),
            seed=seed,
        )
        assert all(r.starting_vp == 0 for r in game.state.racers)

    with_mush = [*no_hotel, RacerConfig(3, "Mush", abilities=set())]
    starts = [
        r.starting_vp
        for seed in SEEDS
        for r in scenario(
            with_mush,
            dice_rolls=[1],
            rules=GameRules(starting_vp=True),
            seed=seed,
        ).state.racers
    ]
    assert any(starts)


def test_sisyphus_game_is_a_first_race_with_zero_vp_for_all(
    scenario: type[GameScenario],
):
    racers = [*_racers(), RacerConfig(4, "Sisyphus", abilities=set())]

    for seed in SEEDS:
        game = scenario(
            racers,
            dice_rolls=[1],
            rules=GameRules(starting_vp=True),
            seed=seed,
        )
        assert all(r.starting_vp == 0 for r in game.state.racers)
