from __future__ import annotations

from typing import Any

from hubspot import HubSpot


OWNER_ID_COL = "hubspot_owner_id"


def get_hubspot_client(token: str) -> HubSpot:
    if not token:
        raise RuntimeError("HS_TOKEN is missing. Add it to your environment or .env file.")
    return HubSpot(access_token=token)


def clean_str(value: Any) -> str:
    s = "" if value is None else str(value).strip()
    return "" if s in {"", "nan", "None"} else s


def ensure_columns(rows: list[dict[str, Any]] | None, columns: list[str]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows or []:
        out.append({col: row.get(col, "") for col in columns})
    return out


def get_token_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
