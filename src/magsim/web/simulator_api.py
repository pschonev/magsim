"""Browser-agnostic interactive simulator facade over magsim's GameScenario."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, cast, get_args, override

import msgspec

from magsim.analysis.filters import get_automatic_racers
from magsim.core.events import (
    GameEvent,
    MoveCmdEvent,
    RacerEliminatedEvent,
    SimultaneousMoveCmdEvent,
    SimultaneousWarpCmdEvent,
    TripCmdEvent,
    TwistCardEvent,
    WarpCmdEvent,
)
from magsim.core.mixins import ApproachHookMixin
from magsim.web.colors import racer_color, racer_palette
from magsim.core.registry import RACER_ABILITIES
from magsim.core.state import GameRules
from magsim.core.types import (
    AbilityName,
    BoardModifierName,
    BoardName,
    RacerModifierName,
    RacerName,
    TwistName,
)
from magsim.engine.board import (
    BOARD_DEFINITIONS,
    MoveDeltaTile,
    SpaceModifier,
    TripTile,
    VictoryPointTile,
    WarpTile,
)
from magsim.engine.logging import TWIST_BANNER
from magsim.engine.scenario import GameScenario, RacerConfig
from magsim.engine.twist import TWIST_DECK
from magsim.simulation.config import GameConfig
from magsim.web.schemas import (
    BoardPieceDTO,
    BoardSnapshotDTO,
    ConfigEncodeResponseDTO,
    DecodedConfigDTO,
    LogEntryDTO,
    RacerPaletteDTO,
    RuleValueDTO,
    SimulationRequestDTO,
    SimulationResponseDTO,
    SimulatorMetaDTO,
    StepSnapshotDTO,
    TileModifierDTO,
)

if TYPE_CHECKING:
    from magsim.engine.board import Board
    from magsim.engine.game_engine import GameEngine

DEFAULT_RACERS: tuple[str, ...] = ("Banana", "Centaur", "Gunk", "Scoocher")
DEFAULT_BOARD = "Standard"
DEFAULT_SEED = 42

SNAPSHOT_EVENTS: tuple[type[GameEvent], ...] = (
    MoveCmdEvent,
    WarpCmdEvent,
    TripCmdEvent,
    SimultaneousMoveCmdEvent,
    SimultaneousWarpCmdEvent,
    RacerEliminatedEvent,
    TwistCardEvent,
)


class _StructuredLogCollector(logging.Handler):
    """In-memory logging handler capturing structured engine records without rich."""

    def __init__(self) -> None:
        super().__init__()
        self.entries: list[LogEntryDTO] = []

    @override
    def emit(self, record: logging.LogRecord) -> None:
        total_turn = int(getattr(record, "total_turn", 0))
        turn_log_count = int(getattr(record, "turn_log_count", 0))
        racer_repr = str(getattr(record, "racer_repr", "_"))
        engine_level = int(getattr(record, "engine_level", 0))
        engine_id = int(getattr(record, "engine_id", 0))
        prefix = f"{engine_level}:{engine_id} {total_turn}.{racer_repr}.{turn_log_count}"
        self.entries.append(
            LogEntryDTO(
                index=len(self.entries),
                turn=total_turn,
                level=record.levelname,
                prefix=prefix,
                message=record.getMessage(),
            ),
        )


def _serialize_tile_modifier(
    mod: SpaceModifier,
    *,
    dynamic: bool,
) -> TileModifierDTO:
    if isinstance(mod, MoveDeltaTile):
        return TileModifierDTO(
            kind="move_delta",
            name=mod.display_name,
            label=f"{mod.delta:+d}",
            dynamic=dynamic,
            delta=mod.delta,
            owner_idx=mod.owner_idx,
        )
    if isinstance(mod, WarpTile):
        return TileModifierDTO(
            kind="warp",
            name=mod.display_name,
            label=f"→{mod.target}",
            dynamic=dynamic,
            target=mod.target,
            owner_idx=mod.owner_idx,
        )
    if isinstance(mod, TripTile):
        return TileModifierDTO(
            kind="trip",
            name=mod.display_name,
            label="TRIP",
            dynamic=dynamic,
            owner_idx=mod.owner_idx,
        )
    if isinstance(mod, VictoryPointTile):
        return TileModifierDTO(
            kind="victory_point",
            name=mod.display_name,
            label=f"+{mod.amount} VP",
            dynamic=dynamic,
            vp_amount=mod.amount,
            consumable=mod.consumable,
            owner_idx=mod.owner_idx,
        )
    if isinstance(mod, ApproachHookMixin):
        return TileModifierDTO(
            kind="blocker",
            name=mod.display_name,
            label=mod.display_name,
            dynamic=dynamic,
            owner_idx=mod.owner_idx,
        )
    return TileModifierDTO(
        kind="other",
        name=mod.display_name,
        label=mod.display_name,
        dynamic=dynamic,
        owner_idx=mod.owner_idx,
    )


def _snapshot_board(board: Board) -> BoardSnapshotDTO:
    tiles: dict[str, list[TileModifierDTO]] = {}
    all_positions = sorted(
        set(board.static_features.keys()) | set(board.dynamic_modifiers.keys()),
    )
    for pos in all_positions:
        serialized: list[TileModifierDTO] = [
            _serialize_tile_modifier(mod, dynamic=False)
            for mod in board.static_features.get(pos, [])
        ]
        serialized.extend(
            _serialize_tile_modifier(mod, dynamic=True)
            for mod in board.dynamic_modifiers.get(pos, [])
        )
        if serialized:
            tiles[str(pos)] = serialized

    return BoardSnapshotDTO(
        length=board.length,
        first_corner=board.first_corner,
        second_turn=board.second_turn,
        twist_after_tile=board.twist_after_tile,
        twists=[str(t) for t in board.twists],
        tiles=tiles,
    )


def _extract_board_pieces(engine: GameEngine) -> list[BoardPieceDTO]:
    pieces: list[BoardPieceDTO] = []
    seen: set[tuple[str, int, int | None]] = set()
    for racer in engine.state.racers:
        for mod in racer.modifiers:
            pos = getattr(mod, "position", None)
            if isinstance(pos, int):
                name = getattr(mod, "name", type(mod).__name__)
                owner_idx = getattr(mod, "owner_idx", None)
                key = (name, pos, owner_idx if isinstance(owner_idx, int) else None)
                if key not in seen:
                    seen.add(key)
                    pieces.append(
                        BoardPieceDTO(
                            name=key[0],
                            position=key[1],
                            owner_idx=key[2],
                        ),
                    )
    return pieces


def _validate_racers(racers: list[str]) -> list[RacerName]:
    valid_racers = set(get_args(RacerName))
    unknown = [r for r in racers if r not in valid_racers]
    if unknown:
        msg = f"Unknown racer(s): {', '.join(unknown)}"
        raise ValueError(msg)
    if not racers:
        msg = "At least one racer is required."
        raise ValueError(msg)
    return cast("list[RacerName]", racers)


def _validate_board(board: str) -> BoardName:
    if board not in BOARD_DEFINITIONS:
        msg = f"Unknown board: {board}"
        raise ValueError(msg)
    return board


def _validate_twists(twists: list[str]) -> list[TwistName]:
    valid_twists = set(TWIST_DECK)
    unknown = [t for t in twists if t not in valid_twists]
    if unknown:
        msg = f"Unknown twist(s): {', '.join(unknown)}"
        raise ValueError(msg)
    return cast("list[TwistName]", twists)


def _build_game_config(req: SimulationRequestDTO) -> GameConfig:
    racers = _validate_racers(req.racers)
    board = _validate_board(req.board)
    exclude_twists = _validate_twists(req.exclude_twists)
    forced_twists = _validate_twists(req.forced_twists)
    return GameConfig(
        racers=tuple(racers),
        board=board,
        seed=req.seed,
        rules=dict(req.rules),
        exclude_twists=tuple(exclude_twists),
        forced_twists=tuple(forced_twists),
    )


def _palettes(names: list[str]) -> dict[str, RacerPaletteDTO]:
    palettes = {name: racer_palette(name) for name in names}
    return {
        name: RacerPaletteDTO(p.primary, p.secondary, p.outline)
        for name, p in palettes.items()
    }


def get_simulator_meta() -> SimulatorMetaDTO:
    """Return static engine registries, colors, and defaults for the simulator UI."""
    racers = sorted(str(r) for r in get_args(RacerName))
    boards = [str(b) for b in BOARD_DEFINITIONS]
    twists = [str(t) for t in TWIST_DECK]
    auto_set = get_automatic_racers()
    automatic_racers = [r for r in racers if r in auto_set]
    racer_abilities = {
        str(racer): [str(ab) for ab in abilities]
        for racer, abilities in RACER_ABILITIES.items()
    }
    return SimulatorMetaDTO(
        racers=racers,
        boards=boards,
        twists=twists,
        automatic_racers=automatic_racers,
        racer_colors={r: racer_color(r) for r in racers},
        racer_palettes=_palettes(racers),
        racer_abilities=racer_abilities,
        ability_names=sorted(str(a) for a in get_args(AbilityName)),
        racer_modifier_names=sorted(str(m) for m in get_args(RacerModifierName)),
        board_modifier_names=sorted(str(b) for b in get_args(BoardModifierName)),
        twist_banner=TWIST_BANNER,
        default_racers=list(DEFAULT_RACERS),
        default_board=DEFAULT_BOARD,
        default_seed=DEFAULT_SEED,
    )


def encode_config(req: SimulationRequestDTO) -> ConfigEncodeResponseDTO:
    """Encode a simulation request into a shareable config string and hash."""
    config = _build_game_config(req)
    return ConfigEncodeResponseDTO(
        encoded=config.encoded,
        config_hash=config.compute_hash(),
    )


def decode_config(encoded: str) -> DecodedConfigDTO:
    """Decode a shareable config string into structured simulation parameters."""
    config = GameConfig.from_encoded(encoded.strip())
    rules: dict[str, RuleValueDTO] = {
        k: v
        for k, v in config.rules.items()
        if isinstance(v, (int, float, str, bool))
    }
    return DecodedConfigDTO(
        racers=[str(r) for r in config.racers],
        board=str(config.board),
        seed=config.seed,
        rules=rules,
        exclude_twists=[str(t) for t in config.exclude_twists],
        forced_twists=[str(t) for t in config.forced_twists],
        encoded=config.encoded,
        config_hash=config.compute_hash(),
    )


def run_simulation(req: SimulationRequestDTO) -> SimulationResponseDTO:
    """Execute a race simulation and return deduplicated board states, steps, and logs."""
    try:
        config = _build_game_config(req)
    except ValueError as exc:
        return SimulationResponseDTO(
            encoded_config="",
            config_hash="",
            board_name=req.board,
            seed=req.seed,
            total_turns=0,
            racer_names=list(req.racers),
            racer_colors={r: racer_color(r) for r in req.racers},
            racer_palettes=_palettes(req.racers),
            board_states=[],
            steps=[],
            turn_map={},
            logs=[],
            error=str(exc),
        )

    board = BOARD_DEFINITIONS[config.board]()
    board.banned_twists = frozenset(config.exclude_twists)
    board.forced_twists = list(config.forced_twists)

    racer_configs: list[RacerConfig] = []
    for idx, racer_name in enumerate(config.racers):
        start_pos = 0
        if req.start_positions is not None and idx < len(req.start_positions):
            start_pos = req.start_positions[idx]
        racer_configs.append(
            RacerConfig(idx, racer_name, start_pos=start_pos),
        )

    base_logger = logging.getLogger("magical_athlete")
    prev_level = base_logger.level
    prev_propagate = base_logger.propagate
    collector = _StructuredLogCollector()
    base_logger.addHandler(collector)
    base_logger.setLevel(logging.DEBUG if req.debug_mode else logging.INFO)
    base_logger.propagate = False

    board_states: list[BoardSnapshotDTO] = []
    board_state_keys: dict[bytes, int] = {}
    steps: list[StepSnapshotDTO] = []
    turn_map: dict[int, list[int]] = {}
    last_log_cursor = 0
    error_message: str | None = None

    def get_board_state_idx(current_board: Board) -> int:
        snap = _snapshot_board(current_board)
        key = msgspec.json.encode(snap)
        existing = board_state_keys.get(key)
        if existing is not None:
            return existing
        new_idx = len(board_states)
        board_states.append(snap)
        board_state_keys[key] = new_idx
        return new_idx

    def record_snapshot(
        eng: GameEngine,
        turn_idx: int,
        event_name: str,
        *,
        override_racer: int | None = None,
        override_roll: int | None = None,
        skipped_roll: bool = False,
    ) -> None:
        nonlocal last_log_cursor
        step_idx = len(steps)
        turn_map.setdefault(turn_idx, []).append(step_idx)

        raw_roll = eng.state.roll_state.final_value
        effective_roll = override_roll if override_roll is not None else raw_roll

        log_end = len(collector.entries)
        log_start = last_log_cursor
        last_log_cursor = log_end

        steps.append(
            StepSnapshotDTO(
                global_step_index=step_idx,
                turn_index=turn_idx,
                event_name=event_name,
                positions=[r.position for r in eng.state.racers],
                tripped=[r.tripped for r in eng.state.racers],
                eliminated=[r.eliminated for r in eng.state.racers],
                sidelined=[r.sidelined for r in eng.state.racers],
                finish_positions=[r.finish_position for r in eng.state.racers],
                vp=[r.victory_points for r in eng.state.racers],
                last_roll=effective_roll,
                current_racer=(
                    override_racer
                    if override_racer is not None
                    else eng.state.current_racer_idx
                ),
                names=[str(r.name) for r in eng.state.racers],
                modifiers=[
                    [getattr(m, "name", type(m).__name__) for m in r.modifiers]
                    for r in eng.state.racers
                ],
                abilities=[
                    [str(a.name) for a in r.active_abilities]
                    for r in eng.state.racers
                ],
                skipped_roll=skipped_roll,
                board_state_idx=get_board_state_idx(eng.state.board),
                pieces=_extract_board_pieces(eng),
                log_start_index=log_start,
                log_end_index=log_end,
            ),
        )

    try:
        scenario = GameScenario(
            racers_config=racer_configs,
            dice_rolls=req.dice_rolls,
            seed=config.seed,
            board=board,
            rules=GameRules.for_play(config.rules),
        )
        engine = scenario.engine
        for racer, vp in zip(engine.state.racers, req.start_vps or [], strict=False):
            racer.victory_points = vp
            racer.starting_vp = vp
        current_turn_ref = [0]

        def on_event(eng: GameEngine, event: GameEvent) -> None:
            if isinstance(event, SNAPSHOT_EVENTS):
                record_snapshot(eng, current_turn_ref[0], type(event).__name__)

        engine.on_event_processed = on_event

        record_snapshot(engine, 0, "InitialState", override_racer=-1, override_roll=0)

        max_snapshots = max(1, req.max_steps)
        step_counter = 0
        while engine.state.race_active:
            step_counter += 1
            current_turn_ref[0] = step_counter
            actual_racer_idx = engine.state.current_racer_idx
            steps_before = len(steps)

            scenario.run_turn()

            post_turn_serial = engine.state.roll_state.serial_id
            roll_was_skipped = post_turn_serial == 0

            if len(steps) == steps_before:
                record_snapshot(
                    engine,
                    step_counter,
                    "TurnSkipped/Recovery",
                    override_racer=actual_racer_idx,
                    override_roll=0 if roll_was_skipped else None,
                    skipped_roll=roll_was_skipped,
                )
            else:
                last_snap = steps[-1]
                last_log_cursor = len(collector.entries)
                steps[-1] = StepSnapshotDTO(
                    global_step_index=last_snap.global_step_index,
                    turn_index=last_snap.turn_index,
                    event_name=last_snap.event_name,
                    positions=last_snap.positions,
                    tripped=last_snap.tripped,
                    eliminated=last_snap.eliminated,
                    sidelined=last_snap.sidelined,
                    finish_positions=last_snap.finish_positions,
                    vp=last_snap.vp,
                    last_roll=0 if roll_was_skipped else last_snap.last_roll,
                    current_racer=actual_racer_idx,
                    names=last_snap.names,
                    modifiers=last_snap.modifiers,
                    abilities=last_snap.abilities,
                    skipped_roll=roll_was_skipped,
                    board_state_idx=get_board_state_idx(engine.state.board),
                    pieces=_extract_board_pieces(engine),
                    log_start_index=last_snap.log_start_index,
                    log_end_index=last_snap.log_end_index,
                )

            if len(steps) > max_snapshots:
                break

        record_snapshot(engine, current_turn_ref[0], "RaceComplete")
        total_turns = step_counter
    except Exception as exc:  # noqa: BLE001
        error_message = str(exc)
        total_turns = len(turn_map)
    finally:
        base_logger.removeHandler(collector)
        base_logger.setLevel(prev_level)
        base_logger.propagate = prev_propagate

    racer_names = [str(r) for r in config.racers]
    return SimulationResponseDTO(
        encoded_config=config.encoded,
        config_hash=config.compute_hash(),
        board_name=str(config.board),
        seed=config.seed,
        total_turns=total_turns,
        racer_names=racer_names,
        racer_colors={r: racer_color(r) for r in racer_names},
        racer_palettes=_palettes(racer_names),
        board_states=board_states,
        steps=steps,
        turn_map={str(k): v for k, v in turn_map.items()},
        logs=collector.entries,
        error=error_message,
    )


def get_simulator_meta_json() -> str:
    """Return SimulatorMetaDTO serialized as JSON."""
    return msgspec.json.encode(get_simulator_meta()).decode("utf-8")


def encode_config_json(request_json: str | bytes) -> str:
    """Decode SimulationRequestDTO JSON and return ConfigEncodeResponseDTO JSON."""
    req = msgspec.json.decode(request_json, type=SimulationRequestDTO)
    return msgspec.json.encode(encode_config(req)).decode("utf-8")


def decode_config_json(encoded: str) -> str:
    """Decode a config string and return DecodedConfigDTO JSON."""
    return msgspec.json.encode(decode_config(encoded)).decode("utf-8")


def run_simulation_json(request_json: str | bytes) -> str:
    """Decode SimulationRequestDTO JSON and return SimulationResponseDTO JSON."""
    req = msgspec.json.decode(request_json, type=SimulationRequestDTO)
    return msgspec.json.encode(run_simulation(req)).decode("utf-8")
