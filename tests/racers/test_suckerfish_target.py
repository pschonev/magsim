from magsim.core.events import Phase
from magsim.engine.abilities import add_racer_modifier
from magsim.engine.movement import push_move
from magsim.engine.scenario import GameScenario, RacerConfig
from magsim.racers.suckerfish import SuckerfishTargetModifier


def test_a_trample_before_the_ride_moves_suckerfish_back_and_keeps_the_ride_target(
    scenario: type[GameScenario],
):
    game = scenario(
        [
            RacerConfig(0, "Centaur", abilities=set(), start_pos=0),
            RacerConfig(1, "Centaur", start_pos=20),
            RacerConfig(2, "Suckerfish", start_pos=10),
        ],
        dice_rolls=[1],
    )
    target = SuckerfishTargetModifier(owner_idx=2, target_tile=17)
    add_racer_modifier(game.engine, 2, target)
    push_move(
        game.engine,
        distance=-2,
        phase=Phase.REACTION,
        moved_racer_idx=2,
        source="CentaurTrample",
        responsible_racer_idx=1,
    )

    game.run_turn()

    assert game.get_racer(2).position == 8
    assert target in game.get_racer(2).modifiers
