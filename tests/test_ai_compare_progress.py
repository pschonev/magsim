import sys
from pathlib import Path

import polars as pl

from magsim.analysis.baseline import run_ai_comparison
from magsim.analysis.filters import racers_with_decisions

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
GAMES = 3
EXCLUDED = "Cheatah"

sys.path.insert(0, str(SCRIPTS_DIR))
import ai_compare  # noqa: E402


def comparable_racers() -> list[str]:
    return [racer for racer in racers_with_decisions() if racer != EXCLUDED]


def test_on_game_fires_once_per_counted_game() -> None:
    racer = comparable_racers()[0]
    calls: list[int] = []

    result = run_ai_comparison(racer, n_games=GAMES, quiet=True, on_game=lambda: calls.append(1))  # pyrefly: ignore[bad-argument-type]

    assert result.games_played == GAMES
    assert len(calls) == GAMES


def test_script_main_writes_one_row_per_racer(tmp_path: Path) -> None:
    racers = comparable_racers()[:2]
    output = tmp_path / "x.parquet"

    code = ai_compare.main(["--games", str(GAMES), "--racers", *racers, "--output", str(output)])

    table = pl.read_parquet(output)
    assert code == 0
    assert table.height == len(racers)
    assert sorted(table["racer_name"].to_list()) == sorted(racers)
