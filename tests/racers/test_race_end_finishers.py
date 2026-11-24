from magsim.engine.flow import mark_finished
from magsim.engine.scenario import GameScenario, RacerConfig


def dummy(idx: int, pos: int) -> RacerConfig:
    return RacerConfig(idx, "Centaur", abilities=set(), start_pos=pos)


def test_simultaneous_cheer_over_the_line_ranks_only_the_second_finisher(
    scenario: type[GameScenario],
):
    """The race ends at the second finisher; racers crossing in the same cheer get no rank."""
    game = scenario(
        [RacerConfig(0, "Cheerleader", start_pos=29), dummy(1, 29), dummy(2, 29), dummy(3, 30)],
        dice_rolls=[1],
    )
    mark_finished(game.engine, game.get_racer(3))

    game.run_turn()

    ranks = sorted(r.finish_position for r in game.state.racers if r.finish_position is not None)
    assert ranks == [1, 2]
    assert not game.state.race_active
    assert sum(r.victory_points for r in game.state.racers) == 6
