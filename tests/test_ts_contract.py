"""Contract test: msgspec DTOs in magsim.web.schemas must match web/src/types/api.ts."""

from __future__ import annotations

import inspect
import re
from pathlib import Path
from typing import get_args

import msgspec
import pytest

from magsim.web import schemas

API_TS = Path(__file__).resolve().parent.parent / "web" / "src" / "types" / "api.ts"

INTERFACE_RE = re.compile(r"export interface (\w+) \{(.*?)^\}", re.DOTALL | re.MULTILINE)
FIELD_RE = re.compile(r"^  (\w+)\??:", re.MULTILINE)
ALIAS_RE = re.compile(r"export type (\w+) =(.*?);", re.DOTALL)
STRING_LITERAL_RE = re.compile(r'"([^"]+)"')

LITERAL_ALIASES = {
    "ComboModeDTO": "ComboMode",
    "RawTableNameDTO": "RawTableName",
    "TileModifierKindDTO": "TileModifierKind",
}

TS_SOURCE = API_TS.read_text()
TS_INTERFACES = {
    name: set(FIELD_RE.findall(body)) for name, body in INTERFACE_RE.findall(TS_SOURCE)
}
TS_ALIASES = {
    name: set(STRING_LITERAL_RE.findall(body))
    for name, body in ALIAS_RE.findall(TS_SOURCE)
}
PY_STRUCTS = {
    name: cls
    for name, cls in inspect.getmembers(schemas, inspect.isclass)
    if issubclass(cls, msgspec.Struct) and cls is not msgspec.Struct
}


@pytest.mark.parametrize("name", sorted(PY_STRUCTS))
def test_struct_fields_match_ts_interface(name: str) -> None:
    assert name in TS_INTERFACES, f"{name} missing from web/src/types/api.ts"
    py_fields = {f.encode_name for f in msgspec.structs.fields(PY_STRUCTS[name])}
    assert py_fields == TS_INTERFACES[name], (
        f"{name}: only in Python {sorted(py_fields - TS_INTERFACES[name])}, "
        f"only in TypeScript {sorted(TS_INTERFACES[name] - py_fields)}"
    )


def test_ts_dto_interfaces_exist_in_python() -> None:
    ts_dtos = {name for name in TS_INTERFACES if name.endswith("DTO")}
    assert ts_dtos <= set(PY_STRUCTS), sorted(ts_dtos - set(PY_STRUCTS))


@pytest.mark.parametrize(("py_name", "ts_name"), sorted(LITERAL_ALIASES.items()))
def test_literal_aliases_match_ts_unions(py_name: str, ts_name: str) -> None:
    py_values = set(get_args(getattr(schemas, py_name).__value__))
    assert py_values == TS_ALIASES[ts_name]
