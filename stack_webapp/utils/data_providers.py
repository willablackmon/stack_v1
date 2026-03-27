from __future__ import annotations

from typing import Any

from .hubspot_client import get_hubspot_client


MEETING_COLUMNS = [
    "id",
    "hs_body_preview",
    "hs_createdate",
    "hs_object_id",
    "hs_meeting_start_time",
    "hs_meeting_end_time",
]


PLACEHOLDER_OPP_INSIGHTS = [
    {"Opportunity": "Opp A", "Stage": "Discovery", "Value": 25000},
    {"Opportunity": "Opp B", "Stage": "Proposal", "Value": 72000},
    {"Opportunity": "Opp C", "Stage": "Negotiation", "Value": 145000},
]


PLACEHOLDER_OPP_SEARCH = [
    {"Company": "Acme Corp", "Opportunity": "ERP Upgrade", "Owner": "Will"},
    {"Company": "Globex", "Opportunity": "Cloud Migration", "Owner": "Julia"},
    {"Company": "Initech", "Opportunity": "Data Cleanup", "Owner": "Sam"},
]


def get_opp_insights() -> list[dict[str, Any]]:
    return PLACEHOLDER_OPP_INSIGHTS



def get_opp_search() -> list[dict[str, Any]]:
    return PLACEHOLDER_OPP_SEARCH



def get_meeting_prep(token: str, limit: int = 100) -> list[dict[str, Any]]:
    client = get_hubspot_client(token)
    page = client.crm.objects.basic_api.get_page(
        object_type="meetings",
        limit=limit,
        properties=[c for c in MEETING_COLUMNS if c != "id"],
        archived=False,
    )

    rows: list[dict[str, Any]] = []
    for meeting in getattr(page, "results", []) or []:
        props = dict(meeting.properties or {})
        row = {"id": getattr(meeting, "id", "")}
        for col in MEETING_COLUMNS:
            if col == "id":
                continue
            row[col] = props.get(col, "")
        rows.append(row)

    rows.sort(key=lambda r: str(r.get("hs_meeting_start_time", "")), reverse=True)
    return rows
