import polars as pl

from magsim.simulation.metrics import calculate_aggregated_racer_stats


def test_speed_counts_override_rolls_and_divides_by_turns_taken() -> None:
    df = pl.DataFrame(
        {
            "racer_name": ["Legs", "Cheatah"],
            "sum_dice_rolled": [0, 0],
            "pos_self_ability_movement": [10, 5],
            "rolling_turns": [0, 0],
            "turns_taken": [4, 4],
            "recovery_turns": [0, 0],
            "skipped_main_moves": [0, 2],
            "finish_position": [1, 2],
            "final_vp": [3, 1],
        },
    )

    speeds = {
        row["racer_name"]: row["speed"]
        for row in calculate_aggregated_racer_stats(df).to_dicts()
    }

    assert speeds["Legs"] == (10 + 3.5 * 4) / 4
    assert speeds["Cheatah"] == (5 + 3.5 * 2) / 4
