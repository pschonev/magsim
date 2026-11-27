import random
from pathlib import Path

import polars as pl

from magsim.analysis.filters import AnalysisFilter, filter_dataset
from magsim.analysis.global_sensitivities import SENSITIVITY_COLUMNS, compute_global_sensitivities
from magsim.analysis.metrics import run_full_analysis

REPO_ROOT = Path(__file__).resolve().parent.parent
RACES_PARQUET = REPO_ROOT / "docs" / "results" / "races.parquet"
RESULTS_PARQUET = REPO_ROOT / "docs" / "results" / "racer_results.parquet"

RACERS = ("A", "B", "C", "D")
RACES_PER_BOARD = 300
BOARDS = ("Seated", "Flat", "Dicey")
OLD_COLUMNS = ("dice_dep", "ability_dep", "start_bias", "midgame_bias")
SEAT_EFFECT = 1.5
CLEAR_EFFECT = 0.3
NEAR_ZERO = 0.1
CLEAR_ROLL_SENS = 0.5


def vp_of(board: str, seat: int, sixes: int, rng: random.Random) -> float:
    noise = rng.random() * 0.3
    if board == "Seated":
        return 2 + noise + SEAT_EFFECT * (1 - seat / 3)
    if board == "Dicey":
        return 1 + sixes + noise
    return 2 + noise


def dataset() -> tuple[pl.DataFrame, pl.DataFrame]:
    """Three boards with four racers each: one with a first-seat bonus, one flat, one where VP follows the dice."""
    rng = random.Random(11)
    races, results = [], []
    for board in BOARDS:
        for i in range(RACES_PER_BOARD):
            config_hash = f"{board}{i}"
            races.append({"config_hash": config_hash, "board": board, "racer_count": len(RACERS)})
            order = list(RACERS)
            rng.shuffle(order)
            for seat, name in enumerate(order):
                faces = {f"dice_{face}": rng.randint(0, 4) for face in range(1, 7)}
                results.append(
                    {
                        "config_hash": config_hash,
                        "racer_name": name,
                        "racer_id": seat,
                        "final_vp": vp_of(board, seat, faces["dice_6"], rng),
                        "turns_taken": 10,
                        "ability_trigger_count": rng.randint(0, 3),
                        "midgame_relative_pos": rng.gauss(0, 3),
                        "rolling_turns": sum(faces.values()),
                        "sum_dice_rolled": sum(int(k[-1]) * v for k, v in faces.items()),
                        **faces,
                    },
                )
    return pl.DataFrame(results), pl.DataFrame(races)


def by_board(column: str) -> dict[str, float]:
    results, races = dataset()
    frame = compute_global_sensitivities(results, races)
    return dict(zip(frame["board"], frame[column], strict=True))


def real_global_dynamics() -> tuple[pl.DataFrame, pl.DataFrame]:
    races = pl.read_parquet(RACES_PARQUET).head(250)
    results = pl.read_parquet(RESULTS_PARQUET).join(races.select("config_hash"), on="config_hash", how="semi")
    racers = tuple(results["racer_name"].unique().to_list())
    boards = tuple(races["board"].unique().to_list())
    counts = tuple(races["racer_count"].unique().to_list())
    filtered = filter_dataset(races, results, AnalysisFilter(racers=racers, boards=boards, counts=counts))
    assert filtered.error is None
    return run_full_analysis(filtered.races, filtered.racer_results).global_dynamics, filtered.races


def test_a_first_seat_bonus_gives_a_positive_going_first_bonus_and_no_bonus_gives_about_zero() -> None:
    bonus = by_board("going_first_bonus")

    assert bonus["Seated"] > CLEAR_EFFECT
    assert abs(bonus["Flat"]) < NEAR_ZERO
    assert abs(bonus["Dicey"]) < NEAR_ZERO


def test_roll_sens_is_clearly_higher_where_vp_follows_the_dice() -> None:
    sens = by_board("roll_sens")

    assert sens["Dicey"] > CLEAR_ROLL_SENS
    assert sens["Flat"] < NEAR_ZERO
    assert sens["Seated"] < NEAR_ZERO


def test_one_row_per_board_and_player_count() -> None:
    results, races = dataset()

    frame = compute_global_sensitivities(results, races)

    assert frame.columns == ["board", "racer_count", *SENSITIVITY_COLUMNS]
    assert sorted(frame["board"].to_list()) == sorted(BOARDS)
    assert frame["racer_count"].to_list() == [len(RACERS)] * len(BOARDS)


def test_the_pipeline_keeps_the_notebook_columns_next_to_the_new_ones() -> None:
    dynamics, _ = real_global_dynamics()

    for column in (*OLD_COLUMNS, *SENSITIVITY_COLUMNS):
        assert column in dynamics.columns


def test_the_pipeline_has_one_global_dynamics_row_per_board_and_player_count() -> None:
    dynamics, races = real_global_dynamics()

    cells = races.select("board", "racer_count").unique()

    assert dynamics.height == cells.height
    assert dynamics.select("board", "racer_count").is_unique().all()
