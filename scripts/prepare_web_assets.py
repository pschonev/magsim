"""Build magsim wheel, export Arrow IPC datasets, and write web runtime manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

from magsim.analysis.export import export_parquet_to_ipc

PYODIDE_VERSION = "314.0.8"
DATASET_FILES = ("races.parquet", "racer_results.parquet")
BATCH_RESULTS_DIR = Path("results")
SNAPSHOT_RESULTS_DIR = Path("docs") / "results"


def build_wheel(repo_root: Path, wheels_dir: Path) -> Path:
    """Build a fresh magsim wheel into wheels_dir/<content hash>/ and return its path."""
    wheels_dir.mkdir(parents=True, exist_ok=True)
    for old_wheel in wheels_dir.glob("magsim-*.whl"):
        old_wheel.unlink()
    for old_dir in wheels_dir.iterdir():
        if old_dir.is_dir():
            shutil.rmtree(old_dir)

    subprocess.run(
        ["uv", "build", "--wheel", "--out-dir", str(wheels_dir)],
        cwd=repo_root,
        check=True,
    )
    wheels = sorted(wheels_dir.glob("magsim-*.whl"))
    if not wheels:
        msg = f"No magsim wheel produced in {wheels_dir}"
        raise RuntimeError(msg)
    wheel = wheels[-1]
    digest = hashlib.sha256(wheel.read_bytes()).hexdigest()[:12]
    hashed_dir = wheels_dir / digest
    hashed_dir.mkdir()
    return wheel.replace(hashed_dir / wheel.name)


def resolve_results_dir(repo_root: Path, override: Path | None) -> Path:
    """Explicit dir, else the latest batch output in results/, else the committed docs/results snapshot."""
    if override is not None:
        return override
    batch_dir = repo_root / BATCH_RESULTS_DIR
    if all((batch_dir / name).exists() for name in DATASET_FILES):
        return batch_dir
    return repo_root / SNAPSHOT_RESULTS_DIR


def export_ipc(src_parquet: Path, dst_ipc: Path) -> None:
    """Export a Parquet dataset to zstd Arrow IPC."""
    if not src_parquet.exists():
        msg = f"Missing source dataset: {src_parquet}"
        raise FileNotFoundError(msg)
    export_parquet_to_ipc(src_parquet, dst_ipc, compression="zstd")


def prepare_web_assets(
    repo_root: Path,
    *,
    public_dir: Path | None = None,
    results_source_dir: Path | None = None,
) -> dict[str, str]:
    """Build wheel + Arrow IPC assets into web/public and write runtime-manifest.json."""
    target_public = public_dir or (repo_root / "web" / "public")
    source_results = resolve_results_dir(repo_root, results_source_dir)
    print(f"Datasets: {source_results}", file=sys.stderr)

    wheels_dir = target_public / "wheels"
    results_dir = target_public / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    wheel_path = build_wheel(repo_root, wheels_dir)
    races_ipc = results_dir / "races.zstd.ipc"
    results_ipc = results_dir / "racer_results.zstd.ipc"

    export_ipc(source_results / "races.parquet", races_ipc)
    export_ipc(source_results / "racer_results.parquet", results_ipc)

    manifest = {
        "wheel": wheel_path.relative_to(target_public).as_posix(),
        "races": f"results/{races_ipc.name}",
        "racerResults": f"results/{results_ipc.name}",
        "pyodideVersion": PYODIDE_VERSION,
    }
    manifest_path = target_public / "runtime-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--results-dir",
        type=Path,
        help="Directory with races.parquet and racer_results.parquet (default: results/, else docs/results/).",
    )
    args = parser.parse_args(argv)
    repo_root = Path(__file__).resolve().parent.parent
    manifest = prepare_web_assets(
        repo_root,
        results_source_dir=args.results_dir,
    )
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
