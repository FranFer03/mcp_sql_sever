from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


SENSITIVE_NAME_PATTERN = re.compile(
    r"("
    r"email|e[-_]?mail|phone|telefono|tel[eé]fono|mobile|celular|"
    r"name|nombre|apellido|surname|address|direccion|direcci[oó]n|"
    r"dni|cuit|cuil|document|documento|passport|ssn|tax|"
    r"token|password|passwd|secret|api[_-]?key|credential"
    r")",
    re.IGNORECASE,
)


def is_sensitive_column(column_name: str) -> bool:
    return bool(SENSITIVE_NAME_PATTERN.search(column_name))


def mask_value(value: Any) -> Any:
    if value is None:
        return None
    text = str(value)
    if not text:
        return text
    if len(text) <= 4:
        return "***"
    return f"{text[:2]}***{text[-2:]}"


def mask_row(row: Mapping[str, Any], *, enabled: bool = True) -> dict[str, Any]:
    if not enabled:
        return dict(row)
    return {
        column: mask_value(value) if is_sensitive_column(column) else value
        for column, value in row.items()
    }


def mask_rows(rows: list[dict[str, Any]], *, enabled: bool = True) -> list[dict[str, Any]]:
    return [mask_row(row, enabled=enabled) for row in rows]
