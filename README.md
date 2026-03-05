<div align="center">
  <h1>magsim - A Magical Athlete Simulator</h1>
  <p>A fan-made Python simulation engine and analysis toolkit for the board game <a href="https://boardgamegeek.com/boardgame/454103/magical-athlete">Magical Athlete</a>.</p>
</div>

<p align="center">
  <a href="#installation"><img alt="Python" src="https://img.shields.io/badge/python-3.12%2B-blue" /></a>
  <a href="#development"><img alt="CI" src="https://img.shields.io/badge/tests-pytest-success" /></a>
  <a href="#license"><img alt="License" src="https://img.shields.io/badge/license-MIT-informational" /></a>
</p>

<p align="center">
  <a href="https://pschonev.github.io/magsim/">
    <img src="https://img.shields.io/badge/✨_View_Interactive_Dashboard_✨-181c1a?style=for-the-badge&logo=marimo&logoColor=white&labelColor=181c1a" height="45" alt="Dashboard Link">
  </a>
  <br><br>
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
- **Visual Analytics:** Visualize races and analyze aggregated data in a reactive `marimo` dashboard
- **A/B Experiments:** Pit Smart AI against Random AI, compare the impact of racers and measure modifying rules changes the balance via the CLI tool

---

## Quickstart

The fastest way to use `magsim` is **via the [web-based frontend](LINK)**. The dashboard runs in WASM-mode, expect long loading times.

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

## CLI

This project ships a `magsim` command with multiple subcommands for running simulations and doing analysis.

***

## `game` — Run one simulation

Run a single game simulation. If you don’t specify racers/board/seed, it will pick defaults (and a random seed).

```bash
magsim game [OPTIONS]
```

Arguments/options:

- `-r, --racers <RACER...>`: Space-separated list of racer names
- `-n, --number <INT>`: Target number of racers. If fewer racers were provided than this number, the roster is filled with unique random racers
- `-b, --board <BOARD>`: Board name
- `-s, --seed <INT>`: RNG seed
- `-c, --config <PATH>`: Path to a TOML config file
- `-e, --encoding <STR>`: Base64 encoded configuration
- `-H, --houserule <KEY=VALUE...>`: House rules (repeatable / multiple values)
- `--max-turns <INT>`: Max turns before stopping (default: `200`)

Config precedence (highest wins):
1. CLI args
2. `--encoding`
3. `--config` TOML file
4. Defaults

Examples:

```bash
magsim game
magsim game -n 6 -b WildWilds
magsim game -r Mouth BabaYaga -n 5 -s 123
magsim game -H start_pos=5 -H timing_mode=BFS
magsim game -c configs/quick.toml
magsim game -e "<base64>"
```

***

## `gui` — Launch dashboard

Launch the interactive simulation analysis dashboard using `uvx`.

```bash
magsim gui
```

***


## `batch` — Run many simulations from a config

Run batch simulations driven by a TOML simulation config. Saves results to parquets which can be loaded in frontend.

```bash
magsim batch <config.toml> [OPTIONS]
```

Arguments/options:

- `<config.toml>`: Path to TOML simulation config file
- `--runs <INT>`: Override runs per combination
- `--max <INT>`: Override maximum total runs
- `--turns <INT>`: Override max turns per race
- `--seed-offset <INT>`: Offset for RNG seeds (default: `0`)
- `-f, --force`: Delete existing `.parquet` / `.duckdb` files in `results/` without prompting

Behavior:
- Writes to `results/`
- If `results/` already contains `.parquet` files, it prompts before deleting unless `--force` is set
- Skips configs already present in the database by hash
- Periodically flushes data to disk in batches

Example:

```bash
magsim batch configs/sim.toml --runs 50 --max 100000 --turns 300
magsim batch configs/sim.toml --force
```

***

## `compare` — Comparative experiments

Appends run histories to Parquet files in `results/` (AI history, rule history, racer-impact history).

### `compare ai` — Smart vs Baseline AI

```bash
magsim compare ai <RACER> [-n INT] [-o PATH]
```

- `<RACER>`: Racer to test
- `-n <INT>`: Number of games (default: `500`)
- `-o <PATH>`: Save a Markdown report to a file

Example:

```bash
magsim compare ai Mouth -n 1000 -o results/ai_mouth.md
```

### `compare rule` — Default vs modified rule

```bash
magsim compare rule <key=value> [-n INT] [-o PATH]
```

- `<key=value>`: Rule setting to test (e.g. `start_pos=5`, `some_flag=true`)
- `-n <INT>`: Total games (default: `1000`)
- `-o <PATH>`: Save a report to a file

Example:

```bash
magsim compare rule hr_mastermind_steal_1st=True -n 2000
```

### `compare racer` — Impact of one racer on the field

```bash
magsim compare racer <RACER> [-n INT] [-o PATH]
```

- `<RACER>`: Target racer
- `-n <INT>`: Total games (default: `1000`)
- `-o <PATH>`: Save a report to a file

Example:

```bash
magsim compare racer BabaYaga -n 3000
```

***

## `recompute` — Data analysis tools

### `recompute aggregate` — Recompute internal aggregates

```bash
magsim recompute aggregate [-f PATH]
```

- `-f, --folder <PATH>`: Data directory containing parquet files (default: `results/`)

### `recompute stats` — Generate `racer_stats.json`

```bash
magsim recompute stats [-f PATH]
```

- `-f, --folder <PATH>`: Data directory containing parquet files (default: `results/`)

Examples:

```bash
magsim recompute aggregate
magsim recompute stats -f results
```

# Run GUI locally
To make changes and look at custom data, you may clone this repository. You can get your own data via a config file and the `magsim batch` command. You may then start the dashboard and load that data by running `uv run marimo run frontend/magical_athlete_analysis.py`.

## Changelog
See the [CHANGELOG.md](https://github.com/pschonev/magical-athlete-simulator/blob/main/CHANGELOG.md) for version history.
