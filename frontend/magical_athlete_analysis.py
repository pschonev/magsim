# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "altair==6.0.0",
#     "marimo>=0.19.0",
#     "numpy>=2.4.1"
# ]
# [tool.marimo.display]
# theme = "dark"
# ///

import marimo

__generated_with = "0.18.4"
app = marimo.App(
    width="full",
    app_title="Magical Athlete Simulator",
    css_file="docs/magical_athlete_analysis.css",
)


@app.cell
def _():
    import sys

    print(sys.version)
    return


@app.cell
async def cell_import():
    from __future__ import annotations

    import dataclasses
    import logging
    import math
    import re
    from typing import Any, Literal, get_args

    import altair as alt
    import marimo as mo
    import micropip
    import numpy as np
    from rich.console import Console
    from rich.logging import RichHandler

    MAGSIM_VERSION = "1.0.1"
    await micropip.install(
        f"magsim=={MAGSIM_VERSION}",
        keep_going=True,
    )

    from magsim.core.events import (
        MoveCmdEvent,
        TripCmdEvent,
        WarpCmdEvent,
    )
    from magsim.core.palettes import (
        get_racer_color,
        get_racer_palette,
    )
    from magsim.core.types import RacerName
    from magsim.engine.board import (
        BOARD_DEFINITIONS,
        MoveDeltaTile,
        TripTile,
        VictoryPointTile,
    )
    from magsim.engine.logging import (
        GameLogHighlighter,
        RichMarkupFormatter,
    )

    # Imports
    from magsim.engine.scenario import GameScenario, RacerConfig
    from magsim.simulation.telemetry import StepSnapshot
    from magsim.simulation.config import GameConfig

    return (
        Any,
        BOARD_DEFINITIONS,
        Console,
        GameConfig,
        GameLogHighlighter,
        GameScenario,
        Literal,
        MAGSIM_VERSION,
        MoveCmdEvent,
        MoveDeltaTile,
        RacerConfig,
        RacerName,
        RichHandler,
        RichMarkupFormatter,
        StepSnapshot,
        TripCmdEvent,
        TripTile,
        VictoryPointTile,
        WarpCmdEvent,
        alt,
        dataclasses,
        get_args,
        get_racer_color,
        get_racer_palette,
        logging,
        math,
        mo,
        np,
        re,
    )


@app.cell
def cell_file_browser(mo):
    from pathlib import Path

    import polars as pl

    reload_data_btn = mo.ui.button(label="⟳ Reload Data")

    # 1. Get location and check type
    notebook_loc = mo.notebook_location()
    is_url = isinstance(notebook_loc, mo._runtime.runtime.URLPath)

    default_results_path = (
        notebook_loc / "results" if is_url else notebook_loc / ".." / "results"
    )

    if is_url:
        # If running via URL (e.g. WASM), we can't use a local file browser
        results_folder_browser = None
        print(f"Running in URL mode. Base: {default_results_path}")
    else:
        # If local, create the browser
        # Ensure we convert Path to string for the widget
        results_folder_browser = mo.ui.file_browser(
            selection_mode="directory",
            label="Select Results Folder",
            initial_path=str(default_results_path),
        )
        print(f"Running locally. Default results path: {default_results_path}")
    return (
        Path,
        default_results_path,
        is_url,
        pl,
        reload_data_btn,
        results_folder_browser,
    )


@app.cell
def cell_load_data(
    Path,
    default_results_path,
    is_url,
    pl,
    reload_data_btn,
    results_folder_browser,
):
    reload_data_btn.value

    # 1. Determine the Base Folder
    if is_url:
        base_folder = default_results_path
    else:
        if results_folder_browser.value:
            base_folder = Path(results_folder_browser.value[0].path)
        else:
            base_folder = Path("results")

    # 2. Construct Paths (Only need Races and Results now)
    path_races = base_folder / "races.parquet"
    path_res = base_folder / "racer_results.parquet"

    # 3. Load Data
    try:
        if not is_url:  # noqa: SIM102
            if not Path(path_races).exists() or not Path(path_res).exists():
                raise FileNotFoundError(
                    f"Folder '{base_folder}' must contain 'races.parquet' and 'racer_results.parquet'",
                )

        if is_url:
            import io
            import urllib.request

            def _wasm_read_parquet(path: Path) -> pl.DataFrame:
                with urllib.request.urlopen(path) as response:
                    parquet_bytes = response.read()
                return pl.read_parquet(io.BytesIO(parquet_bytes), use_pyarrow=True)

            df_racer_results = _wasm_read_parquet(path_res)
            df_races = _wasm_read_parquet(path_races)
        else:
            df_racer_results = pl.read_parquet(path_res)
            df_races = pl.read_parquet(path_races)

        load_status = f"✅ Loaded from: `{base_folder}`"

    except Exception as e:
        df_racer_results = pl.DataFrame()
        df_races = pl.DataFrame()
        load_status = f"❌ Error: {e!s}"
        print(load_status)

    print(f"df_races: {df_races.height} rows, columns: {df_races.columns}")
    print(
        f"df_racer_results: {df_racer_results.height} rows, columns: {df_racer_results.columns}",
    )
    return df_racer_results, df_races, load_status


@app.cell
def cell_display_data(df_racer_results, df_races, mo, pl):
    import json  # Required for the WASM fix

    HASH_COL = "config_hash"

    # 1. Get unique racers for column headers
    unique_racers = sorted(df_racer_results.get_column("racer_name").unique().to_list())

    # 2. FIX DATA TYPE: Decode JSON -> List (WASM Compatible)
    df_races_clean = df_races.with_columns(
        pl.col("racer_names").cast(pl.List(pl.Utf8)).alias("racer_names")
    )

    # 3. EXPAND: Create Display & Boolean Columns
    exprs = [
        # Readable string for searching
        pl.col("racer_names").list.join(", ").alias("roster_display"),
    ]
    for r in unique_racers:
        exprs.append(pl.col("racer_names").list.contains(r).alias(f"Has {r}"))

    df_races_expanded = df_races_clean.with_columns(exprs)

    # 4. DEFINE COLUMN GROUPS

    # A. Priority Columns (Frozen on left)
    priority_cols = [
        "roster_display",
        "board",
        "racer_count",
        "seed",
        "error_code",
        "total_turns",
    ]

    # B. Matrix Columns (The boolean flags)
    matrix_cols = [f"Has {r}" for r in unique_racers]

    # C. Columns to Hide/Drop explicitly
    drop_cols = ["timestamp"]  # Redundant with created_at

    # D. "The Rest" - Calculate dynamically
    other_cols = [
        c
        for c in df_races_expanded.columns
        if c not in priority_cols and c not in matrix_cols and c not in drop_cols
    ]

    racer_results_table = mo.ui.table(
        df_racer_results.sort(["config_hash", "racer_id"]).select(
            pl.all().exclude(HASH_COL),
            pl.col(HASH_COL),
        ),
        selection="single",
        label="Racer Results",
    )

    races_table = mo.ui.table(
        df_races_expanded.select(priority_cols + matrix_cols + other_cols),
        selection="single",
        label="Races (Matrix View)",
        freeze_columns_left=priority_cols,
    )
    return df_races_clean, racer_results_table, races_table


@app.cell
def cell_visual_setup(math):
    BG_COLOR = "#181c1a"

    # --- CONSTANTS: BOARD THEME ---
    BOARD_THEME = {
        "background": BG_COLOR,
        "tile_1": "#2d3432",
        "tile_2": "#363e3b",
        "stroke_default": "#555",
        "text_default": "#aaa",
        # Special Tiles
        "start_fill": "#4CAF50",
        "start_text": "#4CAF50",
        "start_stroke": "#D3D3D3",  # [NEW] Light Grey
        "goal_fill": "#F44336",
        "goal_text": "#F44336",
        "goal_stroke": "#C5A059",  # [NEW] Muted Golden
        "trip_fill": "#111111",
        "trip_text": "#F44336",
        "vp_fill": "#81D4FA",
        "vp_text": "#000000",
        "move_pos_fill": "#A5D6A7",
        "move_pos_text": "#1B5E20",
        "move_neg_fill": "#EF9A9A",
        "move_neg_text": "#B71C1C",
    }

    def generate_racetrack_positions(
        num_spaces,
        start_x,
        start_y,
        straight_len,
        radius,
    ):
        """
        Generates a Clockwise stadium track starting from the Top-Left straight.
        """
        positions = []
        perimeter = (2 * straight_len) + (2 * math.pi * radius)
        step_distance = perimeter / num_spaces

        right_circle_cx = start_x + straight_len
        right_circle_cy = start_y + radius
        left_circle_cx = start_x
        left_circle_cy = start_y + radius

        for i in range(num_spaces):
            dist = i * step_distance

            # 1. Top Straight (Moving Right)
            if dist < straight_len:
                x = start_x + dist
                y = start_y
                angle = 0
            # 2. Right Curve (Moving Clockwise/Down)
            elif dist < (straight_len + math.pi * radius):
                arc_dist = dist - straight_len
                fraction = arc_dist / (math.pi * radius)
                theta = (-math.pi / 2) + (fraction * math.pi)
                x = right_circle_cx + radius * math.cos(theta)
                y = right_circle_cy + radius * math.sin(theta)
                angle = math.degrees(theta) + 90
            # 3. Bottom Straight (Moving Left)
            elif dist < (2 * straight_len + math.pi * radius):
                top_dist = dist - (straight_len + math.pi * radius)
                x = (start_x + straight_len) - top_dist
                y = start_y + (2 * radius)
                angle = 180
            # 4. Left Curve (Moving Clockwise/Up)
            else:
                arc_dist = dist - (2 * straight_len + math.pi * radius)
                fraction = arc_dist / (math.pi * radius)
                theta = (math.pi / 2) + (fraction * math.pi)
                x = left_circle_cx + radius * math.cos(theta)
                y = left_circle_cy + radius * math.sin(theta)
                angle = math.degrees(theta) + 90

            positions.append((x, y, angle))

        return positions

    # Constants
    NUM_TILES = 31
    board_positions = generate_racetrack_positions(NUM_TILES, 120, 150, 350, 100)
    return BG_COLOR, BOARD_THEME, board_positions


@app.cell
def cell_manage_state(mo):
    # --- PERSISTENCE STATE ---
    # We only use this to remember values when the UI refreshes (Add/Remove).
    get_selected_racers, set_selected_racers = mo.state(
        ["Magician", "PartyAnimal", "Egg", "ThirdWheel", "Leaptoad", "Hypnotist"],
        allow_self_loops=True,
    )
    get_racer_to_add, set_racer_to_add = mo.state(None, allow_self_loops=True)

    get_saved_positions, set_saved_positions = mo.state(
        {
            "Magician": 0,
            "PartyAnimal": 0,
            "Egg": 0,
            "ThirdWheel": 0,
            "Leaptoad": 0,
            "Hypnotist": 0,
        },
        allow_self_loops=True,
    )

    get_use_scripted_dice, set_use_scripted_dice = mo.state(
        False,
        allow_self_loops=False,
    )
    get_dice_rolls_text, set_dice_rolls_text = mo.state("", allow_self_loops=False)

    get_debug_mode, set_debug_mode = mo.state(False, allow_self_loops=True)

    # --- NEW STATES FOR CONFIG LOADING ---
    get_seed, set_seed = mo.state(42, allow_self_loops=True)
    get_board, set_board = mo.state("Standard", allow_self_loops=True)

    # Track the last seen selection for EACH table to prevent fighting/loops
    get_last_race_hash, set_last_race_hash = mo.state(None, allow_self_loops=True)
    get_last_result_hash, set_last_result_hash = mo.state(None, allow_self_loops=True)
    return (
        get_board,
        get_debug_mode,
        get_dice_rolls_text,
        get_last_race_hash,
        get_last_result_hash,
        get_racer_to_add,
        get_saved_positions,
        get_seed,
        get_selected_racers,
        get_use_scripted_dice,
        set_board,
        set_debug_mode,
        set_dice_rolls_text,
        set_last_race_hash,
        set_last_result_hash,
        set_racer_to_add,
        set_saved_positions,
        set_seed,
        set_selected_racers,
        set_use_scripted_dice,
    )


@app.cell
def cell_config_ui(
    BOARD_DEFINITIONS,
    GameConfig,
    RacerName,
    get_args,
    get_board,
    get_debug_mode,
    get_dice_rolls_text,
    get_racer_to_add,
    get_saved_positions,
    get_seed,
    get_selected_racers,
    get_use_scripted_dice,
    mo,
    set_board,
    set_debug_mode,
    set_dice_rolls_text,
    set_racer_to_add,
    set_saved_positions,
    set_seed,
    set_selected_racers,
    set_step_idx,
    set_use_scripted_dice,
):
    # --- UI DEFINITION ---
    AVAILABLE_RACERS = sorted(list(get_args(RacerName)))
    current_roster = get_selected_racers()
    saved_positions = get_saved_positions()

    # 1. Main Controls
    reset_button = mo.ui.button(
        label="⟳Reset",
        on_click=lambda _: set_step_idx(0),
    )

    def manual_change(setter, value):
        setter(value)
        set_step_idx(0)
        return value

    scenario_seed = mo.ui.number(
        start=0,
        stop=10000,
        value=get_seed(),
        label="Random Seed",
        on_change=lambda v: manual_change(set_seed, v),
    )

    board_selector = mo.ui.dropdown(
        options=sorted(list(BOARD_DEFINITIONS.keys())),
        value=get_board(),
        label="Board Map",
        on_change=lambda v: manual_change(set_board, v),
    )

    use_scripted_dice_ui = mo.ui.switch(
        value=get_use_scripted_dice(),
        on_change=lambda v: (set_use_scripted_dice(v), set_step_idx(0))[1],
        label="Use scripted dice",
    )
    dice_rolls_text_ui = mo.ui.text(
        value=get_dice_rolls_text(),
        on_change=lambda v: (set_dice_rolls_text(v), set_step_idx(0))[1],
        label="Dice rolls",
        placeholder="e.g. 4,5,6",
    )
    debug_mode_ui = mo.ui.switch(
        value=get_debug_mode(),
        on_change=set_debug_mode,
        label="Debug logging",
    )

    # --- NEW: Share & Load Logic ---
    encoded_config_input = mo.ui.text(
        label="Paste Encoded Config",
        placeholder="eyJ...",
        full_width=True,
    )

    def _on_load_click(_):
        """Parse encoded string using the existing class and update UI state."""
        val = encoded_config_input.value
        if not val:
            return

        try:
            # 1. Decode using your existing Single Source of Truth
            config = GameConfig.from_encoded(val)

            # 2. Update the Shared State directly
            set_seed(config.seed)
            set_board(config.board)
            set_selected_racers(list(config.racers))
            set_saved_positions(dict.fromkeys(config.racers, 0))
            set_use_scripted_dice(False)
            set_step_idx(0)  # Reset simulation
        except Exception:
            pass

    load_encoded_btn = mo.ui.button(label="Load Configuration", on_click=_on_load_click)

    # 2. Position Inputs & Logic
    def _make_pos_on_change(racer_name):
        def _on_change(new_val):
            try:
                v = int(new_val)
            except Exception:
                v = 0
            set_saved_positions(lambda cur: {**cur, racer_name: v})
            set_step_idx(0)

        return _on_change

    pos_widget_map = {
        ui_racer: mo.ui.number(
            start=0,
            stop=29,
            value=int(saved_positions.get(ui_racer, 0)),
            label="",
            on_change=_make_pos_on_change(ui_racer),
        )
        for ui_racer in current_roster
    }

    # 3. Snapshot Logic
    def _snapshot_values(exclude=None):
        return {r: w.value for r, w in pos_widget_map.items() if r != exclude}

    # --- REORDERING LOGIC ---
    def move_racer(index, direction):
        def _move(_):
            roster = list(get_selected_racers())
            new_index = index + direction
            if 0 <= new_index < len(roster):
                roster[index], roster[new_index] = roster[new_index], roster[index]
                set_selected_racers(roster)
                set_step_idx(0)

        return _move

    # 4. Action Buttons
    action_buttons = {}
    for i, ui_racer in enumerate(current_roster):
        btn_remove = mo.ui.button(
            label="✖",
            on_click=lambda _, r=ui_racer: (
                set_saved_positions(_snapshot_values(exclude=r)),
                set_selected_racers(lambda cur: [x for x in cur if x != r]),
                set_step_idx(0),
            ),
            disabled=(len(current_roster) <= 1),
        )
        btn_up = mo.ui.button(label="↑", on_click=move_racer(i, -1), disabled=(i == 0))
        btn_down = mo.ui.button(
            label="↓",
            on_click=move_racer(i, 1),
            disabled=(i == len(current_roster) - 1),
        )
        action_buttons[ui_racer] = (btn_remove, btn_up, btn_down)

    # 5. Add Racer Logic
    available_options = [r for r in AVAILABLE_RACERS if r not in current_roster]
    add_racer_dropdown = mo.ui.dropdown(
        options=available_options,
        value=get_racer_to_add(),
        on_change=set_racer_to_add,
        label="Add racer",
    )

    def _add_racer(v):
        r = get_racer_to_add()
        if r and r not in get_selected_racers():
            new_pos = _snapshot_values()
            new_pos[r] = 0
            set_saved_positions(new_pos)
            set_selected_racers(lambda cur: cur + [r])
            set_racer_to_add(None)
            set_step_idx(0)
        return v

    add_button = mo.ui.button(label="Add", on_click=_add_racer)

    # 6. Layout Table
    table_rows = []
    for i, ui_racer in enumerate(current_roster):
        w_pos = pos_widget_map[ui_racer]
        b_rem, b_up, b_down = action_buttons[ui_racer]
        move_grp = mo.hstack([b_up, b_down], justify="center", gap=0)
        table_rows.append(f"| {i + 1}. {ui_racer} | {w_pos} | {move_grp} | {b_rem} |")

    racer_table = mo.md(
        "| Racer | Start Pos | Order | Remove |\n"
        "| :--- | :--- | :---: | :---: |\n" + "\n".join(table_rows),
    )
    return (
        add_button,
        add_racer_dropdown,
        board_selector,
        current_roster,
        debug_mode_ui,
        dice_rolls_text_ui,
        encoded_config_input,
        load_encoded_btn,
        racer_table,
        reset_button,
        scenario_seed,
        use_scripted_dice_ui,
    )


@app.cell
def cell_share_widget(
    GameConfig,
    board_selector,
    current_roster,
    mo,
    scenario_seed,
):
    # Generate string from current state
    current_config_obj = GameConfig(
        racers=tuple(current_roster),
        board=board_selector.value,
        seed=scenario_seed.value,
    )

    share_widget = mo.ui.text_area(
        value=current_config_obj.encoded,
        disabled=True,  # Read-only
        full_width=True,
        rows=5,
    )
    return (share_widget,)


@app.cell
def _(
    add_button,
    add_racer_dropdown,
    board_selector,
    debug_mode_ui,
    dice_input,
    encoded_config_input,
    load_encoded_btn,
    mo,
    racer_table,
    reset_button,
    results_tabs,
    scenario_seed,
    share_widget,
    use_scripted_dice_ui,
):
    # --- 1. Left Column (Fixed/Narrower) ---
    # We apply the style directly to this vstack
    left_col = mo.vstack(
        [
            mo.md("## Configure"),
            mo.hstack(
                [scenario_seed, board_selector, reset_button],
                justify="start",
                align="center",
            ),
            mo.vstack([use_scripted_dice_ui, dice_input]),
            mo.hstack([debug_mode_ui], justify="start"),
            mo.md("### Racers"),
            racer_table,
            mo.hstack([add_racer_dropdown, add_button], justify="start"),
        ],
    ).style(
        {
            "flex": "1 1 400px",  # Base width 400px
            "max-width": "400px",  # Cap width so it doesn't stretch on wide screens
            "min-width": "300px",  # Minimum before it feels too squashed
        },
    )

    # --- 2. Right Column (Greedy) ---
    # We apply the greedy flex style here
    right_col = mo.vstack(
        [
            results_tabs,
            mo.hstack(
                [
                    mo.md("Enter encoded config: "),
                    encoded_config_input,
                    load_encoded_btn,
                    mo.md("Copy encoded config: "),
                    share_widget,
                ],
                justify="start",
            ),
        ],
    ).style(
        {
            "flex": "999 1 500px",  # Massive grow factor (999) eats all remaining space
            "min-width": "0",  # Critical for scrolling tables
            "overflow-x": "auto",  # Allow internal scrolling
        },
    )

    # --- 3. Native Composition ---
    mo.hstack(
        [left_col, right_col],
        wrap=True,  # Native wrapping support
        align="start",  # Aligns tops of columns
        gap=2,  # 2rem gap
    )
    return


@app.cell
def cell_load_config(
    df_races_clean,
    get_last_race_hash,
    get_last_result_hash,
    pl,
    racer_results_table,
    races_table,
    set_board,
    set_last_race_hash,
    set_last_result_hash,
    set_saved_positions,
    set_seed,
    set_selected_racers,
    set_step_idx,
    set_use_scripted_dice,
):
    # --- CONFIGURATION LOADER (Stable Version) ---

    # 1. Capture Current Table Selections
    curr_race_hash = None
    curr_race_row = None
    if races_table.value is not None and races_table.value.height > 0:
        curr_race_hash = races_table.value.item(0, "config_hash")
        curr_race_row = races_table.value.row(0, named=True)

    curr_res_hash = None
    if racer_results_table.value is not None and racer_results_table.value.height > 0:
        curr_res_hash = racer_results_table.value.item(0, "config_hash")

    # 2. Get Last Known States
    last_race = get_last_race_hash()
    last_res = get_last_result_hash()

    # 3. Detect Changes (Delta Check)
    # We only react if the current selection differs from the last recorded selection for that specific table.
    race_changed = curr_race_hash is not None and curr_race_hash != last_race
    res_changed = curr_res_hash is not None and curr_res_hash != last_res

    target_config = None

    # Priority: Races Table > Results Table
    # But only if it actually changed!
    if race_changed:
        target_config = curr_race_row
    elif res_changed:
        # Use the CLEANED races frame so racer_names is already a list
        filtered = df_races_clean.filter(pl.col("config_hash") == curr_res_hash)
        if filtered.height > 0:
            target_config = filtered.row(0, named=True)

    # 4. Apply Configuration (if any change detected)
    if target_config:
        raw_names = target_config.get("racer_names")

        # Now always expect a list from both paths
        if isinstance(raw_names, list):
            new_roster = [str(n) for n in raw_names]
        else:
            new_roster = []

        new_seed = int(target_config.get("seed", 42))
        new_board = target_config.get("board", "Standard")

        set_seed(new_seed)
        set_board(new_board)
        set_selected_racers(new_roster)
        set_saved_positions(dict.fromkeys(new_roster, 0))
        set_use_scripted_dice(False)
        set_step_idx(0)

    # 5. SYNC STATE (CRITICAL)
    # Always update the "last seen" hashes to match the current table values.
    # This prevents the "other" table from triggering a change in the next cycle
    # just because we ignored it this time.
    if curr_race_hash != last_race:
        set_last_race_hash(curr_race_hash)

    if curr_res_hash != last_res:
        set_last_result_hash(curr_res_hash)
    return


@app.cell
def cell_dice_input(dice_rolls_text_ui, mo, use_scripted_dice_ui):
    dice_input = dice_rolls_text_ui if use_scripted_dice_ui.value else mo.Html("")
    return (dice_input,)


@app.cell
def cell_display_config_ui(
    MAGSIM_VERSION,
    load_status,
    mo,
    racer_results_table,
    races_table,
    reload_data_btn,
    results_folder_browser,
):
    def _header():
        return mo.hstack(
            [mo.md(f"**v{MAGSIM_VERSION}**"), reload_data_btn],
            justify="end",
            gap=1,
        )

    results_tabs = mo.ui.tabs(
        {
            "Racer Results": mo.vstack([_header(), racer_results_table]),
            "Races": mo.vstack([_header(), races_table]),
            "Source": mo.vstack(
                [
                    mo.md("### Data Directory"),
                    mo.md(
                        "Select the folder containing `races.parquet` and `racer_results.parquet`.",
                    ),
                    mo.hstack(
                        [results_folder_browser, reload_data_btn],
                        align="center",
                    ),
                    mo.callout(mo.md(f"Current Status: {load_status}"), kind="neutral"),
                ],
            ).style({"width": "100%", "min-height": "400px"}),
        },
    )
    return (results_tabs,)


@app.cell
def cell_setup_log(
    BOARD_DEFINITIONS,
    Console,
    GameLogHighlighter,
    GameScenario,
    MoveCmdEvent,
    RacerConfig,
    RichHandler,
    RichMarkupFormatter,
    StepSnapshot,
    TripCmdEvent,
    WarpCmdEvent,
    current_roster,
    dataclasses,
    get_board,
    get_debug_mode,
    get_dice_rolls_text,
    get_saved_positions,
    get_seed,
    get_use_scripted_dice,
    logging,
    mo,
    re,
    reset_button,
):
    from magsim.simulation.telemetry import (
        MetricsAggregator,
        SnapshotPolicy,
        SnapshotRecorder,
    )

    # Reactivity triggers
    reset_button.value
    # Use state getters
    current_seed_val = get_seed()
    current_board_val = get_board()

    get_saved_positions()
    get_use_scripted_dice()
    get_dice_rolls_text()

    log_console = Console(
        record=True,
        width=120,
        force_terminal=True,
        color_system="truecolor",
        legacy_windows=False,  # Better rendering
    )

    root_logger = logging.getLogger()
    for h in root_logger.handlers[:]:
        root_logger.removeHandler(h)

    log_handler = RichHandler(
        console=log_console,
        markup=True,
        show_path=False,
        show_time=False,
        highlighter=GameLogHighlighter(),
    )
    log_handler.setFormatter(RichMarkupFormatter())
    root_logger.addHandler(log_handler)
    log_level = logging.DEBUG if get_debug_mode() else logging.INFO
    root_logger.setLevel(log_level)

    dice_rolls = None
    if get_use_scripted_dice():
        raw = get_dice_rolls_text().strip()
        if raw:
            try:
                dice_rolls = [int(t) for t in re.split(r"[,\s]+", raw) if t]
            except:
                pass

    # Updated: Use dynamic board and seed
    scenario = GameScenario(
        racers_config=[
            RacerConfig(i, n, start_pos=int(get_saved_positions().get(n, 0)))
            for i, n in enumerate(current_roster)
        ],
        dice_rolls=dice_rolls,
        seed=None if dice_rolls else current_seed_val,
        board=BOARD_DEFINITIONS.get(current_board_val, BOARD_DEFINITIONS["Standard"])(),
    )

    step_history = []
    turn_map = {}
    SNAPSHOT_EVENTS = (MoveCmdEvent, WarpCmdEvent, TripCmdEvent)

    class RichLogSource:
        def __init__(self, console):
            self._console = console

        def export_text(self) -> str:
            return self._console.export_text(clear=False)

        def export_html(self) -> str:
            return self._console.export_html(
                clear=False,
                inline_styles=True,
                code_format="{code}",
            )

    policy = SnapshotPolicy(
        snapshot_event_types=SNAPSHOT_EVENTS,
        ensure_snapshot_each_turn=True,
        fallback_event_name="TurnSkipped/Recovery",
        snapshot_on_turn_end=False,
    )

    snapshot_recorder = SnapshotRecorder(
        policy=policy,
        log_source=RichLogSource(log_console),
    )

    # --- CHANGED BLOCK START ---
    metrics_aggregator = MetricsAggregator(config_hash="interactive-session")
    metrics_aggregator.initialize_racers(scenario.engine)

    # FIX 1: Start the counter at 1.
    # Turn 0 is reserved for "Board Setup". Turn 1 is the first actual move.
    sim_turn_counter = {"current": 1}

    def on_event(engine, event):
        t_idx = sim_turn_counter["current"]
        snapshot_recorder.on_event(engine, event, turn_index=t_idx)
        metrics_aggregator.on_event(event, engine)

    if hasattr(scenario.engine, "on_event_processed"):
        scenario.engine.on_event_processed = on_event
    # --- CHANGED BLOCK END ---

    engine = scenario.engine

    # FIX 2: Capture Initial State as Turn 0
    snapshot_recorder.capture(engine, "InitialState", turn_index=0)

    with mo.status.spinner(title="Simulating..."):
        while engine.state.race_active:
            log_console.export_html(clear=True)
            t_idx = sim_turn_counter["current"]

            actual_racer_idx = engine.state.current_racer_idx

            # --- PREVIOUS BUG WAS HERE ---
            # Removed: pre_turn_serial = engine.state.roll_state.serial_id

            scenario.run_turn()

            post_turn_serial = engine.state.roll_state.serial_id

            metrics_aggregator.on_turn_end(engine, turn_index=t_idx)
            snapshot_recorder.on_turn_end(engine, turn_index=t_idx)

            last_snap = snapshot_recorder.step_history[-1]

            # Fix 1: Ensure snapshot points to the actor
            updates = {"current_racer": actual_racer_idx}

            # Fix 2: "Red X" logic (CORRECTED)
            # RollState resets to serial 0 at the start of every turn.
            # If serial remains 0 at the end, it means no roll logic was executed (Recovery/Skip).
            if t_idx > 0 and post_turn_serial == 0:
                updates["last_roll"] = 0

            fixed_snap = dataclasses.replace(last_snap, **updates)
            snapshot_recorder.step_history[-1] = fixed_snap

            sim_turn_counter["current"] += 1
            if len(snapshot_recorder.step_history) > 1000:
                break

    step_history: list[StepSnapshot] = snapshot_recorder.step_history
    turn_map = snapshot_recorder.turn_map

    info_md = mo.md(
        f"✅ **Simulation complete!** {len(current_roster)} racers, {sim_turn_counter['current'] - 1} turns",
    )
    return info_md, step_history, turn_map


@app.cell
def cell_show_simulation_info(info_md):
    info_md
    return


@app.cell
def cell_update_step_state(mo):
    get_step_idx, set_step_idx = mo.state(0, allow_self_loops=True)
    return get_step_idx, set_step_idx


@app.cell
def cell_simulation_navigation(
    get_step_idx,
    mo,
    set_step_idx,
    step_history,
    turn_map,
):
    # --- NAVIGATION LOGIC ---
    current_step_idx = get_step_idx()

    if not step_history:
        current_data, current_turn_idx, max_s = None, 0, 0
    else:
        current_step_idx = min(max(0, current_step_idx), len(step_history) - 1)
        current_data = step_history[current_step_idx]
        current_turn_idx = current_data.turn_index
        max_s = len(step_history) - 1

    next_step_val = min(max_s, current_step_idx + 1)
    prev_step_val = max(0, current_step_idx - 1)

    next_turn_target = current_turn_idx + 1
    prev_turn_target = current_turn_idx - 1

    if next_turn_target in turn_map:
        next_turn_step_val = turn_map[next_turn_target][-1]
    else:
        next_turn_step_val = current_step_idx

    if prev_turn_target in turn_map:
        prev_turn_step_val = turn_map[prev_turn_target][0]
    else:
        prev_turn_step_val = 0

    btn_prev_turn = mo.ui.button(
        label="◀◀Turn",
        on_click=lambda _: set_step_idx(prev_turn_step_val),
        disabled=(current_turn_idx <= 0),
    )
    btn_next_turn = mo.ui.button(
        label="Turn▶▶",
        on_click=lambda _: set_step_idx(next_turn_step_val),
        disabled=(next_turn_target not in turn_map),
    )
    btn_prev_step = mo.ui.button(
        label="◀ Step",
        on_click=lambda _: set_step_idx(prev_step_val),
        disabled=(current_step_idx <= 0),
    )
    btn_next_step = mo.ui.button(
        label="Step ▶",
        on_click=lambda _: set_step_idx(next_step_val),
        disabled=(current_step_idx >= max_s),
    )

    def on_slider_change(v):
        if v in turn_map:
            set_step_idx(turn_map[v][0])

    nav_max_turn = max(turn_map.keys()) if turn_map else 0
    turn_slider = mo.ui.slider(
        start=-1,
        stop=nav_max_turn,
        value=current_turn_idx,
        step=1,
        label="Turn Timeline",
        on_change=on_slider_change,
        full_width=True,
    )
    return (
        btn_next_step,
        btn_next_turn,
        btn_prev_step,
        btn_prev_turn,
        current_data,
        current_turn_idx,
        turn_slider,
    )


@app.cell
def cell_display_simulation_nav(
    Any,
    Literal,
    btn_next_step,
    btn_next_turn,
    btn_prev_step,
    btn_prev_turn,
    current_data,
    current_turn_idx,
    mo,
    step_history,
    turn_slider,
):
    # --- NAV LAYOUT ---
    curr_step: Any | Literal[0] = current_data.global_step_index if current_data else 0
    tot_steps = len(step_history) if step_history else 0

    status_text = mo.md(
        f"**Turn {current_turn_idx}** (Step {curr_step + 1}/{tot_steps})",
    )

    nav_ui = mo.vstack(
        [
            mo.hstack(
                [btn_prev_turn, turn_slider, btn_next_turn],
                justify="center",
                gap=1,
            ),
            mo.hstack(
                [btn_prev_step, status_text, btn_next_step],
                justify="center",
                gap=1,
            ),
        ],
    )
    return (nav_ui,)


@app.cell
def cell_log_viewer(
    BG_COLOR,
    current_data,
    current_turn_idx,
    mo,
    step_history,
    turn_map,
):
    # --- LOG VIEWER ---
    if not current_data:
        log_ui = mo.md("No logs")
    else:
        container_id = "log-container-main"
        segments = []
        log_max_turn = max(turn_map.keys())

        for t in range(log_max_turn + 1):
            if t not in turn_map:
                continue
            is_active = t == current_turn_idx
            end_of_turn_idx = turn_map[t][-1]
            full_turn_log = step_history[end_of_turn_idx].log_html

            if is_active:
                bg, border, opacity = "#181818", "#00FF00", "1.0"
                lines = full_turn_log.split("\n")
                target_line = current_data.log_line_index
                safe_idx = min(len(lines), target_line + 1)
                lines.insert(
                    safe_idx,
                    '<div style="color:red; font-size:10px; border-top:1px dashed red; margin-top:2px; margin-bottom:2px;">▲ CURRENT STEP</div>',
                )
                content_html = "<br>".join(lines)
            else:
                bg, border, opacity = BG_COLOR, "#333", "0.5"
                content_html = full_turn_log.replace("\n", "<br>")

            segments.append(f"""
            <div id="turn-log-{t}" style="padding:4px; border-left:4px solid {border}; background:{bg}; opacity:{opacity}; border-bottom:1px solid #333;">
                <div style="font-size:9px; color:#666; font-weight:bold;">TURN {t}</div>
                <div class="rich-wrapper">{content_html}</div>
            </div>
            """)

        full_html = "".join(segments)
        scroll_script = f"""<script>try {{const p = window.parent.document; const c = p.getElementById("{container_id}"); const t = p.getElementById("turn-log-{current_turn_idx}"); if(c && t) c.scrollTo({{top: t.offsetTop - c.offsetTop - 20, behavior: 'smooth'}});}} catch(e) {{}}</script>"""

        log_ui = mo.vstack(
            [
                mo.Html(
                    f"""
      <div id="{container_id}" style="
    height: 750px;
    overflow-y: auto;
    background: {BG_COLOR};
    font-family: Menlo, Monaco, 'Courier New', monospace;
    font-size: 15px;
    line-height: 1.3;
    padding: 8px;
      ">
    {full_html}
      </div>
      """,
                ),
                mo.iframe(scroll_script, width="0", height="0"),
            ],
        )
    return (log_ui,)


@app.cell
def cell_show_simulation_section(
    BOARD_DEFINITIONS,
    board_positions,
    current_data,
    get_board,
    log_ui,
    mo,
    nav_ui,
    render_game_track,
):
    # --- COMPOSITION ---
    if not current_data:
        layout = mo.md("Waiting for simulation...")
    else:
        factory = BOARD_DEFINITIONS.get(get_board())
        if not factory:
            factory = BOARD_DEFINITIONS["Standard"]
        board_instance = factory()

        # 3. Render
        track_svg = mo.Html(
            render_game_track(current_data, board_positions, board=board_instance),
        )
        _left_col = mo.vstack([track_svg, nav_ui], align="center").style(
            {
                "flex": "1 1 800px",
                "min-width": "0",
            },
        )
        _right_col = log_ui.style({"flex": "1 1 650px", "min-width": "650"})

        layout = mo.hstack(
            [_left_col, _right_col],
            align="start",
            wrap=True,
        )
    layout
    return


@app.cell
def cell_vsialize_track(
    BOARD_THEME,
    MoveDeltaTile,
    StepSnapshot,
    TripTile,
    VictoryPointTile,
    get_racer_palette,
    math,
):
    def render_game_track(turn_data: StepSnapshot, positions_map, board=None):
        import html as _html

        # --- VISUALIZATION CONSTANTS ---
        MAIN_RADIUS = 9.0
        SECONDARY_RADIUS = 8.0
        OUTLINE_WIDTH = 1.7
        SECONDARY_WIDTH = 2
        TEXT_STROKE_WIDTH = "4px"

        if not turn_data:
            return "<p>No Data</p>"

        svg_elements = []

        # --- 1. CANVAS CONFIGURATION (PATCHED) ---
        # We define the "logical" size of the drawing area.
        # The viewBox will map these internal units to whatever size the screen allows.
        LOGICAL_W, LOGICAL_H = 950, 400

        # Transformation adjustments to center the track in the new tighter box
        scale_factor = 1.45
        trans_x = 40
        trans_y = -160
        rw, rh = 50, 30

        # 1. Track Groups
        track_group_start = (
            f'<g transform="translate({trans_x}, {trans_y}) scale({scale_factor})">'
        )

        # 2. Track Spaces
        for i, (cx, cy, rot) in enumerate(positions_map):
            transform = f"rotate({rot}, {cx}, {cy})"

            # --- 1. DEFAULT STYLES ---
            is_start = i == 0
            is_end = i == len(positions_map) - 1

            if (i // 2) % 2 == 0:
                fill_color = BOARD_THEME["tile_1"]
            else:
                fill_color = BOARD_THEME["tile_2"]

            stroke_color = BOARD_THEME["stroke_default"]
            stroke_width = "2"

            text_content = str(i)
            text_fill = BOARD_THEME["text_default"]
            font_weight = "bold"
            font_size = "10"

            # --- 2. SPECIAL TILE LOGIC ---
            if board:
                mods = board.static_features.get(i, [])
                for mod in mods:
                    if isinstance(mod, VictoryPointTile):
                        fill_color = BOARD_THEME["vp_fill"]
                        text_content = "VP"
                        text_fill = BOARD_THEME["vp_text"]
                    elif isinstance(mod, TripTile):
                        fill_color = BOARD_THEME["trip_fill"]
                        text_content = "T"
                        text_fill = BOARD_THEME["trip_text"]
                        font_size = "16"
                    elif isinstance(mod, MoveDeltaTile):
                        d = mod.delta
                        if d > 0:
                            fill_color = BOARD_THEME["move_pos_fill"]
                            text_content = f"+{d}"
                            text_fill = BOARD_THEME["move_pos_text"]
                        elif d < 0:
                            fill_color = BOARD_THEME["move_neg_fill"]
                            text_content = f"{d}"
                            text_fill = BOARD_THEME["move_neg_text"]

            # --- 3. START / END OVERRIDES ---
            if is_start:
                stroke_color = BOARD_THEME["start_stroke"]
                stroke_width = "4"
                if text_content == str(i):
                    text_content = "S"
                    text_fill = BOARD_THEME["start_text"]
            elif is_end:
                stroke_color = BOARD_THEME["goal_stroke"]
                stroke_width = "4"
                if text_content == str(i):
                    text_content = "G"
                    text_fill = BOARD_THEME["goal_text"]

            svg_elements.append(
                f'<rect x="{cx - rw / 2:.1f}" y="{cy - rh / 2:.1f}" width="{rw}" height="{rh}" '
                f'fill="{fill_color}" stroke="{stroke_color}" stroke-width="{stroke_width}" '
                f'transform="{transform}" rx="4" />',
            )

            svg_elements.append(
                f'<text x="{cx:.1f}" y="{cy:.1f}" dy="4" font-family="sans-serif" '
                f'font-size="{font_size}" font-weight="{font_weight}" '
                f'text-anchor="middle" fill="{text_fill}" transform="{transform}">{text_content}</text>',
            )

        # 3. Racers
        occupancy = {}
        for idx, pos in enumerate(turn_data.positions):
            if pos is None:
                continue
            draw_pos = min(pos, len(positions_map) - 1)
            name = turn_data.names[idx]
            palette = get_racer_palette(name)

            mods = turn_data.modifiers
            abils = turn_data.abilities
            mod_str = str(mods[idx]) if idx < len(mods) else "[]"
            abil_str = str(abils[idx]) if idx < len(abils) else "[]"
            tooltip_text = f"{name} (ID: {idx})\nVP: {turn_data.vp[idx]}\nTripped: {turn_data.tripped[idx]}\nAbils: {abil_str}\nMods: {mod_str}"

            occupancy.setdefault(draw_pos, []).append(
                {
                    "name": name,
                    "palette": palette,
                    "is_current": (idx == turn_data.current_racer),
                    "tripped": turn_data.tripped[idx],
                    "tooltip": tooltip_text,
                },
            )

        # Render Racers
        for space_idx, racers_here in occupancy.items():
            bx, by, brot = positions_map[space_idx]
            count = len(racers_here)

            if count == 1:
                offsets = [(0, 0)]
            elif count == 2:
                offsets = [(-15, 0), (15, 0)]
            elif count == 3:
                offsets = [(-15, -8), (15, -8), (0, 8)]
            else:
                offsets = [(-15, -8), (15, -8), (-15, 8), (15, 8)]

            for i, racer in enumerate(racers_here):
                if i >= len(offsets):
                    break
                ox, oy = offsets[i]

                rad = math.radians(brot)
                cx = bx + (ox * math.cos(rad) - oy * math.sin(rad))
                cy = by + (ox * math.sin(rad) + oy * math.cos(rad))

                vis_dx = cx - bx
                vis_dy = cy - by
                text_anchor = "middle"
                dy_text = 24
                tx = cx
                ty = cy

                if count > 1:
                    if abs(vis_dy) > abs(vis_dx):
                        if vis_dy < 0:
                            dy_text = -14
                        else:
                            dy_text = 24
                    else:
                        dy_text = 5
                        if vis_dx < 0:
                            text_anchor = "end"
                            tx = cx - 14
                        else:
                            text_anchor = "start"
                            tx = cx + 14

                pal = racer["palette"]
                stroke = pal.outline

                svg_elements.append("<g>")
                svg_elements.append(f"<title>{_html.escape(racer['tooltip'])}</title>")

                svg_elements.append(
                    f'<circle cx="{cx}" cy="{cy}" r="{MAIN_RADIUS}" fill="{pal.primary}" stroke="{stroke}" stroke-width="{OUTLINE_WIDTH}" />',
                )

                if pal.secondary:
                    svg_elements.append(
                        f'<circle cx="{cx}" cy="{cy}" r="{SECONDARY_RADIUS}" fill="none" stroke="{pal.secondary}" stroke-width="{SECONDARY_WIDTH}" />',
                    )

                svg_elements.append(
                    f'<text x="{tx}" y="{ty}" dy="{dy_text}" font-family="sans-serif" font-size="13" '
                    f'font-weight="900" text-anchor="{text_anchor}" fill="{pal.primary}" '
                    f'style="paint-order: stroke; stroke: #000; stroke-width: {TEXT_STROKE_WIDTH};">'
                    f"{_html.escape(racer['name'])}</text>",
                )

                if racer["tripped"]:
                    svg_elements.append(
                        f'<text x="{cx}" y="{cy}" dy="5" fill="#ff0000" font-weight="bold" font-size="14" text-anchor="middle">X</text>',
                    )
                svg_elements.append("</g>")

        svg_elements.append("</g>")

        # 4. Center Display
        # Adjust center calculation for new LOGICAL dimensions if necessary,
        # but since trans_x/scale_factor handle the track, we keep this relative to the track group
        center_x = (100 + 500) / 2 * scale_factor + trans_x
        center_y = (350 - 100) * scale_factor + trans_y

        active_idx = turn_data.current_racer
        active_name = turn_data.names[active_idx]
        active_pal = get_racer_palette(active_name)
        roll: int | None = turn_data.last_roll

        # Active Racer Name
        svg_elements.append(
            f'<text x="{center_x}" y="{center_y - 15}" font-size="28" font-weight="bold" text-anchor="middle" fill="{active_pal.primary}" style="paint-order: stroke; stroke: {active_pal.outline}; stroke-width: 2px; filter: drop-shadow(0px 0px 2px black);">{_html.escape(active_name)}</text>',
        )

        if roll:
            svg_elements.append(
                f'<text x="{center_x}" y="{center_y + 35}" font-size="40" font-weight="bold" text-anchor="middle" fill="#eee" >🎲 {roll}</text>',
            )
        elif turn_data.skipped_roll:
            svg_elements.append(
                f'<text x="{center_x}" y="{center_y + 35}" font-size="60" font-weight="bold" text-anchor="middle" fill="#ff0000" >X</text>',
            )

        # --- RETURN SVG (PATCHED) ---
        # Using viewBox allows the SVG to scale.
        # width="100%" means it fills the container. height="auto" maintains aspect ratio.
        return f"""<svg viewBox="0 0 {LOGICAL_W} {LOGICAL_H}" width="100%" height="auto" preserveAspectRatio="xMidYMid meet" style="background:{BOARD_THEME["background"]}; max-width: 100%;"> 
                {track_group_start}
                {"".join(svg_elements)}
            </svg>"""

    return (render_game_track,)


@app.cell
def cell_filter_autoracers():
    from magsim.core.agent import (
        BooleanInteractive,
        SelectionInteractive,
    )
    from magsim.core.registry import RACER_ABILITIES
    from magsim.racers import get_ability_classes

    ability_classes = get_ability_classes()

    # Filter: Keep racer if NONE of their abilities are interactive
    # This checks if the racer class implements the interactive protocols
    automatic_racers_list = [
        racer
        for racer, abilities in RACER_ABILITIES.items()
        if not any(
            issubclass(
                ability_classes.get(a),
                (BooleanInteractive, SelectionInteractive),
            )
            for a in abilities
            if ability_classes.get(a)
        )
    ]
    return (automatic_racers_list,)


@app.cell
def cell_manage_config_state(mo):
    # last_run_config starts as None.
    # It only updates when "Run Analysis" is clicked.
    last_run_config, set_last_run_config = mo.state(None)
    return last_run_config, set_last_run_config


@app.cell
def cell_combo_filter_state(mo):
    # Stores list of dicts: {"racers": ["Racer A", "Racer B"], "type": "Include", "id": ...}
    get_combo_filters, set_combo_filters = mo.state([], allow_self_loops=True)
    return get_combo_filters, set_combo_filters


@app.cell
def cell_combo_filter_ui(
    df_races_clean,
    get_combo_filters,
    mo,
    set_combo_filters,
):
    # Get unique racers from the clean dataframe for the dropdown options
    # We assume 'racer_names' is a list column in df_races_clean
    _unique_racers = sorted(
        {r for sublist in df_races_clean["racer_names"].to_list() for r in sublist},
    )

    combo_racer_select = mo.ui.multiselect(
        options=_unique_racers,
        label="Select Racers for Combo",
        full_width=True,
    )
    combo_type_select = mo.ui.dropdown(
        options=["Must Include All", "Must Exclude Combination"],
        value="Must Include All",
        label="Filter Type",
    )

    def add_combo_filter():
        if not combo_racer_select.value:
            return

        current = get_combo_filters()
        new_filter = {
            "racers": sorted(list(combo_racer_select.value)),
            "type": combo_type_select.value,
            "id": str(len(current)) + "_" + str(hash(str(combo_racer_select.value))),
        }

        # Prevent duplicates
        for _f in current:
            if (
                _f["racers"] == new_filter["racers"]
                and _f["type"] == new_filter["type"]
            ):
                return

        set_combo_filters(current + [new_filter])

    add_combo_btn = mo.ui.button(
        label="Add Combo Filter",
        on_click=lambda _: add_combo_filter(),
        kind="neutral",
    )

    combo_ui = mo.vstack(
        [
            mo.hstack(
                [combo_type_select, combo_racer_select, add_combo_btn],
                align="end",  # Aligns items vertically to bottom (so button lines up with inputs)
                justify="start",  # Aligns items horizontally to the left
            ),
        ],
        align="start",  # Aligns the whole stack to the left
    )
    return (combo_ui,)


@app.cell
def cell_combo_filter_display(get_combo_filters, mo, set_combo_filters):
    import functools

    # 1. Define Remove Handler
    def _remove_id(target_id):
        current = get_combo_filters()
        # Filter by ID (robust string comparison)
        new_list = [c for c in current if str(c["id"]) != str(target_id)]
        set_combo_filters(new_list)

    # 2. Render Buttons from State
    current_filters = get_combo_filters()
    filter_buttons = []

    for combo in current_filters:
        c_id = str(combo["id"])
        is_include = combo["type"] == "Must Include All"

        # Symbol & Color Logic
        if is_include:
            symbol = "✅"
            kind_val = "success"
        else:
            symbol = "🚫"
            kind_val = "danger"

        label = f"{symbol} {', '.join(combo['racers'])}  [x]"
        handler = functools.partial(lambda _, fid: _remove_id(fid), fid=c_id)

        btn = mo.ui.button(
            label=label,
            on_click=handler,  # <--- FIXED: using the bound handler
            kind=kind_val,
            tooltip="Click to remove",
        )
        filter_buttons.append(btn)

    # 3. Output UI
    if not filter_buttons:
        active_filters_display = mo.md(
            "<span style='color:#999; font-style:italic; font-size:0.9rem'>No active filters</span>",
        )
    else:
        active_filters_display = mo.hstack(
            filter_buttons,
            wrap=True,
            gap=0.5,
            justify="start",
        )
    return (active_filters_display,)


@app.cell
def cell_autoracer_btn(mo):
    select_auto_racers_btn = mo.ui.run_button(
        label="🤖 Select automatic racers",
        kind="neutral",
        tooltip="Select all racers that do not require human/AI decisions.",
    )
    return (select_auto_racers_btn,)


@app.cell
def cell_general_filters_ui(df_races, mo):
    # 1. Define UI Elements
    unique_boards = sorted(df_races["board"].unique().to_list())

    board_filter = mo.ui.multiselect(
        options=unique_boards,
        value=unique_boards,
        label="Filter Boards",
    )

    racer_count_filter = mo.ui.multiselect(
        options=sorted(df_races["racer_count"].unique().to_list()),
        value=sorted(df_races["racer_count"].unique().to_list()),
        label="Racer Count",
    )

    # 2. Display them
    filter_ui = mo.vstack(
        [
            mo.hstack([board_filter, racer_count_filter]),
        ],
    )

    # Return widgets so other cells can access .value
    return


@app.cell
def cell_general_filters_ui(df_races, mo):
    # 1. Define UI Elements
    # We use sorted unique values for the options
    unique_boards_opts = sorted(df_races["board"].unique().to_list())
    unique_counts_opts = sorted(df_races["racer_count"].unique().to_list())

    # Create the widgets
    board_filter_widget = mo.ui.multiselect(
        options=unique_boards_opts,
        value=unique_boards_opts,
        label="Filter Boards",
    )

    racer_count_widget = mo.ui.multiselect(
        options=unique_counts_opts,
        value=unique_counts_opts,
        label="Racer Count",
    )

    # 2. Layout
    general_filters_ui = mo.vstack(
        [
            mo.hstack([board_filter_widget, racer_count_widget]),
        ],
    )

    # Return the WIDGET OBJECTS so the next cell can read their .value
    return board_filter_widget, racer_count_widget


@app.cell
def cell_apply_all_filters(
    board_filter_widget,
    df_races_clean,
    get_combo_filters,
    mo,
    pl,
    racer_count_widget,
):
    # 1. Start with General Filters (reading .value is allowed here because widgets were created in a different cell)
    # We use 'current_mask' to build the filter expression incrementally
    current_mask = (pl.col("board").is_in(board_filter_widget.value)) & (
        pl.col("racer_count").is_in(racer_count_widget.value)
    )

    # 2. Apply Combo Filters
    # We iterate over the list of active combo filters
    active_combos = get_combo_filters()
    for combo_item in active_combos:
        target_racers = combo_item["racers"]

        # Check if row has ALL these racers
        # Using list.contains for each racer and combining with AND
        has_all_racers = pl.all_horizontal(
            [pl.col("racer_names").list.contains(r_name) for r_name in target_racers],
        )

        if combo_item["type"] == "Must Include All":
            current_mask = current_mask & has_all_racers
        else:
            # "Must Exclude Combination" means: It is NOT the case that (Has A AND Has B)
            current_mask = current_mask & (~has_all_racers)

    # 3. Execute Filter
    # We produce a NEW dataframe with a UNIQUE global name
    df_races_final_selection = df_races_clean.filter(current_mask)

    # 4. Rich Status Display
    n_selected_racers = len(
        racer_count_widget.value,
    )  # Assuming you can access this or pass it
    # Actually, better to read from the dataframe or the widgets directly available in this cell

    selected_boards = board_filter_widget.value
    selected_counts = racer_count_widget.value
    n_combos = len(active_combos)

    summary_md = f"""
    **Analysis Scope:**
    - **Races Found:** {df_races_final_selection.height} (of {df_races_clean.height})
    - **Boards:** {", ".join(selected_boards) if len(selected_boards) < 4 else f"{len(selected_boards)} boards"}
    - **Player Counts:** {", ".join(map(str, selected_counts))}
    - **Active Constraints:** {n_combos} combo filters
    """

    status_display = mo.callout(mo.md(summary_md), kind="info")
    return


@app.cell
def _(
    automatic_racers_list,
    df_racer_results,
    df_races,
    get_combo_filters,
    mo,
    select_auto_racers_btn,
    set_last_run_config,
):
    # 1. Prepare Options from RAW Data
    all_racers = sorted(df_racer_results.get_column("racer_name").unique().to_list())
    all_boards = sorted(df_races.get_column("board").unique().to_list())
    all_counts = sorted(df_races.get_column("racer_count").unique().to_list())

    # 2. Handle Auto-Select Logic
    # We can safely read .value because the button was defined in a previous cell
    if select_auto_racers_btn.value:
        _current_selection = [r for r in automatic_racers_list if r in all_racers]
    else:
        _current_selection = all_racers

    # 3. Define Filter Widgets
    ui_racers = mo.ui.multiselect(
        options=all_racers,
        value=_current_selection,
        label="Racers (roster pool)",
    )
    ui_counts = mo.ui.multiselect(
        options=all_counts,
        value=all_counts,
        label="Racer count(s)",
    )
    ui_boards = mo.ui.multiselect(
        options=all_boards,
        value=all_boards,
        label="Board(s)",
    )

    matchup_metric_toggle = mo.ui.switch(value=True, label="Show Percentage Shift")
    dynamic_zoom_toggle = mo.ui.switch(label="🔍 Rank-based view", value=False)

    # 4. Define "Run Analysis" Button with Callback
    def _submit_filters(_):
        set_last_run_config(
            {
                "racers": ui_racers.value,
                "boards": ui_boards.value,
                "counts": ui_counts.value,
                "combo_filters": get_combo_filters(),
            },
        )

    run_computation_btn = mo.ui.button(
        label="🚀 Run Analysis",
        kind="success",
        on_click=_submit_filters,
        tooltip="Click to process data with current filters.",
    )
    return (
        dynamic_zoom_toggle,
        matchup_metric_toggle,
        run_computation_btn,
        ui_boards,
        ui_counts,
        ui_racers,
    )


@app.cell
def cell_show_filters(
    active_filters_display,
    combo_ui,
    get_combo_filters,
    last_run_config,
    mo,
    run_computation_btn,
    select_auto_racers_btn,
    ui_boards,
    ui_counts,
    ui_racers,
):
    stale_warning = None  # Initialize to None, not empty markdown

    if last_run_config() is not None:

        def _norm_combos(cs):
            return sorted((c["type"], tuple(c["racers"])) for c in (cs or []))

        run_cfg = last_run_config()
        is_stale = (
            ui_racers.value != run_cfg["racers"]
            or ui_boards.value != run_cfg["boards"]
            or ui_counts.value != run_cfg["counts"]
            or _norm_combos(get_combo_filters()) != _norm_combos(run_cfg.get("combos"))
        )

        if is_stale:
            # FIX: Removed the trailing comma that made this a Tuple
            stale_warning = mo.md(
                '<div style="color: #DC143C; margin-bottom: 0.75rem;">⚠️ <b>Filters Changed:</b> The dashboard below is showing old data. Click <b>🚀 Run Analysis</b> to update.</div>',
            )

    # Layout
    header = mo.md(
        """
        <hr style="margin: 1.25rem 0;" />
        <h2 style="margin: 0 0 0.5rem 0;">Aggregated Dashboard</h2>
        <div style="color: #aaa; margin-bottom: 0.75rem;">
          Filter races by roster, board, and player count.
        </div>
        """,
    )

    # Combine everything
    mo.vstack(
        [
            header,
            # Row 1: Basic Filters
            mo.hstack(
                [ui_racers, select_auto_racers_btn, ui_counts, ui_boards],
                justify="start",
                align="center",
            ),
            # Row 2: Combo Filters (Accordion + Display)
            mo.accordion(
                {
                    "Advanced Combination Filters": mo.vstack(
                        [
                            combo_ui,  # The "Add" interface
                            mo.md("---"),  # Separator
                            active_filters_display,  # The list of removal buttons
                        ],
                    ),
                },
            ),
            # Row 3: Run Button
            mo.hstack([run_computation_btn], justify="end"),
            stale_warning if stale_warning else mo.md(""),
        ],
    )
    return


@app.cell
def cell_filter_data(
    df_racer_results,
    df_races_clean,
    last_run_config,
    mo,
    pl,
):
    # 1. Initialize Outputs
    df_racer_results_f = df_racer_results.head(0)
    df_races_f = df_races_clean.head(0)
    _selected_boards = []
    _selected_counts = []
    selected_racers = []

    _error_msg = None

    # 2. Logic Block
    if last_run_config() is None:
        mo.output.replace(
            mo.md(
                '<div style="color: #DC143C; margin-bottom: 0.75rem;">ℹ️ <b>Waiting for Input:</b> Adjust filters above and click <b>🚀 Run Analysis</b> to generate stats.<div>',
            ),
        )
    else:
        # 3. Unwrap Config
        selected_racers = list(last_run_config()["racers"])
        _selected_counts = list(last_run_config()["counts"])
        _selected_boards = list(last_run_config()["boards"])

        # 4. Validation
        if len(_selected_boards) == 0:
            _error_msg = "Select at least one board."
        elif len(_selected_counts) == 0:
            _error_msg = "Select at least one racer count."
        else:
            _min_req = max(_selected_counts)
            if len(selected_racers) < _min_req:
                _error_msg = f"Need at least {_min_req} racers selected, but only {len(selected_racers)} selected."

        # 5. Apply Filters
        if _error_msg is None:
            _base_filter_mask = (
                pl.col("board").is_in(_selected_boards)
                & pl.col("racer_count").is_in(_selected_counts)
                & pl.col("error_code").is_null()
                & pl.col("total_turns").gt(1)
            )

            # B. Combo Filters
            _active_combos = last_run_config().get("combo_filters", [])
            for _combo in _active_combos:
                _targets = _combo["racers"]
                _has_all = pl.all_horizontal(
                    [pl.col("racer_names").list.contains(r) for r in _targets],
                )
                if _combo["type"] == "Must Include All":
                    _base_filter_mask = _base_filter_mask & _has_all
                else:
                    _base_filter_mask = _base_filter_mask & (~_has_all)

            _races_bc = df_races_clean.filter(_base_filter_mask)

            # C. Roster Check
            _roster_ok = (
                df_racer_results.join(
                    _races_bc.select("config_hash", "racer_count"),
                    on="config_hash",
                    how="inner",
                )
                .group_by(["config_hash", "racer_count"])
                .agg(
                    [
                        pl.col("racer_name").n_unique().alias("n_present"),
                        pl.col("racer_name")
                        .is_in(selected_racers)
                        .all()
                        .alias("all_in_pool"),
                    ],
                )
                .filter(
                    pl.col("all_in_pool")
                    & (pl.col("n_present") == pl.col("racer_count")),
                )
                .select(["config_hash"])
            )

            _eligible_hashes = _roster_ok.get_column("config_hash").unique()

            # D. Final Data Assignment
            df_races_f = df_races_clean.filter(
                pl.col("config_hash").is_in(_eligible_hashes),
            )
            df_racer_results_f = df_racer_results.filter(
                pl.col("config_hash").is_in(_eligible_hashes),
            )

            if df_races_f.height == 0:
                _error_msg = "No data matches filters."
                df_races_f = df_races_clean.head(0)
                df_racer_results_f = df_racer_results.head(0)

        # 6. Display Error if needed
        if _error_msg:
            mo.output.replace(
                mo.md(
                    f"<div style='color:#ff6b6b; font-weight:600; margin-top:0.5rem;'>⚠ {_error_msg}</div>",
                ),
            )

    # 7. Final Return
    return df_racer_results_f, df_races_f


@app.cell
def _(df_racer_results_f, df_races_f, mo, pl):
    if df_races_f.height == 0:
        mo.stop(True)

    df_working = df_races_f
    df_racer_results_filtered = df_racer_results_f

    def _calculate_all_data():
        # 0. PREP: Extract Duration Info First
        race_time_info = df_working.select(
            [
                "config_hash",
                "racer_count",
                "turns_on_winning_round",
                pl.col("total_turns").alias("race_global_turns"),
            ],
        )

        results_augmented = (
            df_racer_results_filtered.join(race_time_info, on="config_hash", how="left")
            .with_columns(
                [
                    pl.col("pos_self_ability_movement").fill_null(0),
                    pl.col("neg_self_ability_movement").fill_null(0),
                    pl.col("pos_other_ability_movement").fill_null(0),
                    pl.col("neg_other_ability_movement").fill_null(0),
                    pl.col("ability_own_turn_count").fill_null(0),
                    pl.col("ability_self_target_count").fill_null(0),
                    pl.col("ability_trigger_count").fill_null(0),
                    pl.col("rolling_turns").fill_null(0),
                    pl.col("sum_dice_rolled").fill_null(0),
                    pl.col("recovery_turns").fill_null(0),
                    pl.col("skipped_main_moves").fill_null(0),
                    pl.col("skipped_self_main_move").fill_null(0),
                    pl.col("skipped_other_main_move").fill_null(0),
                ],
            )
            .with_columns(
                [
                    # --- DURATION LOGIC ---
                    pl.when(pl.col("finish_position") == 1)
                    .then(pl.col("turns_on_winning_round") * pl.col("racer_count"))
                    .otherwise(pl.col("race_global_turns"))
                    .alias("effective_global_duration"),
                    # ----------------------
                    (
                        pl.col("turns_taken")
                        - pl.col("recovery_turns")
                        - pl.col("skipped_main_moves")
                    ).alias("active_turns_count"),
                ],
            )
            # -----------------------------------------------------------------
            # 1. BASE CALCS + DICE ATTRIBUTION (Corrected)
            # -----------------------------------------------------------------
            .with_columns(
                [
                    (pl.col("active_turns_count") / pl.col("turns_taken").replace(0, 1))
                    .fill_nan(0)
                    .alias("active_turns_pct"),
                    # Identify if Dicemonger is in this specific race
                    pl.col("racer_name")
                    .eq("Dicemonger")
                    .any()
                    .over("config_hash")
                    .alias("dicemonger_in_race"),
                ]
            )
            .with_columns(
                # A. Calculate "Pure Baseline" (Avg Dice ignoring Dicemonger games)
                # For Magician: This is his Avg in non-Dicemonger games.
                # For Others: This will likely converge to 3.5, but we calculate it to be precise.
                (
                    pl.col("sum_dice_rolled")
                    .filter(~pl.col("dicemonger_in_race"))
                    .sum()
                    .over("racer_name")
                    / pl.col("rolling_turns")
                    .filter(~pl.col("dicemonger_in_race"))
                    .sum()
                    .over("racer_name")
                )
                .fill_null(3.5)
                .alias("global_avg_dice_pure")
            )
            .with_columns(
                [
                    # DICE LUCK: Self-Actualization (vs 3.5)
                    # 1. Dicemonger: Gets his own actual luck (Actual - 3.5).
                    # 2. Magician (No Dicemonger): Gets actual luck (Actual - 3.5).
                    # 3. Magician (With Dicemonger): Gets "Standard" luck (PureBaseline - 3.5).
                    # 4. Everyone else: 0.
                    (
                        pl.col("pos_self_ability_movement")
                        + (
                            pl.when(pl.col("racer_name") == "Dicemonger")
                            .then(
                                (
                                    pl.col("sum_dice_rolled")
                                    - (pl.col("rolling_turns") * 3.5)
                                )
                            )
                            .when(
                                (pl.col("racer_name") == "Magician")
                                & (~pl.col("dicemonger_in_race"))
                            )
                            .then(
                                (
                                    pl.col("sum_dice_rolled")
                                    - (pl.col("rolling_turns") * 3.5)
                                )
                            )
                            .when(
                                (pl.col("racer_name") == "Magician")
                                & (pl.col("dicemonger_in_race"))
                            )
                            .then(
                                (
                                    # Grant "Standard Performance" to stabilize the average
                                    (pl.col("global_avg_dice_pure") - 3.5)
                                    * pl.col("rolling_turns")
                                )
                            )
                            .otherwise(0)
                            .clip(0, 9999)
                        ).fill_nan(0)
                    ).alias("pos_self_ability_movement"),
                    # 3. Dicemonger Attribution: Calculate marginal gain vs "Pure Baseline"
                    (
                        (
                            (
                                pl.col("sum_dice_rolled")
                                / pl.col("rolling_turns").replace(0, 1)
                            )
                            - pl.col("global_avg_dice_pure")
                        )
                        * pl.col("rolling_turns")
                    )
                    .fill_nan(0)
                    .alias("marginal_gain_dice"),
                ]
            )
            .with_columns(
                # 4. Dicemonger Attribution: Give Dicemonger credit for the BOOST (Actual - Pure)
                pl.when(pl.col("racer_name") == "Dicemonger")
                .then(
                    pl.col("pos_other_ability_movement")
                    + (
                        pl.col("marginal_gain_dice").sum().over("config_hash")
                        - pl.col("marginal_gain_dice")
                    )
                )
                .otherwise(pl.col("pos_other_ability_movement"))
                .alias("pos_other_ability_movement"),
                # 5. Net Self Movement (Finalized)
                (
                    pl.col("pos_self_ability_movement")
                    - pl.col("neg_self_ability_movement")
                ).alias("net_self_movement"),
            )
        )

        # --- 0.5. CALCULATE SKIPPED TURN COSTS ---
        # We calculate individual speeds to get the global average
        results_augmented = results_augmented.with_columns(
            (
                (pl.col("sum_dice_rolled") + pl.col("pos_self_ability_movement"))
                / pl.col("active_turns_count").replace(0, 1)  # Avoid div/0
            ).alias("raw_speed_per_active_turn"),
        )

        # GLOBAL CONSTANT: Used for skip penalties to avoid circular logic
        global_avg_active_speed = (
            results_augmented.select(pl.col("raw_speed_per_active_turn").mean()).item()
            or 3.5
        )

        # 1. TRUTH
        global_win_rates = (
            results_augmented.group_by("racer_name")
            .agg(
                (pl.col("finish_position") == 1).sum().alias("total_wins"),
                pl.len().alias("total_races"),
            )
            .with_columns(
                (pl.col("total_wins") / pl.col("total_races")).alias("global_win_rate"),
            )
        )

        # 2. BASELINE
        df_baselines = (
            results_augmented.filter(
                (~pl.col("finish_position") == 1) & (~pl.col("eliminated")),
            )
            .group_by("config_hash")
            .agg(pl.col("turns_taken").median().alias("median_turns_baseline"))
        )
        stats_results = results_augmented.join(
            df_baselines,
            on="config_hash",
            how="left",
        ).with_columns(
            pl.col("median_turns_baseline").fill_null(pl.col("turns_taken")),
            pl.when(pl.col("turns_taken") <= 0)
            .then(None)
            .otherwise(pl.col("turns_taken"))
            .alias("total_turns_clean"),
        )

        # 3. RACE ENV
        race_agg_stats = stats_results.group_by("config_hash").agg(
            (pl.col("ability_trigger_count").sum() / pl.col("racer_id").count()).alias(
                "race_avg_triggers",
            ),
            (pl.col("recovery_turns").sum() / pl.col("turns_taken").sum()).alias(
                "race_avg_trip_rate",
            ),
        )

        stats_races = (
            df_working.select(
                [
                    "config_hash",
                    "tightness_score",
                    "volatility_score",
                    "board",
                    "racer_count",
                ],
            )
            .join(race_time_info, on=["config_hash", "racer_count"], how="left")
            .join(race_agg_stats, on="config_hash", how="left")
            .fill_null(0)
        )

        # 4. ENRICHMENT (The Final Calculation)
        # We integrate the Inchworm correction directly into the cost assignment
        stats_results = (
            stats_results.with_columns(
                [
                    # A. Calculate Costs (including Special Mechanics)
                    (
                        pl.col("skipped_self_main_move")
                        * pl.lit(global_avg_active_speed)
                    ).alias("cost_skip_self"),
                    pl.when(pl.col("racer_name") == "Inchworm")
                    .then(
                        pl.col("skipped_other_main_move")
                        * (pl.lit(global_avg_active_speed) - 2.5),
                    )
                    .otherwise(
                        pl.col("skipped_other_main_move")
                        * pl.lit(global_avg_active_speed),
                    )
                    .alias("cost_skip_other"),
                ],
            )
            .with_columns(
                [
                    # B. Normalization (using the costs calculated above)
                    (
                        pl.col("pos_self_ability_movement")  # +Self
                        / pl.col("total_turns_clean").replace(0, None)
                    ).alias("norm_pos_self"),
                    (
                        (
                            pl.col("neg_self_ability_movement")  # -Self
                            + pl.col("cost_skip_self")
                        )
                        / pl.col("total_turns_clean").replace(0, None)
                    ).alias("norm_neg_self"),
                    (
                        pl.col("pos_other_ability_movement")  # +Other
                        / (
                            pl.col("effective_global_duration")
                            - pl.col("total_turns_clean")
                        ).replace(0, None)
                    ).alias("norm_pos_other"),
                    (
                        (
                            pl.col("neg_other_ability_movement")  # -Other
                            + pl.col("cost_skip_other")
                        )
                        / (
                            pl.col("effective_global_duration")
                            - pl.col("total_turns_clean")
                        ).replace(0, None)
                    ).alias("norm_neg_other"),
                    (
                        (
                            pl.col("pos_self_ability_movement")
                            - pl.col("neg_self_ability_movement")
                        )
                        / pl.col("total_turns_clean").replace(0, None)
                        + 3.5
                    ).alias("speed_raw_calc"),
                ],
            )
            .with_columns(
                # C. Net Movement
                (
                    pl.col("norm_pos_self").fill_null(0)
                    - pl.col("norm_neg_self").fill_null(0)
                    - pl.col("norm_pos_other").fill_null(0)
                    + pl.col("norm_neg_other").fill_null(0)
                ).alias("relative_speed_calc"),
            )
        )

        # 5. CONSISTENCY
        racer_mu_sigma = stats_results.group_by("racer_name").agg(
            pl.col("final_vp").mean().alias("mean_vp_mu"),
            pl.col("final_vp").std().fill_null(0).alias("std_vp_sigma"),
        )
        consistency_calc = (
            stats_results.join(racer_mu_sigma, on="racer_name", how="left")
            .with_columns(
                pl.when(pl.col("std_vp_sigma") == 0)
                .then(True)
                .otherwise(
                    (pl.col("final_vp") - pl.col("mean_vp_mu")).abs()
                    <= pl.col("std_vp_sigma"),
                )
                .alias("is_consistent"),
            )
            .group_by("racer_name")
            .agg(
                pl.col("is_consistent").mean().alias("consistency_score"),
                pl.col("std_vp_sigma").first().alias("std_dev_val"),
            )
        )

        # 6. BASE STATS
        base_stats = (
            stats_results.join(
                stats_races.select(
                    [
                        "config_hash",
                        "tightness_score",
                        "volatility_score",
                        "race_avg_triggers",
                        "race_avg_trip_rate",
                        "race_global_turns",
                    ],
                ),
                on="config_hash",
                how="left",
            )
            .group_by("racer_name")
            .agg(
                pl.col("final_vp").mean().alias("mean_vp"),
                (pl.col("finish_position") == 1).sum().alias("cnt_1st"),
                (pl.col("finish_position") == 2).sum().alias("cnt_2nd"),
                pl.len().alias("races_run"),
                pl.col("tightness_score").mean().alias("avg_race_tightness"),
                pl.col("volatility_score").mean().alias("avg_race_volatility"),
                pl.col("race_avg_triggers").mean().alias("avg_env_triggers"),
                pl.col("race_avg_trip_rate").mean().alias("avg_env_trip_rate"),
                pl.col("race_global_turns").mean().alias("avg_game_duration"),
                pl.col("speed_raw_calc").mean().alias("avg_speed_raw"),
                pl.col("relative_speed_calc").mean().alias("avg_net_movement"),
                pl.col("active_turns_pct").mean().alias("avg_active_turns_pct"),
                pl.col("norm_pos_self").mean().alias("avg_pos_self"),
                pl.col("norm_neg_self").mean().alias("avg_neg_self"),
                pl.col("norm_pos_other").mean().alias("avg_pos_other"),
                pl.col("norm_neg_other").mean().alias("avg_neg_other"),
                (pl.col("ability_trigger_count") / pl.col("total_turns_clean"))
                .mean()
                .alias("triggers_per_turn"),
                (pl.col("ability_self_target_count") / pl.col("total_turns_clean"))
                .mean()
                .alias("self_targets_per_turn"),
                (pl.col("ability_own_turn_count") / pl.col("total_turns_clean"))
                .mean()
                .alias("own_turn_triggers_per_turn"),
            )
            .fill_nan(0)
        )

        # 7. CORRELATIONS
        stats_results_corr = stats_results.with_columns(
            (pl.col("sum_dice_rolled") / pl.col("rolling_turns").replace(0, 1)).alias(
                "avg_dice_val",
            ),
        )

        corr_df = (
            stats_results_corr.group_by("racer_name")
            .agg(
                pl.corr("avg_dice_val", "final_vp").abs().alias("dice_sensitivity"),
                pl.corr("net_self_movement", "final_vp").alias(
                    "ability_move_dependency",
                ),
                (pl.corr("racer_id", "final_vp") * -1).alias("start_pos_bias"),
                pl.corr("midgame_relative_pos", "final_vp").alias("midgame_bias"),
                pl.corr("ability_trigger_count", "final_vp")
                .abs()
                .alias("trigger_dependency"),
            )
            .fill_nan(0)
        )

        final_stats = (
            base_stats.join(corr_df, on="racer_name", how="left")
            .join(consistency_calc, on="racer_name", how="left")
            .join(
                global_win_rates.select(["racer_name", "global_win_rate"]),
                on="racer_name",
                how="left",
            )
            .with_columns(
                (pl.col("cnt_1st") / pl.col("races_run")).alias("pct_1st"),
                (pl.col("cnt_2nd") / pl.col("races_run")).alias("pct_2nd"),
                pl.col("consistency_score").fill_null(0),
                pl.col("global_win_rate").fill_null(0),
                pl.col("std_dev_val").fill_null(0).alias("std_vp_sigma"),
            )
            .fill_nan(0)
        )

        # B. MATRICES
        global_means = final_stats.select(
            ["racer_name", pl.col("mean_vp").alias("my_global_avg")],
        )
        subjects = stats_results.select(["config_hash", "racer_name", "final_vp"])
        opponents = stats_results.select(
            [pl.col("config_hash"), pl.col("racer_name").alias("opponent_name")],
        )
        matchup_df = (
            subjects.join(opponents, on="config_hash", how="inner")
            .filter(pl.col("racer_name") != pl.col("opponent_name"))
            .group_by(["racer_name", "opponent_name"])
            .agg(pl.col("final_vp").mean().alias("avg_vp_with_opponent"))
            .join(global_means, on="racer_name", how="left")
            .with_columns(
                (pl.col("avg_vp_with_opponent") - pl.col("my_global_avg")).alias(
                    "residual_matchup",
                ),
                (
                    (pl.col("avg_vp_with_opponent") - pl.col("my_global_avg"))
                    / pl.col("my_global_avg")
                ).alias("percentage_shift"),
            )
            .fill_nan(0)
        )

        # C. ABILITIES BREAKDOWN
        df_abilities_agg = (
            stats_results.group_by("racer_name")
            .agg(
                [
                    pl.col("norm_pos_self").mean().alias("+ Self"),
                    pl.col("norm_neg_self").mean().alias("- Self"),
                    pl.col("norm_pos_other").mean().alias("+ Others"),
                    pl.col("norm_neg_other").mean().alias("- Others"),
                ],
            )
            .fill_nan(0)
        )

        # --- D. RAW DISTRIBUTION DATA (NO FILTERING HERE) ---
        race_vp_agg = results_augmented.group_by("config_hash").agg(
            pl.col("final_vp").sum().alias("total_race_vp"),
        )
        dist_base_raw = stats_races.join(
            race_vp_agg,
            on="config_hash",
            how="inner",
        ).select(
            [
                "config_hash",
                "board",
                "racer_count",
                "race_global_turns",
                "total_race_vp",
            ],
        )

        return {
            "stats": final_stats,
            "matchup_df": matchup_df,
            "results_raw": stats_results,
            "races_raw": stats_races,
            "abilities_df": df_abilities_agg,
            "dist_raw": dist_base_raw,
        }

    chart_height_slider = mo.ui.slider(
        start=400,
        stop=1200,
        value=900,
        step=50,
    )

    with mo.status.spinner(
        title=f"Aggregating data for {df_working.height} races...",
    ) as _spinner:
        dashboard_data = _calculate_all_data()

    mo.output.replace(mo.md(f"✅ **{df_working.height}** races analyzed."))
    return chart_height_slider, dashboard_data


@app.cell
def _(BG_COLOR, alt, np, pl):
    def get_contrasting_stroke(hex_color):
        if not hex_color or not hex_color.startswith("#"):
            return "white"
        hex_color = hex_color.lstrip("#")
        try:
            r, g, b = tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
            return (
                "black"
                if ((0.299 * r + 0.587 * g + 0.114 * b) / 255) > 0.6
                else "white"
            )
        except:
            return "white"

    def build_quadrant_chart(
        stats_df,
        racers,
        colors,
        x_col,
        y_col,
        title,
        x_title,
        y_title,
        *,
        use_rank_scale: bool,
        reverse_x=False,
        quad_labels=None,
        extra_tooltips=None,
    ):
        PLOT_BG = "#232826"
        racer_to_hex = dict(zip(racers, colors))
        racer_to_stroke = {
            r: get_contrasting_stroke(c) for r, c in racer_to_hex.items()
        }

        # 1. Prepare Data & Domains
        if use_rank_scale:

            def _apply_rank_transform(df, col):
                series = df[col].drop_nulls()
                if series.len() < 3:
                    return df, col, [], []
                vals = series.to_numpy()
                sorted_vals = np.sort(vals)
                sorted_ranks = np.linspace(0, 1, len(vals))
                new_col = f"{col}_rank"

                def get_rank_pos(x):
                    return float(np.interp(x, sorted_vals, sorted_ranks))

                transformed_df = df.with_columns(
                    pl.col(col)
                    .map_elements(get_rank_pos, return_dtype=pl.Float64)
                    .alias(new_col),
                )
                ticks = np.unique(
                    np.percentile(vals, [0, 20, 40, 60, 80, 100]),
                ).tolist()
                vis_ticks = [
                    float(np.interp(t, sorted_vals, sorted_ranks)) for t in ticks
                ]
                return transformed_df, new_col, ticks, vis_ticks

            df_x, plot_x, ticks_x, vis_ticks_x = _apply_rank_transform(stats_df, x_col)
            chart_df, plot_y, ticks_y, vis_ticks_y = _apply_rank_transform(df_x, y_col)

            # Rank domains are always [0, 1] (plus padding)
            dom_x = [-0.05, 1.05]
            dom_y = [-0.05, 1.05]

            # Custom Axis Labels for Rank Mode
            axis_x = alt.Axis(
                grid=True,
                labelExpr=f"datum.value == {vis_ticks_x[0]} ? '{ticks_x[0]:.2f}' : "
                + " ".join(
                    [
                        f"abs(datum.value - {vt}) < 0.001 ? '{rt:.2f}' :"
                        for vt, rt in zip(vis_ticks_x[1:], ticks_x[1:])
                    ],
                )
                + " format(datum.value, '.2f')",
            )
            axis_y = alt.Axis(
                grid=True,
                labelExpr=f"datum.value == {vis_ticks_y[0]} ? '{ticks_y[0]:.2f}' : "
                + " ".join(
                    [
                        f"abs(datum.value - {vt}) < 0.001 ? '{rt:.2f}' :"
                        for vt, rt in zip(vis_ticks_y[1:], ticks_y[1:])
                    ],
                )
                + " format(datum.value, '.2f')",
            )
            mid_x, mid_y = 0.5, 0.5

        else:
            # Absolute Mode
            plot_x, plot_y = x_col, y_col
            chart_df = stats_df
            vals_x, vals_y = (
                stats_df[x_col].drop_nulls().to_list(),
                stats_df[y_col].drop_nulls().to_list(),
            )

            if not vals_x:
                return alt.Chart(stats_df).mark_text(text="No Data")

            min_x_val, max_x_val = min(vals_x), max(vals_x)
            min_y_val, max_y_val = min(vals_y), max(vals_y)

            # Avoid singular matrix if all values are same
            if min_x_val == max_x_val:
                max_x_val += 0.01
                min_x_val -= 0.01
            if min_y_val == max_y_val:
                max_y_val += 0.01
                min_y_val -= 0.01

            pad_x = (max_x_val - min_x_val) * 0.15
            pad_y = (max_y_val - min_y_val) * 0.15

            dom_x = [min_x_val - pad_x, max_x_val + pad_x]
            dom_y = [min_y_val - pad_y, max_y_val + pad_y]

            axis_x, axis_y = alt.Axis(grid=False), alt.Axis(grid=False)
            mid_x, mid_y = (min_x_val + max_x_val) / 2, (min_y_val + max_y_val) / 2

        # 2. Build Scales
        scale_x = alt.Scale(domain=dom_x, reverse=reverse_x, zero=False, nice=False)
        scale_y = alt.Scale(domain=dom_y, zero=False, nice=False)

        # 3. Add Stroke Data
        chart_df = chart_df.with_columns(
            pl.col("racer_name")
            .map_elements(
                lambda n: racer_to_stroke.get(n, "white"),
                return_dtype=pl.String,
            )
            .alias("txt_stroke"),
        )

        # 4. Reference Lines
        h_line = (
            alt.Chart(pl.DataFrame({"y": [mid_y]}))
            .mark_rule(strokeDash=[4, 4], color="#888")
            .encode(y=alt.Y("y:Q", scale=scale_y))
        )
        v_line = (
            alt.Chart(pl.DataFrame({"x": [mid_x]}))
            .mark_rule(strokeDash=[4, 4], color="#888")
            .encode(x=alt.X("x:Q", scale=scale_x))
        )

        # 5. Points & Labels
        points = (
            alt.Chart(chart_df)
            .mark_circle(size=250, opacity=0.9)
            .encode(
                x=alt.X(f"{plot_x}:Q", title=x_title, scale=scale_x, axis=axis_x),
                y=alt.Y(f"{plot_y}:Q", title=y_title, scale=scale_y, axis=axis_y),
                color=alt.Color(
                    "racer_name:N",
                    scale=alt.Scale(domain=racers, range=colors),
                    legend=None,
                ),
                tooltip=[
                    "racer_name:N",
                    alt.Tooltip(f"{x_col}:Q", format=".2f", title=x_title),
                    alt.Tooltip(f"{y_col}:Q", format=".2f", title=y_title),
                ]
                + (extra_tooltips or []),
            )
        )

        text_outline = points.mark_text(
            align="center",
            baseline="middle",
            dy=-22,
            dx=-22,
            fontSize=15,
            fontWeight=800,
            stroke=PLOT_BG,
            strokeWidth=3,
            opacity=1,
        ).encode(text="racer_name:N", color=alt.value(PLOT_BG))

        text_fill = points.mark_text(
            align="center",
            baseline="middle",
            dy=-22,
            dx=-22,
            fontSize=15,
            fontWeight=800,
        ).encode(
            text="racer_name:N",
            color=alt.Color(
                "racer_name:N",
                scale=alt.Scale(domain=racers, range=colors),
            ),
        )

        # 6. Quadrant Labels (Fixed Positioning)
        label_layers = []
        if quad_labels and len(quad_labels) == 4:
            # Calculate positions based on the definitive domains we calculated earlier
            x_min, x_max = dom_x
            y_min, y_max = dom_y

            # 5% padding from the edges
            x_range = x_max - x_min
            y_range = y_max - y_min

            px = x_range * 0.05
            py = y_range * 0.05

            # Define coordinates (Left/Right, Top/Bottom)
            # Note: If reverse_x is True, "Left" visually is x_max numerically
            if reverse_x:
                left_x = x_max - px
                right_x = x_min + px
            else:
                left_x = x_min + px
                right_x = x_max - px

            top_y = y_max - py
            bottom_y = y_min + py

            # Labels: TL, TR, BL, BR
            # quad_labels input order: [TL, TR, BL, BR]
            labels_config = [
                (left_x, top_y, quad_labels[0], "left", "top"),  # Top-Left
                (right_x, top_y, quad_labels[1], "right", "top"),  # Top-Right
                (
                    left_x,
                    bottom_y,
                    quad_labels[2],
                    "left",
                    "bottom",
                ),  # Bottom-Left
                (
                    right_x,
                    bottom_y,
                    quad_labels[3],
                    "right",
                    "bottom",
                ),  # Bottom-Right
            ]

            text_props = {
                "fontWeight": "bold",
                "opacity": 0.6,
                "fontSize": 14,
                "color": "#e0e0e0",
            }

            def _lbl(x, y, t, align, baseline):
                return (
                    alt.Chart(pl.DataFrame({"x": [x], "y": [y], "t": [t]}))
                    .mark_text(align=align, baseline=baseline, **text_props)
                    .encode(
                        x=alt.X("x:Q", scale=scale_x),
                        y=alt.Y("y:Q", scale=scale_y),
                        text="t:N",
                    )
                )

            label_layers = [_lbl(*cfg) for cfg in labels_config]

        layers = [points, text_outline, text_fill] + label_layers + [h_line, v_line]
        xzoom = alt.selection_interval(bind="scales", encodings=["x"], zoom="wheel!")
        return (
            alt.layer(*layers)
            .resolve_scale(x="shared", y="shared")
            .add_params(xzoom)
            .properties(width="container", height=800, background=BG_COLOR)
        )

    return (build_quadrant_chart,)


@app.cell
def cell_prepare_aggregated_data(alt):
    METRIC_ORDER = ["+ Self", "- Others", "- Self", "+ Others"]

    BAR_CHART_COLORS = alt.Scale(
        domain=METRIC_ORDER,
        range=["#40B0A6", "#D81B60", "#1E88E5", "#FFC107"],
    )

    X_AXIS_TICK_STEP = 0.5
    return BAR_CHART_COLORS, METRIC_ORDER


@app.cell
def _(
    BAR_CHART_COLORS,
    BG_COLOR,
    METRIC_ORDER,
    alt,
    build_quadrant_chart,
    chart_height_slider,
    dashboard_data,
    df_races_f,
    dynamic_zoom_toggle,
    get_racer_color,
    matchup_metric_toggle,
    mo,
    pl,
):
    if df_races_f.height == 0:
        mo.stop(True)

    if dashboard_data is None:
        mo.stop(True)

    stats = dashboard_data["stats"]
    matchup_df = dashboard_data["matchup_df"]
    proc_results = dashboard_data["results_raw"]
    proc_races = dashboard_data["races_raw"]
    abilities_df = dashboard_data["abilities_df"]

    # Raw dist data
    dist_raw = dashboard_data["dist_raw"]

    # --- 1. HELPERS ---
    r_list = stats["racer_name"].unique().to_list()
    c_list = [get_racer_color(r) for r in r_list]

    # --- CONSTANTS ---
    # Reducing fixed height to fit smaller screens better
    CHART_HEIGHT = chart_height_slider.value

    # --- 2. ABILITY SHIFT CHART ---
    df_racer = abilities_df.with_columns(
        (
            (pl.col("+ Self").abs() + pl.col("- Others").abs())
            - (pl.col("- Self").abs() + pl.col("+ Others").abs())
        ).alias("net_benefit_score"),
    ).sort("net_benefit_score", descending=True)
    y_sort_order = df_racer["racer_name"].to_list()
    df_long = df_racer.melt(
        id_vars=["racer_name"],
        value_vars=METRIC_ORDER,
        variable_name="metric",
        value_name="magnitude",
    )
    df_long = df_long.with_columns(
        [
            pl.when(pl.col("metric").is_in(["+ Self", "- Others"]))
            .then(-pl.col("magnitude").abs())
            .otherwise(pl.col("magnitude").abs())
            .alias("magnitude_signed"),
            pl.when(pl.col("metric").is_in(["+ Self", "- Self"]))
            .then(pl.lit(0))
            .otherwise(pl.lit(1))
            .alias("stack_order"),
        ],
    )
    neg_sums = (
        df_long.filter(pl.col("magnitude_signed") < 0)
        .group_by("racer_name")
        .agg(pl.col("magnitude_signed").sum().alias("left_edge"))
    )
    df_racer = df_racer.join(neg_sums, on="racer_name", how="left").with_columns(
        pl.col("left_edge").fill_null(0),
    )
    global_min_edge = df_racer["left_edge"].min()
    global_max_val = df_long["magnitude_signed"].max()
    domain_min = global_min_edge * 1.1 if global_min_edge < 0 else -1.0
    domain_max = global_max_val * 1.05
    y_axis_config = alt.Y("racer_name:N", sort=y_sort_order, axis=None)

    bars = (
        alt.Chart(df_long)
        .mark_bar()
        .encode(
            y=y_axis_config,
            x=alt.X(
                "magnitude_signed:Q",
                title="Movement Impact (Normalized)",
                scale=alt.Scale(domain=[domain_min, domain_max]),
                axis=alt.Axis(grid=False, labelColor="#E0E0E0", titleColor="#E0E0E0"),
            ),
            color=alt.Color(
                "metric:N",
                scale=BAR_CHART_COLORS,
                sort=METRIC_ORDER,
                legend=alt.Legend(
                    title="Ability Type",
                    orient="none",
                    legendX=60,
                    legendY=CHART_HEIGHT - 180,
                    direction="vertical",
                    titleColor="#E0E0E0",
                    labelColor="#E0E0E0",
                ),
            ),
            order=alt.Order("stack_order"),
            tooltip=[
                "racer_name:N",
                "metric:N",
                alt.Tooltip("magnitude:Q", format=".2f"),
            ],
        )
    )
    text_labels = (
        alt.Chart(df_racer)
        .mark_text(align="right", baseline="middle", dx=-8, fontSize=12, fontWeight=700)
        .encode(
            y=y_axis_config,
            x=alt.X("left_edge:Q"),
            text="racer_name:N",
            color=alt.Color(
                "racer_name:N",
                scale=alt.Scale(domain=r_list, range=c_list),
                legend=None,
            ),
        )
    )
    final_ability_chart = (
        alt.layer(
            bars,
            alt.Chart(pl.DataFrame({"x": [0]}))
            .mark_rule(color="#888", strokeDash=[2, 2])
            .encode(x="x:Q"),
            text_labels,
        )
        .resolve_scale(color="independent")
        .properties(
            width="container",
            height=CHART_HEIGHT,
            title=alt.TitleParams("Racer Ability Speed Profile", color="#E0E0E0"),
            background="transparent",
        )
    )

    # --- 3. QUADRANT CHARTS ---
    c_consist = build_quadrant_chart(
        stats,
        r_list,
        c_list,
        "consistency_score",
        "mean_vp",
        "Consistency",
        "Stability",
        "Avg VP",
        quad_labels=["Wildcard", "Reliable Winner", "Erratic", "Reliable Loser"],
        use_rank_scale=dynamic_zoom_toggle.value,
        extra_tooltips=[alt.Tooltip("std_vp_sigma:Q", format=".2f")],
    ).properties(height=CHART_HEIGHT)

    c_momentum = build_quadrant_chart(
        stats,
        r_list,
        c_list,
        "start_pos_bias",
        "midgame_bias",
        "Momentum Profile",
        "Start Pos Bias",
        "Mid-Game Bias",
        quad_labels=["Late Bloomer", "Snowballer", "Comeback King", "Frontrunner"],
        use_rank_scale=dynamic_zoom_toggle.value,
        extra_tooltips=[
            alt.Tooltip("pct_1st:Q", format=".1%"),
            alt.Tooltip("mean_vp:Q", format=".2f"),
        ],
    ).properties(height=CHART_HEIGHT)

    c_excitement = build_quadrant_chart(
        stats,
        r_list,
        c_list,
        "avg_race_tightness",
        "avg_race_volatility",
        "Excitement Profile",
        "Tightness",
        "Volatility",
        reverse_x=True,
        quad_labels=["Rubber Band", "Thriller", "Procession", "Stalemate"],
        use_rank_scale=dynamic_zoom_toggle.value,
    ).properties(height=CHART_HEIGHT)

    c_engine = build_quadrant_chart(
        stats,
        r_list,
        c_list,
        "dice_sensitivity",
        "trigger_dependency",
        "Engine Profile",
        "Dice Sensitivity",
        "Ability Efficacy",
        use_rank_scale=dynamic_zoom_toggle.value,
        quad_labels=["Technician", "Unstable", "Independent", "Gambler"],
    ).properties(height=CHART_HEIGHT)

    # --- 4. GLOBAL DYNAMICS ---
    color_turns = "#40B0A6"
    color_vp = "#D81B60"
    player_count_scale = alt.Scale(
        range=["#40B0A6", "#FFC107", "#D81B60", "#1E88E5", "#9C27B0"],
    )

    race_meta = df_races_f.select(["config_hash", "board", "racer_count"])
    joined_env = proc_results.join(race_meta, on="config_hash", how="inner")

    race_level_agg = proc_races.group_by(["board", "racer_count"]).agg(
        pl.col("race_global_turns").mean().alias("Avg Turns"),
        pl.col("tightness_score").mean().alias("Tightness"),
        pl.col("volatility_score").mean().alias("Volatility"),
        pl.col("race_avg_trip_rate").mean().alias("Trip Rate"),
        pl.col("race_avg_triggers").mean().alias("Abilities Triggered"),
    )
    result_level_agg = (
        joined_env.group_by(["board", "racer_count"])
        .agg(
            pl.col("final_vp").mean().alias("Avg VP"),
            pl.corr("sum_dice_rolled", "final_vp").alias("Dice Dep"),
            pl.corr("net_self_movement", "final_vp").alias("Ability Dep"),
            (pl.corr("racer_id", "final_vp") * -1).alias("Start Bias"),
            pl.corr("midgame_relative_pos", "final_vp").alias("MidGame Bias"),
        )
        .fill_nan(0)
    )

    global_wide = race_level_agg.join(
        result_level_agg,
        on=["board", "racer_count"],
        how="inner",
    ).fill_nan(0)

    c_global_1 = (
        alt.Chart(
            global_wide.select(
                [
                    "board",
                    "racer_count",
                    "Avg VP",
                    "Avg Turns",
                    "Tightness",
                    "Volatility",
                    "Trip Rate",
                ],
            ).unpivot(
                index=["board", "racer_count"],
                variable_name="metric",
                value_name="val",
            ),
        )
        .mark_bar()
        .encode(
            x=alt.X("board:N", title="Board", axis=alt.Axis(labelAngle=0)),
            xOffset=alt.XOffset("racer_count:N"),
            y=alt.Y("val:Q", title=None),
            color=alt.Color("racer_count:N", title="Players", scale=player_count_scale),
            column=alt.Column("metric:N", title=None),
            tooltip=[
                "board:N",
                "racer_count:N",
                "metric:N",
                alt.Tooltip("val:Q", format=".3f"),
            ],
        )
        .resolve_scale(y="independent")
        .properties(width=120, height=200, background="transparent")
    )
    c_global_2 = (
        alt.Chart(
            global_wide.select(
                [
                    "board",
                    "racer_count",
                    "Dice Dep",
                    "Ability Dep",
                    "Start Bias",
                    "MidGame Bias",
                    "Abilities Triggered",
                ],
            ).unpivot(
                index=["board", "racer_count"],
                variable_name="metric",
                value_name="val",
            ),
        )
        .mark_bar()
        .encode(
            x=alt.X("board:N", title="Board", axis=alt.Axis(labelAngle=0)),
            xOffset=alt.XOffset("racer_count:N"),
            y=alt.Y("val:Q", title=None),
            color=alt.Color("racer_count:N", title="Players", scale=player_count_scale),
            column=alt.Column("metric:N", title=None),
            tooltip=[
                "board:N",
                "racer_count:N",
                "metric:N",
                alt.Tooltip("val:Q", format=".3f"),
            ],
        )
        .resolve_scale(y="independent")
        .properties(width=120, height=200, background="transparent")
    )

    # --- 4.5 DISTRIBUTIONS ---
    q_low, q_high = 0.02, 0.98
    bounds = dist_raw.select(
        [
            pl.col("race_global_turns").quantile(q_low).alias("t_min"),
            pl.col("race_global_turns").quantile(q_high).alias("t_max"),
            pl.col("total_race_vp").quantile(q_low).alias("v_min"),
            pl.col("total_race_vp").quantile(q_high).alias("v_max"),
        ],
    ).to_dicts()[0]

    dist_viz = dist_raw.filter(
        pl.col("race_global_turns").is_between(bounds["t_min"], bounds["t_max"])
        & pl.col("total_race_vp").is_between(bounds["v_min"], bounds["v_max"]),
    )

    n_bins = 20
    turns_min = float(dist_viz["race_global_turns"].min())
    turns_max = float(dist_viz["race_global_turns"].max())
    vp_min = float(dist_viz["total_race_vp"].min())
    vp_max = float(dist_viz["total_race_vp"].max())
    turns_step = (turns_max - turns_min) / n_bins if turns_max > turns_min else 1.0
    vp_step = (vp_max - vp_min) / n_bins if vp_max > vp_min else 1.0

    def add_bins(df, col, min_v, step_v, prefix):
        idx = (
            ((pl.col(col) - min_v) / step_v).floor().cast(pl.Int64).clip(0, n_bins - 1)
        )
        start = (pl.lit(min_v) + idx * pl.lit(step_v)).round(0).cast(pl.Int64)
        end = (start + pl.lit(step_v)).round(0).cast(pl.Int64)
        label = start.cast(pl.Utf8) + pl.lit("-") + end.cast(pl.Utf8)
        return [idx.alias(f"{prefix}_idx"), label.alias(f"{prefix}_label")]

    dist_binned = dist_viz.with_columns(
        add_bins(dist_viz, "race_global_turns", turns_min, turns_step, "turns")
        + add_bins(dist_viz, "total_race_vp", vp_min, vp_step, "vp"),
    )

    def make_long_dist(df, group_cols):
        group_cols_eff = ["_grp"] if len(group_cols) == 0 else group_cols
        if len(group_cols) == 0:
            df = df.with_columns(pl.lit(1).alias("_grp"))

        t = (
            df.group_by(group_cols_eff + ["turns_idx", "turns_label"])
            .agg(pl.len().alias("count"))
            .with_columns(
                (pl.col("count") / pl.col("count").sum().over(group_cols_eff)).alias(
                    "pct",
                ),
                pl.col("turns_idx").alias("bin_index"),
                pl.col("turns_label").alias("bin_label"),
                pl.lit("Game Length (Turns)").alias("series_type"),
                pl.lit(1).alias("direction"),
            )
        )
        v = (
            df.group_by(group_cols_eff + ["vp_idx", "vp_label"])
            .agg(pl.len().alias("count"))
            .with_columns(
                (pl.col("count") / pl.col("count").sum().over(group_cols_eff)).alias(
                    "pct",
                ),
                pl.col("vp_idx").alias("bin_index"),
                pl.col("vp_label").alias("bin_label"),
                pl.lit("Total VP").alias("series_type"),
                pl.lit(-1).alias("direction"),
            )
        )
        out = pl.concat(
            [
                t.select(
                    group_cols_eff
                    + [
                        "bin_index",
                        "bin_label",
                        "series_type",
                        "pct",
                        "direction",
                    ],
                ),
                v.select(
                    group_cols_eff
                    + [
                        "bin_index",
                        "bin_label",
                        "series_type",
                        "pct",
                        "direction",
                    ],
                ),
            ],
        )
        return out.drop("_grp") if "_grp" in out.columns else out

    df_dist_global = make_long_dist(dist_binned, [])
    df_dist_faceted = make_long_dist(dist_binned, ["board", "racer_count"])

    df_turns = df_dist_global.filter(pl.col("direction") == 1)
    df_vp = df_dist_global.filter(pl.col("direction") == -1)

    c_dist_global_top = (
        alt.Chart(df_turns)
        .mark_bar(color=color_turns)
        .encode(
            x=alt.X(
                "bin_label:N",
                sort=alt.SortField("bin_index"),
                axis=alt.Axis(
                    orient="top",
                    title="Game Length (Turns)",
                    labelAngle=-45,
                    labelOverlap="parity",
                ),
            ),
            y=alt.Y("pct:Q", axis=alt.Axis(format="%", title=None)),
            tooltip=["bin_label", alt.Tooltip("pct", format=".1%")],
        )
        .properties(width="container", height=140)
    )

    c_dist_global_bottom = (
        alt.Chart(df_vp)
        .mark_bar(color=color_vp)
        .encode(
            x=alt.X(
                "bin_label:N",
                sort=alt.SortField("bin_index"),
                axis=alt.Axis(
                    orient="bottom",
                    title="Total VP",
                    labelAngle=-45,
                    labelOverlap="parity",
                ),
            ),
            y=alt.Y(
                "pct:Q",
                scale=alt.Scale(reverse=True),
                axis=alt.Axis(format="%", title=None),
            ),
            tooltip=["bin_label", alt.Tooltip("pct", format=".1%")],
        )
        .properties(width="container", height=140)
    )

    c_dist_global = (
        alt.vconcat(c_dist_global_top, c_dist_global_bottom, spacing=10)
        .properties(
            title="Global Distribution: Game Length (Top) vs Total VP (Bottom)",
            background="transparent",
            autosize={"contains": "padding"},
        )
        .configure_view(stroke=None)
        .configure(autosize={"type": "fit-x", "contains": "padding"})
    )

    # --- DEFINITION FIXED: Defined BEFORE usage ---
    scale_facet = alt.Scale(
        domain=["Game Length (Turns)", "Total VP"],
        range=[color_turns, color_vp],
    )

    c_dist_faceted = (
        alt.Chart(df_dist_faceted)
        .transform_calculate(pct_signed="datum.pct * datum.direction")
        .mark_bar()
        .encode(
            x=alt.X(
                "bin_index:O",
                title=None,
                axis=alt.Axis(labels=False, ticks=False),
            ),
            y=alt.Y(
                "pct_signed:Q",
                title=None,
                axis=alt.Axis(format="%", labels=False),
                scale=alt.Scale(domain=[-0.3, 0.3], clamp=True),
            ),
            color=alt.Color("series_type:N", scale=scale_facet, legend=None),
            tooltip=["series_type", "bin_label", alt.Tooltip("pct", format=".1%")],
        )
        .properties(width=300, height=200)
    )

    c_dist_faceted = (
        alt.layer(
            c_dist_faceted,
            alt.Chart().mark_rule(color="#FFF", opacity=0.3).encode(y=alt.datum(0)),
            data=df_dist_faceted,
        )
        .facet(
            row=alt.Row("board:N", title="Board"),
            column=alt.Column("racer_count:N", title="Player Count"),
        )
        .properties(background="transparent")
        .configure_view(stroke=None)
    )

    # --- 5. MATCHUPS & ENV ---
    use_pct = matchup_metric_toggle.value
    metric_col = "percentage_shift" if use_pct else "residual_matchup"
    c_matrix = (
        alt.Chart(matchup_df)
        .mark_rect()
        .encode(
            x=alt.X("opponent_name:N"),
            y=alt.Y("racer_name:N"),
            color=alt.Color(
                f"{metric_col}:Q",
                scale=alt.Scale(
                    range=["#AD1457", "#F06292", "#3E3B45", "#42A5F5", "#0D47A1"],
                    domainMid=0,
                ),
                legend=alt.Legend(format=("+.1%" if use_pct else "+.2f")),
            ),
            tooltip=[
                "racer_name",
                "opponent_name",
                alt.Tooltip("percentage_shift:Q", format="+.1%"),
            ],
        )
        .properties(
            title="Matchup Matrix",
            width="container",
            height=CHART_HEIGHT,
            background=BG_COLOR,
        )
    )

    racer_baselines = joined_env.group_by("racer_name").agg(
        pl.col("final_vp").mean().alias("racer_global_avg_vp"),
    )
    env_stats = (
        joined_env.group_by(["racer_name", "board", "racer_count"])
        .agg(pl.col("final_vp").mean().alias("cond_avg_vp"))
        .join(racer_baselines, on="racer_name", how="left")
        .with_columns(
            (
                (pl.col("cond_avg_vp") - pl.col("racer_global_avg_vp"))
                / pl.col("racer_global_avg_vp")
            ).alias("relative_shift"),
            (pl.col("cond_avg_vp") - pl.col("racer_global_avg_vp")).alias(
                "absolute_shift",
            ),
            (
                pl.col("racer_count").cast(pl.String)
                + "p\n"
                + pl.col("board").cast(pl.String)
            ).alias("env_label"),
        )
    )
    env_sort_order = (
        env_stats.select(["board", "racer_count", "env_label"])
        .unique()
        .sort(["board", "racer_count"])
        .get_column("env_label")
        .to_list()
    )

    c_env = (
        alt.Chart(env_stats)
        .mark_rect()
        .encode(
            x=alt.X("env_label:N", sort=env_sort_order),
            y=alt.Y("racer_name:N"),
            color=alt.Color(
                f"{('relative_shift' if use_pct else 'absolute_shift')}:Q",
                scale=alt.Scale(
                    range=["#AD1457", "#F06292", "#3E3B45", "#42A5F5", "#0D47A1"],
                    domainMid=0,
                ),
                legend=alt.Legend(format=(".0%" if use_pct else "+.2f")),
            ),
            tooltip=[
                "racer_name:N",
                "env_label:N",
                alt.Tooltip("relative_shift:Q", format="+.1%"),
            ],
        )
        .properties(
            title="Env Adaptability",
            width="container",
            height=CHART_HEIGHT,
            background=BG_COLOR,
        )
    )

    # --- 6. TABLES ---
    master_df = stats.sort("mean_vp", descending=True)
    df_overview = master_df.select(
        pl.col("racer_name").alias("Racer"),
        pl.col("mean_vp").round(2).alias("Avg VP"),
        (pl.col("consistency_score") * 100).round(1).alias("Consist%"),
        (pl.col("pct_1st") * 100).round(1).alias("1st%"),
        (pl.col("pct_2nd") * 100).round(1).alias("2nd%"),
        pl.col("races_run").alias("# Races"),
    )
    df_movement = master_df.select(
        pl.col("racer_name").alias("Racer"),
        pl.col("avg_speed_raw").round(2).alias("Speed (Raw)"),
        pl.col("avg_net_movement").round(2).alias("+Rel Abil Speed"),
        (pl.col("avg_active_turns_pct") * 100).round(1).alias("Rolling Turns %"),
        pl.col("avg_pos_self").round(2).alias("Abil +Self"),
        pl.col("avg_neg_self").round(2).alias("Abil -Self"),
    )
    df_abilities = master_df.select(
        pl.col("racer_name").alias("Racer"),
        pl.col("triggers_per_turn").round(2).alias("Trig/Turn"),
        pl.col("self_targets_per_turn").round(2).alias("Self-Targ/Turn"),
        pl.col("own_turn_triggers_per_turn").round(2).alias("OwnTurn Trig/Turn"),
        pl.col("avg_pos_other").round(2).alias("Abil +Other"),
        pl.col("avg_neg_other").round(2).alias("Abil -Other"),
    )
    df_dynamics = master_df.select(
        pl.col("racer_name").alias("Racer"),
        pl.col("avg_race_volatility").cast(pl.Float64).round(2).alias("Volatility"),
        pl.col("avg_race_tightness").cast(pl.Float64).round(2).alias("Tightness"),
        pl.col("avg_game_duration").round(1).alias("Avg Game Len"),
        pl.col("avg_env_triggers").round(1).alias("Race Trigs"),
        (pl.col("avg_env_trip_rate") * 100).round(1).alias("Race Trip%"),
    )
    df_vp = master_df.select(
        pl.col("racer_name").alias("Racer"),
        pl.col("mean_vp").round(2).alias("Avg VP"),
        pl.col("dice_sensitivity").round(2).alias("Dice Sens"),
        pl.col("trigger_dependency").round(2).alias("Ability Trig Sens"),
        pl.col("start_pos_bias").round(2).alias("Start Bias"),
        pl.col("midgame_bias").round(2).alias("MidGame Bias"),
    )

    # --- 7. UI COMPOSITION ---
    desc_ability = mo.md("""
    * **Left Side (Beneficial):** `+Self` (Speed Boosts) and `-Others` (Pushing others/Tripping).  
    * **Right Side (Cost/Altruism):** `-Self` (Investments/Cooldowns) and `+Others` (Helping).  
    * **Sorting:** Racers are ordered by Net Benefit (Total Good - Total Cost).
    """)

    desc_consist = mo.md("""
    * **Y-Axis (Avg VP):** How many points they score on average.  
    * **X-Axis (Stability):** How reliably they hit that average. High stability means low variance.
    """)

    desc_momentum = mo.md("""
    * **Start Bias:** Does starting earlier help them win more VP?.  
    * **Mid-Game Bias:** How many VPs do they gain from from a leading position after 2/3 of the race.
    """)

    desc_excitement = mo.md("""
    * **Tightness:** How close the racers are together throughout the race (Right = Closer).  
    * **Volatility:** How much the lead changes (Top = More Chaos).
    """)

    desc_engine = mo.md("""
    * **Y-Axis (Ability Sensitivity):** Correlation between using abilities and VP. High = Ability trigger counts decide how many VP are earned.
    * **X-Axis (Dice Sensitivity):** Correlation between rolls and VP. High = Needs high (or low) rolls to get VP.
    """)

    global_ui = mo.vstack(
        [
            mo.ui.altair_chart(c_global_1),
            mo.ui.altair_chart(c_global_2),
            mo.ui.altair_chart(c_dist_global),
            mo.ui.altair_chart(c_dist_faceted),
        ],
    )

    chart_height_slider_ui = mo.hstack(
        [
            chart_height_slider,
            mo.md("chart height (px)"),
        ],
        justify="start",
    )
    chart_config_ui = mo.hstack(
        [dynamic_zoom_toggle, chart_height_slider_ui],
        gap=12,
    )
    left_charts_ui = mo.ui.tabs(
        {
            "🎯 Consistency": mo.vstack(
                [
                    c_consist.interactive(),
                    chart_config_ui,
                    desc_consist,
                ],
            ),
            "⚡ Ability Speed": mo.vstack(
                [final_ability_chart, chart_height_slider_ui, desc_ability],
            ),
            "🌊 Momentum": mo.vstack(
                [c_momentum.interactive(), chart_config_ui, desc_momentum],
            ),
            "🔥 Excitement": mo.vstack(
                [c_excitement.interactive(), chart_config_ui, desc_excitement],
            ),
            "⚙️ Engine": mo.vstack(
                [c_engine.interactive(), chart_config_ui, desc_engine],
            ),
            "🌍 Global": global_ui,
        },
    )

    right_ui = mo.ui.tabs(
        {
            "🏆 Overview": mo.vstack(
                [
                    mo.ui.table(df_overview, page_size=50, selection=None),
                    mo.md("**Overview**: Summary stats."),
                ],
            ),
            "⚔️ Interactions": mo.vstack(
                [
                    matchup_metric_toggle,
                    mo.ui.altair_chart(c_matrix),
                    mo.md("**Matchups**: Subject vs Opponent."),
                ],
            ),
            "🌍 Environments": mo.vstack(
                [
                    matchup_metric_toggle,
                    mo.ui.altair_chart(c_env),
                    mo.md("**Environment**: Board/Player Count effects."),
                ],
            ),
            "🏃 Movement": mo.vstack(
                [
                    mo.ui.table(df_movement, page_size=50, selection=None),
                    mo.md("**Movement**: Speed & Efficiency."),
                ],
            ),
            "💎 VP Analysis": mo.vstack(
                [
                    mo.ui.table(df_vp, page_size=50, selection=None),
                    mo.md("**VP Analysis**: Correlations."),
                ],
            ),
            "⚡ Abilities": mo.vstack(
                [
                    mo.ui.table(df_abilities, page_size=50, selection=None),
                    mo.md("**Abilities**: Triggers & Control."),
                ],
            ),
            "🔥 Dynamics": mo.vstack(
                [
                    mo.ui.table(df_dynamics, page_size=50, selection=None),
                    mo.md("**Dynamics**: Chaos & Duration."),
                ],
            ),
        },
    )

    # --- 8. FINAL LAYOUT ---

    # Left Column: Charts
    left_style = {
        "flex": "1 1 1100px",
        "min-width": "0",
        "overflow-x": "auto",
        "max-width": "1100px",  # Constrains width to keep charts square-ish
        "width": "100%",
        "margin": "0 auto",  # Centers the column
    }

    # Right Column: Tables
    right_style = {
        "flex": "1 1 950px",
        "min-width": "0",
        "overflow-x": "auto",
    }

    final_output = mo.hstack(
        [left_charts_ui.style(left_style), right_ui.style(right_style)],
        wrap=True,
        gap=2,
        align="start",
    )

    # Explicitly return/evaluate the output to display it
    final_output
    return


if __name__ == "__main__":
    app.run()
