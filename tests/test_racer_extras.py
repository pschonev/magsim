import polars as pl

from magsim.analysis.racer_extras import compute_racer_extras
from magsim.analysis.tables import build_summary_tables, with_racer_extras


def races() -> pl.DataFrame:
    """Twelve races on one board: 4, 5 and 6 players, long and short."""
    return pl.DataFrame(
        {
            "config_hash": [f"r{i}" for i in range(12)],
            "board": ["Standard"] * 12,
            "racer_count": [4] * 4 + [5] * 4 + [6] * 4,
            "total_turns": [20, 40, 20, 40] * 3,
        },
    )


def results() -> pl.DataFrame:
    """Big wins 'Climber' grows with player count and with game length; 'Plain' is constant."""
    rows = []
    for i, count in enumerate([4] * 4 + [5] * 4 + [6] * 4):
        long_game = i % 2 == 1
        climber = count - 4 + (2 if long_game else 0)
        rows.append((f"r{i}", "Climber", climber, False, 10 + i, 3))
        rows.append((f"r{i}", "Plain", 1, i % 4 == 0, 10 + i, 3))
        rows.append((f"r{i}", "Filler", 4 - climber if climber < 4 else 0, False, 10 + i, 3))
    return pl.DataFrame(
        rows,
        schema=["config_hash", "racer_name", "final_vp", "eliminated", "sum_dice_rolled", "rolling_turns"],
        orient="row",
    )


def extras() -> dict[str, dict[str, float]]:
    frame = compute_racer_extras(results(), races())
    return {row["racer_name"]: row for row in frame.to_dicts()}


def test_a_racer_that_gains_with_more_players_has_a_positive_player_count_preference() -> None:
    assert extras()["Climber"]["player_count_pref"] > 0.5


def test_a_racer_with_constant_results_has_no_preference() -> None:
    plain = extras()["Plain"]

    assert plain["player_count_pref"] < 0.5
    assert plain["game_length_pref"] <= 0.5


def test_a_racer_that_gains_in_long_games_has_a_positive_game_length_preference() -> None:
    assert extras()["Climber"]["game_length_pref"] > 0.3


def test_elimination_rate_is_the_share_of_races_the_racer_was_eliminated_in() -> None:
    assert extras()["Plain"]["elimination_rate"] == 0.25
    assert extras()["Climber"]["elimination_rate"] == 0.0


def test_tables_get_the_extra_columns_in_the_requested_places() -> None:
    racer_stats = pl.DataFrame(
        {
            name: [1.0, 2.0]
            for name in [
                "mean_vp", "consistency_score", "pct_1st", "pct_2nd", "avg_speed_raw", "avg_net_movement",
                "avg_active_turns_pct", "avg_pos_self", "avg_neg_self", "dice_sensitivity", "trigger_dependency",
                "start_pos_bias", "midgame_bias", "triggers_per_turn", "self_targets_per_turn",
                "own_turn_triggers_per_turn", "avg_pos_other", "avg_neg_other", "avg_race_volatility",
                "avg_race_tightness", "avg_game_duration", "avg_env_triggers", "avg_env_trip_rate",
            ]
        }
        | {"racer_name": ["Climber", "Plain"], "races_run": [6, 6]},
    )
    base = build_summary_tables(racer_stats)
    pull = pl.DataFrame({"racer_name": ["Climber", "Plain"], "others_trigger_ratio": [1.5, 1.0]})

    tables = with_racer_extras(base, pull, compute_racer_extras(results(), races()))

    assert tables["overview"].columns[-2:] == ["Avg Game Len", "# Races"]
    assert "Avg Game Len" not in tables["dynamics"].columns
    assert tables["dynamics"].columns[-2:] == ["Player Count Pref", "Game Length Pref"]
    assert tables["movement"].columns[-2:] == ["Abil +Other", "Abil -Other"]
    assert "Rolling Turns %" not in tables["movement"].columns
    assert tables["abilities"].columns[-5:] == [
        "Triggers Caused",
        "Rolling Turns %",
        "Eliminated %",
        "Extra VP When Active %",
        "Triggers When Behind",
    ]
    assert tables["overview"].columns[:3] == ["Racer", "Avg VP", "Swinginess"]
    assert tables["vp"].columns == ["Racer", "Avg VP", "Roll Sens %", "Going-First Bonus %", "Lead Bonus %"]
    assert base["overview"].columns[-1] == "# Races"
