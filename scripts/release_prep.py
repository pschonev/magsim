from __future__ import annotations

import pathlib
import re
import shutil
import subprocess
import tomllib  # Requires Python 3.11+

ROOT = pathlib.Path(__file__).resolve().parents[1]
PYPROJECT = ROOT / "pyproject.toml"
NOTEBOOK = ROOT / "frontend" / "magical_athlete_analysis.py"
DOCS_DIR = ROOT / "docs"
RESULTS_DIR = ROOT / "results"

PACKAGE = "magsim"


def read_version() -> str:
    """Reads the project version using standard tomllib."""
    # tomllib.load requires opening the file in binary mode
    with PYPROJECT.open("rb") as f:
        data = tomllib.load(f)

    # Assumes PEP 621 metadata structure
    try:
        return data["project"]["version"]
    except KeyError:
        raise SystemExit("Could not find [project] version in pyproject.toml")


def update_notebook_pin(version: str) -> None:
    """Updates the version constant in the notebook file."""
    text = NOTEBOOK.read_text(encoding="utf-8")

    # Universal pattern: any assignment to this variable
    pattern = r'(MAGSIM_VERSION\s*=\s*)(["\'])([^"\']+)\2'

    # Find ALL matches first
    matches = list(re.finditer(pattern, text))
    if len(matches) != 1:
        print(f"Found {len(matches)} matches instead of 1:")
        for i, m in enumerate(matches):
            print(f"  {i}: '{m.group(0)}'")
        raise SystemExit(f"Expected exactly 1 match, found {len(matches)}")

    # Replace the single match
    new_text = re.sub(pattern, rf"\g<1>\g<2>{version}\g<2>", text)

    NOTEBOOK.write_text(new_text, encoding="utf-8")
    print(f"✅ Updated version: {version}")


def export_docs() -> None:
    (DOCS_DIR / "results").mkdir(parents=True, exist_ok=True)

    # Copy CSS BEFORE export so marimo can find it
    shutil.copy2(
        ROOT / "frontend" / "docs" / "magical_athlete_analysis.css",
        DOCS_DIR / "magical_athlete_analysis.css",
    )

    subprocess.check_call(
        [
            "uvx",
            "marimo",
            "export",
            "html-wasm",
            "--mode",
            "run",
            "--no-show-code",
            str(NOTEBOOK),
            "-o",
            str(DOCS_DIR),
        ]
    )

    for p in RESULTS_DIR.glob("*.parquet"):
        shutil.copy2(p, DOCS_DIR / "results" / p.name)


def main() -> None:
    version = read_version()
    update_notebook_pin(version)
    export_docs()


if __name__ == "__main__":
    main()
