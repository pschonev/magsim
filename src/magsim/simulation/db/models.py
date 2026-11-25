from __future__ import annotations

import datetime
from typing import ClassVar

import msgspec


class Race(msgspec.Struct, array_like=True, gc=False):
    """
    Represents a single race simulation.
    Maps to races.parquet.
    Uses array_like=True for tuple serialization (fastest DB insert).
    """

    table_name: ClassVar[str] = "races"

    # --- Primary Key ---
    config_hash: str
    config_encoded: str

    # --- Configuration Details ---
    seed: int
    board: str
    racer_names: list[str]
    racer_count: int

    # --- Execution Metadata ---
    timestamp: float
    execution_time_ms: float
    error_code: str | None = None  # Msgspec handles Optional types natively
    total_turns: int = 0
    turns_on_winning_round: int | None = None

    # --- Created At ---
    created_at: datetime.datetime = msgspec.field(
        default_factory=lambda: datetime.datetime.now(datetime.UTC),
    )

    # --- METRICS (Calculated from positions) ---
    tightness_score: float = 0.0
    volatility_score: float = 0.0

    # --- Twist cards in resolution order (empty if none drawn) ---
    twists: list[str] = msgspec.field(default_factory=list)

    @classmethod
    def get_create_sql(cls) -> str:
        """
        Generate SQL matching the exact field order.
        """
        return """
        CREATE TABLE IF NOT EXISTS races (
            config_hash VARCHAR PRIMARY KEY,
            config_encoded VARCHAR,
            seed BIGINT,
            board VARCHAR,
            racer_names VARCHAR[],
            racer_count BIGINT,
            timestamp DOUBLE,
            execution_time_ms DOUBLE,
            error_code VARCHAR,
            total_turns BIGINT,
            turns_on_winning_round BIGINT,
            created_at TIMESTAMP,
            tightness_score DOUBLE,
            volatility_score DOUBLE,
            twists VARCHAR[]
        )
        """


FACE_COLUMNS: tuple[str, ...] = tuple(f"rolled_{face}" for face in range(1, 7))
# Columns added after the first batches: name -> SQL type (an older table gets them appended)
LATE_COLUMNS: dict[str, str] = {
    **dict.fromkeys(FACE_COLUMNS, "BIGINT"),
    "avg_rank_frac": "DOUBLE",
    "turns_started_last": "BIGINT",
    "turns_started_ahead": "BIGINT",
    "hotel_stops": "BIGINT",
    "eliminated_by": "BIGINT",
    "main_roll_totals": "INTEGER[]",
    "predicted_racer_id": "BIGINT",
    "copied_racers": "VARCHAR[]",
    "guessed_rolls": "INTEGER[]",
    **{f"dice_{face}": "BIGINT" for face in range(1, 7)},
}


class RacerResult(msgspec.Struct, array_like=True, gc=False):
    """
    Represents the result of one racer in a specific race.
    """

    table_name: ClassVar[str] = "racer_results"

    # --- Composite Primary Key ---
    config_hash: str
    racer_id: int

    # --- Racer Identity ---
    racer_name: str

    # --- Results ---
    final_vp: int = 0
    turns_taken: int = 0
    recovery_turns: int = 0
    skipped_main_moves: int = 0  # Times I was skipped

    # --- 1. Self-Movement (The "Speed" Score) ---
    pos_self_ability_movement: float = 0.0
    neg_self_ability_movement: float = 0.0
    skipped_self_main_move: float = 0.0

    # --- 2. Moving Others (The "Control" Score) ---
    pos_other_ability_movement: float = 0.0
    neg_other_ability_movement: float = 0.0
    skipped_other_main_move: float = 0.0  # time I skipped someone else

    # --- Raw Dice Stats ---
    sum_dice_rolled: int = 0
    rolling_turns: int = 0

    # --- Abilities ---
    ability_trigger_count: int = 0
    ability_self_target_count: int = 0
    ability_own_turn_count: int = 0

    # --- Status ---
    finish_position: int | None = None
    eliminated: bool = False

    # --- Metrics ---
    midgame_relative_pos: float = 0.0

    # --- Main-roll face counts (appended last: tables are filled by position) ---
    rolled_1: int = 0
    rolled_2: int = 0
    rolled_3: int = 0
    rolled_4: int = 0
    rolled_5: int = 0
    rolled_6: int = 0
    avg_rank_frac: float | None = None  # mean rank over the race, 0 = leading, 1 = last
    turns_started_last: int | None = None  # own turns that began in last place
    turns_started_ahead: int | None = None  # own turns that began anywhere else
    hotel_stops: int | None = None  # times the racer stopped on Hotel's space
    eliminated_by: int | None = None  # racer_id whose turn it was when this racer was eliminated
    main_roll_totals: list[int] | None = None  # final main roll of each turn, only for TOTAL_TRACKED racers
    predicted_racer_id: int | None = None  # racer_id Mastermind predicted to win
    copied_racers: list[str] | None = None  # racers whose powers Mush drew
    guessed_rolls: list[int] | None = None  # numbers Cheatah set that were guessed
    # Every die the racer rolled for any reason (rerolls, duels, extra dice), not only the kept main roll
    dice_1: int = 0
    dice_2: int = 0
    dice_3: int = 0
    dice_4: int = 0
    dice_5: int = 0
    dice_6: int = 0

    @classmethod
    def get_create_sql(cls) -> str:
        return """
        CREATE TABLE IF NOT EXISTS racer_results (
            config_hash VARCHAR,
            racer_id BIGINT,
            racer_name VARCHAR,
            final_vp BIGINT,
            turns_taken BIGINT,
            recovery_turns BIGINT,
            skipped_main_moves BIGINT,
            pos_self_ability_movement DOUBLE,
            neg_self_ability_movement DOUBLE,
            skipped_self_main_move DOUBLE,
            pos_other_ability_movement DOUBLE,
            neg_other_ability_movement DOUBLE,
            skipped_other_main_move DOUBLE,
            sum_dice_rolled BIGINT,
            rolling_turns BIGINT,
            ability_trigger_count BIGINT,
            ability_self_target_count BIGINT,
            ability_own_turn_count BIGINT,
            finish_position BIGINT,
            eliminated BOOLEAN,
            midgame_relative_pos DOUBLE,
            rolled_1 BIGINT,
            rolled_2 BIGINT,
            rolled_3 BIGINT,
            rolled_4 BIGINT,
            rolled_5 BIGINT,
            rolled_6 BIGINT,
            avg_rank_frac DOUBLE,
            turns_started_last BIGINT,
            turns_started_ahead BIGINT,
            hotel_stops BIGINT,
            eliminated_by BIGINT,
            main_roll_totals INTEGER[],
            predicted_racer_id BIGINT,
            copied_racers VARCHAR[],
            guessed_rolls INTEGER[],
            dice_1 BIGINT,
            dice_2 BIGINT,
            dice_3 BIGINT,
            dice_4 BIGINT,
            dice_5 BIGINT,
            dice_6 BIGINT,
            PRIMARY KEY (config_hash, racer_id)
        )
        """


# Helper for the position logs table (which is inserted via Arrow, not Structs)
class RacePositionLogHelper:
    table_name: ClassVar[str] = "race_position_logs"

    @classmethod
    def get_create_sql(cls) -> str:
        return """
        CREATE TABLE IF NOT EXISTS race_position_logs (
            config_hash VARCHAR,
            turn_index BIGINT,
            current_racer_id BIGINT,
            pos_r0 BIGINT,
            pos_r1 BIGINT,
            pos_r2 BIGINT,
            pos_r3 BIGINT,
            pos_r4 BIGINT,
            pos_r5 BIGINT,
            PRIMARY KEY (config_hash, turn_index)
        )
        """
