from magsim.engine.scenario import GameScenario, RacerConfig


def test_re_runner_is_a_generic_racer_without_abilities(
    scenario: type[GameScenario],
):
    game = scenario(
        [RacerConfig(0, "ReRunner"), RacerConfig(1, "Banana")],  # pyright: ignore[reportArgumentType]
        dice_rolls=[4, 2],
    )

    game.run_turn()

    racer = game.get_racer(0)
    assert racer.position == 4
    assert len(racer.active_abilities) == 0
