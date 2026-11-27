import msgspec
import polars as pl

from magsim.analysis.profiles import compute_profiles
from magsim.web.schemas import ProfileDTO
from tests.test_profiles import dataset


def test_races_is_an_integer_column() -> None:
    results, races = dataset()

    assert compute_profiles(results, races)["races"].dtype.is_integer()


def test_every_profile_row_converts_to_the_export_dto() -> None:
    results, races = dataset()
    profiles = compute_profiles(results, races).with_columns(pl.col(pl.Float64).round(4))

    dtos = [msgspec.convert(row, ProfileDTO) for row in profiles.to_dicts()]

    assert [d.racer_name for d in dtos] == profiles["racer_name"].to_list()
    assert [d.races for d in dtos] == profiles["races"].to_list()
