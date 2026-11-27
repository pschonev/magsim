import polars as pl

import magsim.web.dashboard_api as api
from magsim.web.schemas import AnalysisFilterDTO

RESULTS_DIR = "docs/results"


def test_environment_matrix_carries_board_count_and_grand_totals() -> None:
    races = pl.read_parquet(f"{RESULTS_DIR}/races.parquet").head(3000)
    results = pl.read_parquet(f"{RESULTS_DIR}/racer_results.parquet").join(
        races.select("config_hash"),
        on="config_hash",
    )
    dataset = api.load_dataframes(races, results)
    meta = api.get_metadata(dataset)
    everything = AnalysisFilterDTO(racers=meta.racers, boards=meta.boards, counts=meta.counts, combos=[])

    cells = api.analyze(api.apply_filter(dataset, everything)).environment_matrix

    board_totals = {c.board for c in cells if c.racer_count is None and c.board is not None}
    count_totals = {c.racer_count for c in cells if c.board is None and c.racer_count is not None}
    grand = [c for c in cells if c.board is None and c.racer_count is None]
    assert board_totals == set(meta.boards)
    assert count_totals == set(meta.counts)
    assert len(grand) == len({c.racer_name for c in cells})
    assert all(c.relative_shift == 0 for c in grand)
