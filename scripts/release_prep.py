from __future__ import annotations

import pathlib
import re
import shutil
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]
PYPROJECT = ROOT / "pyproject.toml"
NOTEBOOK = ROOT / "frontend" / "magical_athlete_analysis.py"
DOCS_DIR = ROOT / "docs"
RESULTS_DIR = ROOT / "results"

PACKAGE = "magical-athlete-simulator"


def read_version() -> str:
    text = PYPROJECT.read_text(encoding="utf-8")
    m = re.search(r'(?m)^\s*version\s*=\s*"([^"]+)"\s*$', text)
    if not m:
        raise SystemExit('Could not find: version = "..." in pyproject.toml')
    return m.group(1)


def update_notebook_pin(version: str) -> None:
    text = NOTEBOOK.read_text(encoding="utf-8")
    pat = re.compile(
        rf'(await\s+micropip\.install\("){re.escape(PACKAGE)}==[^"]+("\s*,\s*keep_going=True\s*\))'
    )
    new, n = pat.subn(rf"\1{PACKAGE}=={version}\2", text)
    if n != 1:
        raise SystemExit(f"Expected to update 1 micropip.install pin, updated {n}")
    NOTEBOOK.write_text(new, encoding="utf-8")


def export_docs() -> None:
    (DOCS_DIR / "results").mkdir(parents=True, exist_ok=True)

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

    shutil.copy2(ROOT / "frontend" / "magical_athlete_analysis.css", DOCS_DIR / "magical_athlete_analysis.css")

    for p in RESULTS_DIR.glob("*.parquet"):
        shutil.copy2(p, DOCS_DIR / "results" / p.name)


def main() -> None:
    version = read_version()
    update_notebook_pin(version)
    export_docs()


if __name__ == "__main__":
    main()
