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
