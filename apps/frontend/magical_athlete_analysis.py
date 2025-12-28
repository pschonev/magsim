import marimo

__generated_with = "0.18.4"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import math
    from magical_athlete_simulator.engine.scenario import GameScenario, RacerConfig
    from magical_athlete_simulator.engine.board import BOARD_DEFINITIONS
    return BOARD_DEFINITIONS, GameScenario, RacerConfig, math, mo


@app.cell
def _(math):
    # Space colors: Green start, alternating grey/white, red finish
    space_colors = ["#4CAF50"] + ["#F5F5F5", "#E0E0E0"] * 14 + ["#F44336"]
    space_colors = space_colors[:30]

    # Racer colors (map racer names to colors)
    racer_colors = {
        "Banana": "#FFD700",      # Gold
        "Centaur": "#8B4513",     # Brown
        "Magician": "#9370DB",    # Purple
        "Scoocher": "#FF6347",    # Tomato
        "Gunk": "#228B22",        # Forest Green
    }

    def generate_racetrack_positions(num_spaces, start_x, start_y, straight_len, radius):
        positions = []
        perimeter = (2 * straight_len) + (2 * math.pi * radius)
        step_distance = perimeter / num_spaces

        right_circle_cx = start_x + straight_len
        right_circle_cy = start_y - radius
        left_circle_cx = start_x
        left_circle_cy = start_y - radius

        for i in range(num_spaces):
            dist = i * step_distance

            if dist < straight_len:
                x = start_x + dist
                y = start_y
                angle = 0
            elif dist < (straight_len + math.pi * radius):
                arc_dist = dist - straight_len
                fraction = arc_dist / (math.pi * radius)
                theta_rad = (math.pi / 2) - (fraction * math.pi)
                x = right_circle_cx + radius * math.cos(theta_rad)
                y = right_circle_cy + radius * math.sin(theta_rad)
                angle = math.degrees(theta_rad) + 90
            elif dist < (2 * straight_len + math.pi * radius):
                top_dist = dist - (straight_len + math.pi * radius)
                x = (start_x + straight_len) - top_dist
                y = start_y - (2 * radius)
                angle = 180
            else:
                arc_dist = dist - (2 * straight_len + math.pi * radius)
                fraction = arc_dist / (math.pi * radius)
                theta_rad = (-math.pi / 2) - (fraction * math.pi)
                x = left_circle_cx + radius * math.cos(theta_rad)
                y = left_circle_cy + radius * math.sin(theta_rad)
                angle = math.degrees(theta_rad) + 90

            positions.append((x, y, angle))

        return positions

    board_positions = generate_racetrack_positions(
        num_spaces=30, start_x=120, start_y=350, straight_len=350, radius=100
    )
    return board_positions, racer_colors, space_colors


@app.cell
def _(mo):
    # Reset button to restart the simulation
    reset_button = mo.ui.button(label="🔄 Reset Simulation")

    # Scenario configuration
    scenario_seed = mo.ui.number(start=1, stop=10000, value=42, label="Random Seed")

    mo.hstack([reset_button, scenario_seed], justify="start")

    return reset_button, scenario_seed


@app.cell
def _(
    BOARD_DEFINITIONS,
    GameScenario,
    RacerConfig,
    mo,
    reset_button,
    scenario_seed,
):
    import logging
    from io import StringIO
    from rich.console import Console
    from rich.logging import RichHandler
    from magical_athlete_simulator.engine.logging import RichMarkupFormatter, GameLogHighlighter

    # Trigger re-run when reset is clicked
    reset_button.value

    # Create log capture
    log_buffer = StringIO()
    log_console = Console(file=log_buffer, width=120)

    log_handler = RichHandler(
        console=log_console,
        markup=True,
        show_path=False,
        show_time=False,
        highlighter=GameLogHighlighter(),
    )
    log_handler.setFormatter(RichMarkupFormatter())

    base_logger = logging.getLogger("magical_athlete")
    base_logger.handlers.clear()
    base_logger.addHandler(log_handler)
    base_logger.setLevel(logging.INFO)

    # Create scenario
    scenario = GameScenario(
        racers_config=[
            RacerConfig(idx=0, name="Banana", start_pos=0),
            RacerConfig(idx=1, name="Centaur", start_pos=0),
            RacerConfig(idx=2, name="Magician", start_pos=0),
            RacerConfig(idx=3, name="Scoocher", start_pos=0),
        ],
        seed=scenario_seed.value,
        board=BOARD_DEFINITIONS["standard"](),
    )

    engine = scenario.engine

    # PRE-SIMULATE THE ENTIRE GAME
    game_history = []

    with mo.status.spinner(title="Simulating game...", subtitle="Running turns", remove_on_exit=True):
        while not engine.state.race_over:
            log_start_pos = log_buffer.tell()
        
            snapshot = {
                "turn": len(game_history),
                "positions": [r.position for r in engine.state.racers],
                "names": [r.name for r in engine.state.racers],
                "tripped": [r.tripped for r in engine.state.racers],
                "current_racer": engine.state.current_racer_idx,
                "log_start": log_start_pos,
            }
        
            scenario.run_turn()
        
            snapshot["log_end"] = log_buffer.tell()
            game_history.append(snapshot)
        
            # Safety limit to prevent infinite loops
            if len(game_history) > 200:
                break

    total_turns = len(game_history)

    mo.md(f"✅ **Simulation complete!** Total turns: {total_turns}")
    return game_history, log_buffer, total_turns


@app.cell
def _(mo, total_turns):
    # Slider dynamically sized to the actual game length
    turn_slider = mo.ui.slider(
        start=0, 
        stop=max(0, total_turns - 1),  # Dynamic max based on actual game
        step=1, 
        label="Turn to View", 
        value=0
    )
    return (turn_slider,)


@app.cell
def _(game_history, turn_slider):


    current_turn_data = game_history[turn_slider.value] if turn_slider.value < len(game_history) else None



    return (current_turn_data,)


@app.cell
def _(turn_slider):
    turn_slider
    return


@app.cell
def _():
    return


@app.cell
def _(
    board_positions,
    current_turn_data,
    math,
    mo,
    racer_colors,
    space_colors,
):
    def render_game_track(turn_data, positions_map, colors_map):
        if not turn_data:
            return "<p>No game data yet. Move the slider.</p>"

        svg_elements = []
        rw, rh = 50, 30

        # Draw track spaces
        for i, (cx, cy, rot) in enumerate(positions_map):
            transform = f"rotate({rot}, {cx}, {cy})"
            svg_elements.append(
                f'<rect x="{cx - rw / 2:.1f}" y="{cy - rh / 2:.1f}" width="{rw}" height="{rh}" '
                f'fill="{colors_map[i]}" stroke="#555" stroke-width="1" transform="{transform}" rx="4" />'
            )
            svg_elements.append(
                f'<text x="{cx:.1f}" y="{cy:.1f}" dy="4" font-family="sans-serif" font-size="10" font-weight="bold" '
                f'text-anchor="middle" fill="#333" transform="{transform}">{i}</text>'
            )

        # Group racers by position
        occupancy = {}
        for idx, pos in enumerate(turn_data["positions"]):
            if pos not in occupancy:
                occupancy[pos] = []
            occupancy[pos].append({
                "name": turn_data["names"][idx],
                "color": racer_colors.get(turn_data["names"][idx], "#888"),
                "tripped": turn_data["tripped"][idx],
                "is_current": idx == turn_data["current_racer"]
            })

        # Draw racers
        for space_idx, racers_here in occupancy.items():
            if space_idx >= 30:
                continue

            bx, by, brot = positions_map[space_idx]
            count = len(racers_here)

            if count == 1:
                offsets = [(0, 0)]
            elif count == 2:
                offsets = [(-15, 0), (15, 0)]
            elif count == 3:
                offsets = [(-15, -8), (15, -8), (0, 8)]
            elif count == 4:
                offsets = [(-15, -8), (15, -8), (-15, 8), (15, 8)]
            else:
                offsets = [(-18, -8), (18, -8), (0, 0), (-18, 8), (18, 8)]

            for i, racer in enumerate(racers_here):
                if i >= len(offsets):
                    break
                ox, oy = offsets[i]

                rad = math.radians(brot)
                rot_ox = ox * math.cos(rad) - oy * math.sin(rad)
                rot_oy = ox * math.sin(rad) + oy * math.cos(rad)

                # Circle with glow effect for current racer
                stroke_color = "yellow" if racer["is_current"] else "white"
                stroke_width = "2.5" if racer["is_current"] else "1.5"

                svg_elements.append(
                    f'<circle cx="{bx + rot_ox:.1f}" cy="{by + rot_oy:.1f}" r="7" '
                    f'fill="{racer["color"]}" stroke="{stroke_color}" stroke-width="{stroke_width}" />'
                )

                # X marker if tripped
                if racer["tripped"]:
                    svg_elements.append(
                        f'<text x="{bx + rot_ox:.1f}" y="{by + rot_oy:.1f}" dy="4" '
                        f'font-size="14" font-weight="bold" fill="red" text-anchor="middle">X</text>'
                    )

        return f"""
        <svg width="600" height="500" style="background: #eef; border: 2px solid #ccc; border-radius: 8px;">
            <ellipse cx="295" cy="250" rx="150" ry="70" fill="#C8E6C9" stroke="none" />
            {"".join(svg_elements)}
        </svg>
        """

    mo.Html(render_game_track(current_turn_data, board_positions, space_colors))
    return


@app.cell
def _(current_turn_data, log_buffer, mo):
    def render_turn_logs(turn_data, log_buf):
        if not turn_data:
            return mo.md("_No logs available yet._")
    
        # Get the full log content
        full_logs = log_buf.getvalue()
    
        # Extract the substring for this turn
        start = turn_data["log_start"]
        end = turn_data["log_end"]
        turn_log_text = full_logs[start:end].strip()
    
        if not turn_log_text:
            return mo.md("_No logs for this turn._")
    
        return mo.ui.code_editor(
            value=turn_log_text,
            language="text",
            disabled=True,
            label=f"Turn {turn_data['turn']} - {turn_data['names'][turn_data['current_racer']]}"
        )

    render_turn_logs(current_turn_data, log_buffer)

    return


@app.cell
def _(current_turn_data, mo):
    if current_turn_data:
        status_md = f"""
        ## Turn {current_turn_data['turn']} Summary

        **Current Racer:** {current_turn_data['names'][current_turn_data['current_racer']]}

        | Racer | Position | Status |
        |-------|----------|--------|
        """

        for idx, name in enumerate(current_turn_data['names']):
            status = "🔴 Tripped" if current_turn_data['tripped'][idx] else "✅ Active"
            status_md += f"| {name} | {current_turn_data['positions'][idx]} | {status} |\n"

        mo.md(status_md)
    else:
        mo.md("_Start the game by moving the slider._")
    return


if __name__ == "__main__":
    app.run()
