"""Database models for simulation results."""

from __future__ import annotations

import datetime

from sqlmodel import JSON, Column, Field, SQLModel, String

# we can't put this into type checking block because SQLModel needs to use it
from magical_athlete_simulator.core.types import ErrorCode  # noqa: TC001


class Race(SQLModel, table=True):
    """
    Represents a single race simulation.
    Maps to races.parquet
    """

    __tablename__ = "races"  # pyright: ignore[reportAssignmentType, reportUnannotatedClassAttribute]

    # Primary Key
    config_hash: str = Field(primary_key=True)
    config_encoded: str

    # Configuration Details
    seed: int
    board: str
    racer_names: list[str] = Field(sa_column=Column(JSON))
    racer_count: int

    # Execution Metadata
    timestamp: float
    execution_time_ms: float
    error_code: ErrorCode | None = Field(sa_type=String)
    total_turns: int

    # Created at
    created_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.UTC),
    )

    # --- METRICS (Calculated from positions) ---
    tightness_score: float = 0.0
    volatility_score: float = 0.0


class RacerResult(SQLModel, table=True):
    """
    Represents the result of one racer in a specific race.
    """

    __tablename__ = "racer_results"  # pyright: ignore[reportAssignmentType, reportUnannotatedClassAttribute]

    # Composite Primary Key
    config_hash: str = Field(primary_key=True)
    racer_id: int = Field(primary_key=True)

    # Racer Identity
    racer_name: str

    # Results
    final_vp: int = 0
    turns_taken: int = 0
    recovery_turns: int = 0
    skipped_main_moves: int = 0  # Times I was skipped

    # 1. SELF-GENERATED MOVEMENT (The "Speed" Score)
    # Sum of:
    # - Physical moves (Scoocher)
    # - Dice Modifiers (Hare)
    # - Base Value Gain (Legs/Alchemist)
    ability_movement: float = 0.0

    # 2. MOVEMENT IMPACT (The "Control" Score)
    # Sum of:
    # - Pushing/Pulling/Blocking others
    # - Modifying others' dice
    movement_impact: float = 0.0

    # Raw Dice Stats (for calculating Re-roll value in frontend)
    sum_dice_rolled: int = 0  # Raw base values
    rolling_turns: int = 0  # Count of rolls

    # --------------------------------------------------------------------------

    # Abilities (Legacy / Detail counts)
    ability_trigger_count: int = 0
    ability_self_target_count: int = 0
    ability_target_count: int = 0

    # Status
    finish_position: int | None = None
    eliminated: bool = False

    # Ranking
    rank: int | None = None

    # Position relative to median at 66% of race duration
    midgame_relative_pos: float = 0.0


class RacePositionLog(SQLModel, table=True):
    """
    Log of board state at the end of each turn (flat format).
    One row per turn, with columns for each racer position.
    """

    __tablename__ = "race_position_logs"  # pyright: ignore[reportAssignmentType, reportUnannotatedClassAttribute]

    config_hash: str = Field(primary_key=True)
    turn_index: int = Field(primary_key=True)

    current_racer_id: int

    # Position columns (nullable for 4-racer games)
    pos_r0: int | None = None
    pos_r1: int | None = None
    pos_r2: int | None = None
    pos_r3: int | None = None
    pos_r4: int | None = None
    pos_r5: int | None = None
