"""Arrow IPC export utilities for fast Pyodide/WASM browser data loading."""

from __future__ import annotations

import io
from typing import TYPE_CHECKING, Literal

import polars as pl

if TYPE_CHECKING:
    from pathlib import Path

type IpcCompression = Literal["uncompressed", "lz4", "zstd"]


def dataframe_to_ipc_bytes(
    df: pl.DataFrame,
    *,
    compression: IpcCompression = "zstd",
) -> bytes:
    """Serialize a Polars DataFrame to Arrow IPC bytes."""
    buf = io.BytesIO()
    df.write_ipc(buf, compression=compression)
    return buf.getvalue()


def export_parquet_to_ipc(
    parquet_path: Path,
    ipc_path: Path,
    *,
    compression: IpcCompression = "zstd",
) -> Path:
    """Convert a Parquet file on disk to compressed Arrow IPC format."""
    df = pl.read_parquet(parquet_path)
    ipc_path.parent.mkdir(parents=True, exist_ok=True)
    df.write_ipc(ipc_path, compression=compression)
    return ipc_path
