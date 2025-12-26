from tests.test_utils import GameScenario, RacerConfig

def test_flip_flop_vs_baba_yaga_simultaneous(scenario: type[GameScenario]):
    """
    Flip Flop swaps with Baba Yaga. 
    Sequential warp would place Flip Flop on Baba Yaga's space momentarily (or vice versa), triggering trip.
    Simultaneous warp should avoid this sharing state.
    """
    game = scenario(
        [
            RacerConfig(0, "FlipFlop", start_pos=0),
            RacerConfig(1, "BabaYaga", start_pos=10),
        ],
        dice_rolls=[1] # Unused
    )
    
    # Flip Flop (0) is >6 behind Baba Yaga (10). Swap is valid.
    game.run_turn()
    
    ff = game.get_racer(0)
    baba = game.get_racer(1)
    
    assert ff.position == 10, "Flip Flop should be at 10"
    assert baba.position == 0, "Baba Yaga should be at 0"
    
    # This assertion will fail until simultaneous warp logic is implemented
    assert ff.tripped is False, "Flip Flop should not be tripped by Baba Yaga during swap"
