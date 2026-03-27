from __future__ import annotations

from typing import Any

from hubspot import HubSpot


def get_hubspot_client(token: str) -> HubSpot:
    if not token:
        raise RuntimeError("HS_TOKEN is missing. Add it to your environment or .env file.")
    return HubSpot(access_token=token)


def login_preview(token: str) -> dict[str, Any]:
    client = get_hubspot_client(token)
    page = client.crm.contacts.basic_api.get_page(
        limit=1,
        properties=["email", "firstname", "lastname"],
    )

    if getattr(page, "results", None):
        return dict(page.results[0].properties or {})
    return {}
