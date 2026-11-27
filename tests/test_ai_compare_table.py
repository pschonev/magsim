from datetime import UTC, datetime

import msgspec

from magsim.analysis.ai_compare import ai_compare_rows
from magsim.analysis.baseline import ExperimentResult, run_ai_comparison
from magsim.analysis.filters import racers_with_decisions
from magsim.web.schemas import AiCompareDTO

SMALL_RUN_GAMES = 3


def experiment(racer: str, games: int, vp: tuple[float, float], wins: tuple[float, float], se: float | None) -> ExperimentResult:
    return ExperimentResult(
        run_id="test",
        timestamp=datetime.now(UTC),
        racer=racer,  # pyrefly: ignore[bad-argument-type]
        games_played=games,
        winrate_control=wins[0],
        winrate_treatment=wins[1],
        vp_control=vp[0],
        vp_treatment=vp[1],
        max_vp_control=10,
        max_vp_treatment=10,
        elapsed_control=1.0,
        elapsed_treatment=1.0,
        vp_delta_se=se,
    )


def test_rows_hold_deltas_and_percentages_sorted_by_relative_gain() -> None:
    table = ai_compare_rows(
        [
            experiment("Banana", 100, (4.0, 4.2), (0.2, 0.25), 0.05),
            experiment("Magician", 200, (5.0, 6.0), (0.3, 0.4), None),
            experiment("Egg", 0, (0.0, 0.0), (0.0, 0.0), None),
        ],
    )

    assert table["racer_name"].to_list() == ["Magician", "Banana"]
    magician, banana = table.to_dicts()
    assert magician["games"] == 200
    assert abs(magician["vp_delta"] - 1.0) < 1e-9
    assert abs(magician["vp_delta_pct"] - 20.0) < 1e-9
    assert abs(magician["win_delta"] - 0.1) < 1e-9
    assert magician["vp_delta_se"] is None
    assert abs(banana["vp_delta_pct"] - 5.0) < 1e-9
    assert abs(banana["win_delta"] - 0.05) < 1e-9
    assert banana["vp_delta_se"] == 0.05


def test_rows_convert_to_the_export_dto() -> None:
    table = ai_compare_rows([experiment("Banana", 100, (4.0, 4.2), (0.2, 0.25), 0.05)])

    dtos = [msgspec.convert(row, AiCompareDTO) for row in table.to_dicts()]

    assert [d.racer_name for d in dtos] == ["Banana"]


def test_a_tiny_real_run_gives_a_valid_row() -> None:
    racer = racers_with_decisions()[0]

    result = run_ai_comparison(racer, n_games=SMALL_RUN_GAMES, quiet=True)  # pyrefly: ignore[bad-argument-type]
    row = ai_compare_rows([result]).to_dicts()[0]

    assert row["racer_name"] == racer
    assert row["games"] == SMALL_RUN_GAMES
    assert row["vp_baseline"] >= 0
    assert row["vp_smart"] >= 0
    assert abs(row["vp_delta"] - (row["vp_smart"] - row["vp_baseline"])) < 1e-9
    assert row["vp_delta_se"] is not None
    assert row["vp_delta_se"] >= 0
