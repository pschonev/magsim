<div align="center">
  <h1>magsim - A Magical Athlete Simulator</h1>
  <p>A fan-made Python simulation engine and analysis toolkit for the board game <a href="https://boardgamegeek.com/boardgame/454103/magical-athlete">Magical Athlete</a>.</p>
</div>

<p align="center">
  <a href="#installation"><img alt="Python" src="https://img.shields.io/badge/python-3.12%2B-blue?color=539912&logo=python&logoColor=white" /></a>
  <a href="#development"><img alt="CI" src="https://img.shields.io/badge/tests-pytest-green?color=6ca1d8&logo=githubactions&logoColor=white" /></a>
  <a href="#license"><img alt="License" src="https://img.shields.io/badge/license-MIT-blue?color=f6ae00" /></a>
</p>



<p align="center">
  <a href="https://pschonev.github.io/magsim/">
    <picture>
      <!-- Shown in Light Mode -->
      <source media="(prefers-color-scheme: light)" srcset="assets/dashboard-button-light.svg">
      <!-- Shown in Dark Mode / Default -->
      <img alt="✨ View Interactive Dashboard ✨" src="assets/dashboard-button.svg" width="600">
    </picture>
  </a>
</p>

<p align="center">
  <a href="https://boardgamegeek.com/boardgame/454103/magical-athlete">BoardGameGeek</a> ·
  <a href="https://www.cmyk.games/products/magical-athlete">CMYK Games</a> ·
  <a href="https://boardgamegeek.com/blog/1/blogpost/178228/designer-diary-magical-athlete">Designer Diary</a> ·
  <a href="https://elizabethgoodspeed.com/magicalathlete">Art Blog</a>
</p>




---

## What is this?
**Magical Athlete** is a draft-based racing board game where you roll a die to move, but every racer has a game-breaking, unique ability. 

`magsim` translates the physical game into a high-performance Python engine. Capable of running 60+ full races per second with complete state logging, it allows you to:
- **Simulate Races:** Run single game simulations in the command line or UI
- **Data Generation:** Run high-volume batch simulations to generate datasets for analysis
- **Visual Analytics:** Visualize races and analyze aggregated data in an interactive web dashboard that runs fully in your browser (Pyodide)
- **A/B Experiments:** Pit Smart AI against Random AI, compare the impact of racers and measure modifying rules changes the balance via the CLI tool

---

## Quickstart

The fastest way to use `magsim` is **via the [web app](https://pschonev.github.io/magsim/)**. Python runs in your browser (Pyodide), so the first load downloads the runtime.

To run `magsim` locally, I recommend using `uv` ([Install `uv` here](https://docs.astral.sh/uv/getting-started/installation/)). 

**1. Run a single test race:**
```bash
uvx magsim game
```

**2. Run a game with specific configuration:**
```bash
uvx magsim game -n 6 -b standard -r Egg Magician
```

**3. Launch the interactive dashboard locally:**
```bash
uvx magsim gui
```

---

## Command Line Interface

`magsim` ships with a powerful CLI for running simulations, conducting A/B testing, and generating datasets. 

***

### `magsim game`
Run a single game simulation. If no board or racers are specified, the engine will pick defaults and a random seed.

| Option | Flag | Description |
| :--- | :---: | :--- |
| **Racers** | `-r, --racers` | Space-separated list of racer names to include. |
| **Player Count** | `-n, --number` | Target number of racers. Roster is filled with unique randoms if fewer are provided. |
| **Board** | `-b, --board` | The name of the board to race on. |
| **RNG Seed** | `-s, --seed` | Integer seed for reproducible races. |
| **Config File** | `-c, --config` | Path to a TOML configuration file. |
| **Encoding** | `-e, --encoding` | Base64 encoded configuration string. |
| **House Rules** | `-H, --houserule` | Repeatable key-value pairs for custom rules (e.g., `start_pos=5`). |
| **Max Turns** | `--max-turns` | Safety cutoff for infinite loops. *(Default: `200`)* |

> **Config Precedence:** 1. CLI Args ➔ 2. Base64 Encoding ➔ 3. TOML Config ➔ 4. Defaults

**Examples:**
```bash
# Basic quickstart
magsim game -n 6 -b WildWilds

# Specific matchups with a fixed seed
magsim game -r Mouth BabaYaga -n 5 -s 123
```

***

### `magsim batch`
Run high-volume batch simulations driven by a TOML configuration. Saves results to `.parquet` files for the frontend dashboard.

| Option | Flag | Description |
| :--- | :---: | :--- |
| **Config** | `<path>` | *(Required)* Path to the TOML simulation config file. |
| **Runs** | `--runs` | Override the number of runs per combination. |
| **Max Runs** | `--max` | Override the maximum total runs across the batch. |
| **Turn Limit** | `--turns` | Override the max turns per race. |
| **Seed Offset** | `--seed-offset` | Offset for RNG seeds to prevent overlap. *(Default: `0`)* |
| **Results Dir** | `--results-dir` | Where the database and Parquet files go. *(Default: `results`)* |
| **Force** | `-f, --force` | Delete existing Parquet/DuckDB files in the results directory without prompting. |

The config can name `required_racers`: those racers are in every game and the rest of each team is drawn from the pool (see `configs/mush_only.toml`).

**Examples:**
```bash
magsim batch configs/sim.toml --runs 50 --max 100000 
magsim batch configs/sim.toml --force
```

***

### `magsim compare`
Run comparative A/B experiments. Appends run histories to Parquet files in `results/`. All commands accept `-n` (total games) and `-o` (save markdown report to path).

| Command | Target | Description |
| :--- | :--- | :--- |
| `ai` | `<RACER>` | Pits a Smart AI against a Baseline Random AI. |
| `rule` | `<k=v>` | Default rules vs a modified setting. |
| `racer` | `<RACER>` | The overall impact of one specific racer on the field. |

**Examples:**
```bash
# Test how 'Mouth' performs with Smart AI vs Random AI over 1000 games
magsim compare ai Mouth -n 1000 -o results/ai_mouth.md

# Evaluate the impact of a house rule (e.g., Mastermind steals 1st place)
magsim compare rule hr_mastermind_steal_1st=True -n 2000

# See how 'BabaYaga' warps the win rates of the rest of the field
magsim compare racer BabaYaga -n 3000
```

***

### `magsim recompute`
Internal data analysis and aggregation tools. Both commands accept `-f, --folder` to target a specific data directory *(Default: `results/`)*.

| Command | Description | Example |
| :--- | :--- | :--- |
| `aggregate` | Recomputes internal statistical aggregates. | `magsim recompute aggregate` |
| `stats` | Generates a fresh `racer_stats.json` file. | `magsim recompute stats -f custom_results/` |

***

### `magsim gui`
Instantly launch the interactive simulation analysis dashboard.
```bash
magsim gui
```

---

## 🖥️ Run GUI Locally

If you want to modify the dashboard or analyze custom datasets, you can run the project locally from a cloned repository.

**1. Clone the repository:**
```bash
git clone https://github.com/pschonev/magical-athlete-simulator.git
cd magical-athlete-simulator
```

**2. Generate your custom dataset:**
```bash
magsim batch configs/sim.toml
```
The dashboard's own dataset takes two runs, which one command does (it replaces `results/` and `results_mush/`):
```bash
uv run poe batch   # main batch (configs/twisty_oversampled.toml) + Mush-only games + Mush's merged power pairs
uv run poe mush    # only the Mush-only games and the pairs, when the main batch already exists
```
Mush's power pairs need far more Mush games than a uniform batch holds. The Mush-only games go to `results_mush/` and are never merged into `results/`, because they would make Mush a third of all races and tilt every other statistic. Only a small table of pairs (`results/mush_pairs.parquet`, about 10 KB) is merged and shipped with the dashboard; `poe release-prep` copies it into the committed `docs/results` snapshot next to the two datasets. A dataset you upload in the dashboard has no such table, so its Mush charts use only its own Mush games (and stay empty without enough of them).

**3. Build and start the dashboard with your results:**
```bash
uv run poe web-build   # uses results/ if present (error if incomplete), else the committed docs/results snapshot
uv run magsim gui      # serves web/dist locally; without a build it opens the hosted app
```
Requires Node.js. During development use `uv run poe web-dev` instead.

---

## Changelog
See the [CHANGELOG.md](https://github.com/pschonev/magical-athlete-simulator/blob/main/CHANGELOG.md) for version history.
