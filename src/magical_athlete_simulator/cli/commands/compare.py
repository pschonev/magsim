from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any

import cappa
import polars as pl

from magical_athlete_simulator.analysis.baseline import (
    ExperimentResult,
    run_ai_comparison,
    run_racer_impact_comparison,
    run_rule_comparison,
)
from magical_athlete_simulator.core.types import RacerName  # noqa: TC001

RESULTS_DIR = Path("results")
AI_STATS_FILE = RESULTS_DIR / "ai_comparison_history.parquet"
RULE_STATS_FILE = RESULTS_DIR / "rule_comparison_history.parquet"
RACER_IMPACT_FILE = RESULTS_DIR / "racer_impact_history.parquet"

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())
logger.propagate = False


@cappa.command(name="ai", help="Compare AI performance (Smart vs Baseline).")
@dataclass
class CompareAICommand:
    racer: Annotated[RacerName, cappa.Arg(help="Racer to test.")]
    number: Annotated[int, cappa.Arg(short="-n", default=500, help="Number of games.")]
    output: Annotated[
        Path | None,
        cappa.Arg(short="-o", help="Save report to file."),
    ] = None

    def __call__(self):
        logger.info(f"Running comparison for {self.racer} (N={self.number})...")
        logging.getLogger("magical_athlete").setLevel(logging.CRITICAL)

        result = run_ai_comparison(self.racer, self.number)

        header = f"{'Metric':<20} | {'Baseline (Ctrl)':<15} | {'Smart (Trt)':<15} | {'Delta':<10} | {'Change':<10}"
        sep = "-" * len(header)
        rows = [
            f"{'Win Rate':<20} | {result.winrate_control:<15.1%} | {result.winrate_treatment:<15.1%} | {result.winrate_delta:<+10.1%} | {result.winrate_pct_change:<+10.1%}",
            f"{'Avg VP':<20} | {result.vp_control:<15.1f} | {result.vp_treatment:<15.1f} | {result.vp_delta:<+10.1f} | {result.vp_pct_change:<+10.1%}",
            f"{'Max VP (Debug)':<20} | {result.max_vp_control:<15} | {result.max_vp_treatment:<15} | {'-':<10} | {'-':<10}",
            f"{'Speed (gms/s)':<20} | {result.speed_control:<15.1f} | {result.speed_treatment:<15.1f} | {result.speed_delta:<+10.1f} | {result.speed_pct_change:<+10.1%}",
        ]
        logger.info("\n" + "\n".join([sep, header, sep, *rows, sep]) + "\n")  # noqa: G003

        if self.output:
            with Path(self.output).open("w") as f:
                f.write(f"# AI Comparison: {self.racer}\n\n")
                f.write("| Metric | Baseline | Smart | Delta | Change |\n")
                f.write("| --- | --- | --- | --- | --- |\n")
                f.write(
                    f"| Win Rate | {result.winrate_control:.1%} | {result.winrate_treatment:.1%} | {result.winrate_delta:+.1%} | {result.winrate_pct_change:+.1%} |\n",
                )
                f.write(
                    f"| Avg VP | {result.vp_control:.1f} | {result.vp_treatment:.1f} | {result.vp_delta:+.1f} | {result.vp_pct_change:+.1%} |\n",
                )
                f.write(
                    f"| Max VP | {result.max_vp_control} | {result.max_vp_treatment} | - | - |\n",
                )
                f.write(f"\n*Run ID: {result.run_id}*")
            logger.info(f"Report saved to {self.output}")

        _save_results(AI_STATS_FILE, [result], {})


@cappa.command(name="rule", help="Compare Default vs Modified Rules.")
@dataclass
class CompareRuleCommand:
    rule_setting: Annotated[str, cappa.Arg(help="Rule to test (e.g. 'start_pos=5').")]
    number: Annotated[int, cappa.Arg(short="-n", default=1000, help="Total games.")]
    output: Annotated[
        Path | None,
        cappa.Arg(short="-o", help="Save report to file."),
    ] = None

    def __call__(self):
        if "=" not in self.rule_setting:
            raise cappa.Exit("Rule must be format 'key=value'", code=1)

        key, raw_val = self.rule_setting.split("=", 1)
        val: Any = (
            int(raw_val)
            if raw_val.isdigit()
            else (
                True
                if raw_val.lower() == "true"
                else (False if raw_val.lower() == "false" else raw_val)
            )
        )

        logger.info(f"Testing Rule Shift: {key}={val} (N={self.number})...")
        logging.getLogger("magical_athlete").setLevel(logging.CRITICAL)

        results = run_rule_comparison(key, val, self.number)
        results.sort(key=lambda x: x.vp_pct_change, reverse=True)

        logger.info(f"\n--- Impact of {key}={val} (Sorted by VP Impact) ---\n")
        header = (
            f"{'Racer':<15} | {'N':<4} | "
            f"{'Win Base':<8} | {'Win New':<8} | {'Win Δ':<8} | {'Win Rel':<8} | "
            f"{'VP Base':<7} | {'VP New':<7} | {'VP Δ':<6} | {'VP Rel':<7}"
        )
        logger.info(header)
        logger.info("-" * len(header))

        for res in results:
            if res.games_played < 20:
                continue

            # Updated row formatting to match the new header
            logger.info(
                f"{res.racer:<15} | {res.games_played:<4} | "
                f"{res.winrate_control:<8.1%} | {res.winrate_treatment:<8.1%} | {res.winrate_delta:<+8.1%} | {res.winrate_pct_change:<+8.1%} | "
                f"{res.vp_control:<7.1f} | {res.vp_treatment:<7.1f} | {res.vp_delta:<+6.1f} | {res.vp_pct_change:<+7.1%}",
            )

        _save_results(
            RULE_STATS_FILE,
            results,
            {"rule_key": key, "rule_value": str(val)},
        )


@cappa.command(name="racer", help="Analyze impact of a racer on the field.")
@dataclass
class CompareRacerCommand:
    racer: Annotated[RacerName, cappa.Arg(help="Target racer to analyze.")]
    number: Annotated[int, cappa.Arg(short="-n", default=1000, help="Total games.")]
    output: Annotated[
        Path | None,
        cappa.Arg(short="-o", help="Save report to file."),
    ] = None

    def __call__(self):
        logger.info(f"Analyzing Impact of {self.racer} (N={self.number})...")
        logging.getLogger("magical_athlete").setLevel(logging.CRITICAL)

        results = run_racer_impact_comparison(self.racer, self.number)

        opponents = [r for r in results if r.racer != self.racer]
        target_res = next((r for r in results if r.racer == self.racer), None)
        opponents.sort(key=lambda x: x.vp_pct_change, reverse=True)

        logger.info(f"\n--- Target Statistics: {self.racer} ---")
        if target_res:
            logger.info(f"Win Rate: {target_res.winrate_treatment:.1%}")
            logger.info(f"Avg VP:   {target_res.vp_treatment:.1f}")
            logger.info(f"Max VP:   {target_res.max_vp_treatment}")

        logger.info("\n--- Impact on Opponents (Sorted by Relative VP Change) ---\n")
        header = f"{'Racer':<15} | {'N':<4} | {'Win% w/o':<8} | {'Win% w/':<8} | {'Win% Rel':<8} | {'VP w/o':<6} | {'VP w/':<6} | {'VP Rel':<7} | {'Max VP':<3}"
        sep = "-" * len(header)
        logger.info(header)
        logger.info(sep)

        for res in opponents:
            if res.games_played < 20:
                continue
            max_v = max(res.max_vp_control, res.max_vp_treatment)
            logger.info(
                f"{res.racer:<15} | {res.games_played:<4} | {res.winrate_control:<8.1%} | {res.winrate_treatment:<8.1%} | {res.winrate_pct_change:<+8.1%} | {res.vp_control:<6.1f} | {res.vp_treatment:<6.1f} | {res.vp_pct_change:<+7.1%} | {max_v:<3}",
            )

        _save_results(RACER_IMPACT_FILE, results, {"target_racer": str(self.racer)})


def _save_results(path: Path, results: list[ExperimentResult], extras: dict):
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    for res in results:
        row = {
            "run_id": res.run_id,
            "timestamp": res.timestamp,
            "racer_name": str(res.racer),
            "games_played": res.games_played,
            "winrate_control": res.winrate_control,
            "winrate_treatment": res.winrate_treatment,
            "winrate_delta": res.winrate_delta,
            "winrate_pct_change": res.winrate_pct_change,
            "vp_control": res.vp_control,
            "vp_treatment": res.vp_treatment,
            "vp_delta": res.vp_delta,
            "vp_pct_change": res.vp_pct_change,
            "max_vp_control": res.max_vp_control,
            "max_vp_treatment": res.max_vp_treatment,
            "speed_control": res.speed_control,
            "speed_treatment": res.speed_treatment,
        }
        row.update(extras)
        rows.append(row)

    if not rows:
        return

    new_df = pl.DataFrame(rows)
    if path.exists():
        try:
            existing = pl.read_parquet(path)
            pl.concat([existing, new_df], how="diagonal").write_parquet(path)
            logger.info(f"✅ Data appended to {path}")
        except Exception:  # noqa: BLE001
            new_df.write_parquet(path)
            logger.info(f"✅ Data saved to {path} (overwrite/reset)")
    else:
        new_df.write_parquet(path)
        logger.info(f"✅ Data saved to {path}")


@cappa.command(name="compare", help="Run comparative experiments.")
@dataclass
class CompareCommand:
    subcommand: cappa.Subcommands[
        CompareAICommand | CompareRuleCommand | CompareRacerCommand
    ]
