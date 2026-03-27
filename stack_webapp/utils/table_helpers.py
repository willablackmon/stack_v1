from __future__ import annotations

from typing import Any


def normalize_rows(rows: list[dict[str, Any]], columns: list[str] | None = None) -> tuple[list[str], list[dict[str, Any]]]:
    if not rows:
        return columns or [], []

    if columns is None:
        seen: list[str] = []
        for row in rows:
            for key in row.keys():
                if key not in seen:
                    seen.append(key)
        columns = seen

    normalized: list[dict[str, Any]] = []
    for row in rows:
        normalized.append({col: row.get(col, "") for col in columns})

    return columns, normalized
