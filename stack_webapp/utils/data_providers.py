from __future__ import annotations

from typing import Any

import requests

from .hubspot_client import OWNER_ID_COL, clean_str, get_hubspot_client, get_token_headers

MEETING_COLUMNS = [
    "id",
    "company_contacts_summary",
    "associated_deal_names",
    "associated_deal_ids",
    "hs_meeting_start_time",
    "hs_meeting_end_time",
    "hs_body_preview",
]

PLACEHOLDER_OPP_INSIGHTS = [
    {"Opportunity": "Opp Insights not ready", "Stage": "", "Value": ""},
]

PLACEHOLDER_OPP_SEARCH = [
    {"Opportunity Search": "Opp Search not ready"},
]


def get_opp_insights() -> list[dict[str, Any]]:
    return PLACEHOLDER_OPP_INSIGHTS



def get_opp_search() -> list[dict[str, Any]]:
    return PLACEHOLDER_OPP_SEARCH


# ---------------------------
# Login / probe helpers
# ---------------------------
def _probe_endpoint(label: str, method: str, url: str, headers: dict[str, str], json_body=None) -> dict[str, Any]:
    try:
        if method.upper() == "GET":
            resp = requests.get(url, headers=headers, timeout=30)
        elif method.upper() == "POST":
            resp = requests.post(url, headers=headers, json=json_body, timeout=30)
        else:
            raise ValueError(f"Unsupported method: {method}")

        try:
            payload = resp.json()
        except Exception:
            payload = {"raw_text": resp.text[:1000]}

        return {
            "label": label,
            "method": method.upper(),
            "url": url,
            "status_code": resp.status_code,
            "ok": resp.ok,
            "payload": payload,
        }
    except Exception as exc:
        return {
            "label": label,
            "method": method.upper(),
            "url": url,
            "status_code": None,
            "ok": False,
            "payload": {"error": str(exc)},
        }



def run_hubspot_login(token: str) -> dict[str, Any]:
    headers = get_token_headers(token)
    acct_resp = requests.get(
        "https://api.hubapi.com/account-info/2026-03/details",
        headers=headers,
        timeout=30,
    )
    acct_resp.raise_for_status()
    acct = acct_resp.json()

    tokn_resp = requests.post(
        "https://api.hubapi.com/oauth/v2/private-apps/get/access-token-info",
        headers=headers,
        json={"tokenKey": token},
        timeout=30,
    )
    tokn_resp.raise_for_status()
    tokn = tokn_resp.json()

    return {
        "portal_id": clean_str(acct.get("portalId", "")),
        "portal_name": clean_str(acct.get("accountName", "")),
        "portal_timezone": clean_str(acct.get("timeZone", "")),
        "portal_currency": clean_str(acct.get("companyCurrency", "")),
        "token_user_id": clean_str(tokn.get("userId", "")),
        "token_hub_id": clean_str(tokn.get("hubId", "")),
        "token_app_id": clean_str(tokn.get("appId", "")),
        "token_scopes": tokn.get("scopes", []) or [],
        "token_user_email": clean_str(((tokn.get("user") or {}).get("email", ""))),
    }



def run_userid_debug_probes(token: str, login_info: dict[str, Any], owner_ids: list[str] | None = None, max_owner_ids: int = 3) -> dict[str, Any]:
    headers = get_token_headers(token)
    token_user_id = clean_str(login_info.get("token_user_id", ""))
    probes = [
        _probe_endpoint("Account Details", "GET", "https://api.hubapi.com/account-info/2026-03/details", headers),
        _probe_endpoint(
            "Access Token Info",
            "POST",
            "https://api.hubapi.com/oauth/v2/private-apps/get/access-token-info",
            headers,
            json_body={"tokenKey": token},
        ),
        _probe_endpoint("Owners List", "GET", "https://api.hubapi.com/crm/owners/2026-03", headers),
        _probe_endpoint("Users List", "GET", "https://api.hubapi.com/settings/users/2026-03", headers),
    ]

    if token_user_id:
        probes.append(
            _probe_endpoint(
                f"User By Token userId {token_user_id}",
                "GET",
                f"https://api.hubapi.com/settings/users/2026-03/{token_user_id}",
                headers,
            )
        )
        probes.append(
            _probe_endpoint(
                f"Owner By Token userId As OwnerId {token_user_id}",
                "GET",
                f"https://api.hubapi.com/crm/owners/2026-03/{token_user_id}",
                headers,
            )
        )

    for owner_id in (owner_ids or [])[:max_owner_ids]:
        probes.append(
            _probe_endpoint(
                f"Owner By Company Owner ID {owner_id}",
                "GET",
                f"https://api.hubapi.com/crm/owners/2026-03/{owner_id}",
                headers,
            )
        )

    return {
        "login_info": login_info,
        "owner_ids": owner_ids or [],
        "probes": probes,
    }


# ---------------------------
# Generic HubSpot object helpers
# ---------------------------
def _objects_to_rows(objects, out_cols: list[str]) -> list[dict[str, Any]]:
    rows = [{"id": getattr(obj, "id", ""), **(obj.properties or {})} for obj in (objects or [])]
    return [{col: row.get(col, "") for col in out_cols} for row in rows]



def _fetch_objects_by_id(fetch_fn, ids: list[str], properties: list[str], out_cols: list[str] | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for obj_id in ids:
        obj = fetch_fn(obj_id, properties=properties)
        rows.append({"id": getattr(obj, "id", ""), **(obj.properties or {})})
    out_cols = out_cols or (["id"] + properties)
    return [{col: row.get(col, "") for col in out_cols} for row in rows]



def get_associated_ids(client: HubSpot, from_type: str, from_id: str, to_type: str, limit: int = 100) -> list[str]:
    r = client.crm.associations.v4.basic_api.get_page(
        object_type=from_type,
        object_id=str(from_id),
        to_object_type=to_type,
        limit=limit,
    )
    return [str(x.to_object_id) for x in (r.results or [])]



def filter_rows_to_user(rows: list[dict[str, Any]], token_user_id: str, owner_col: str = OWNER_ID_COL) -> list[dict[str, Any]]:
    token_user_id = clean_str(token_user_id)
    if not token_user_id:
        return []
    out: list[dict[str, Any]] = []
    for row in rows or []:
        if clean_str(row.get(owner_col, "")) == token_user_id:
            out.append(row)
    return out


# ---------------------------
# Companies
# ---------------------------
def get_my_companies(token: str, limit: int = 100) -> list[dict[str, Any]]:
    client = get_hubspot_client(token)
    company_props = [
        "hs_object_id",
        "name",
        "domain",
        "website",
        "phone",
        "city",
        "state",
        "country",
        "createdate",
        "hs_lastmodifieddate",
        OWNER_ID_COL,
    ]
    page = client.crm.companies.basic_api.get_page(
        limit=limit,
        properties=company_props,
        archived=False,
    )
    rows = _objects_to_rows(page.results, ["id"] + company_props)
    for row in rows:
        homepage_url = clean_str(row.get("website", "")) or clean_str(row.get("domain", ""))
        if homepage_url and not homepage_url.startswith(("http://", "https://")):
            homepage_url = f"https://{homepage_url}"
        row["homepage_url"] = homepage_url
    return rows



def get_my_owned_companies(token: str, limit: int = 100) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    login_info = run_hubspot_login(token)
    token_user_id = clean_str(login_info.get("token_user_id", ""))
    rows = get_my_companies(token, limit=limit)
    rows = filter_rows_to_user(rows, token_user_id, owner_col=OWNER_ID_COL)
    return login_info, rows


# ---------------------------
# Meetings
# ---------------------------
def _company_contacts_for_companies(client: HubSpot, companies_rows: list[dict[str, Any]], token_user_id: str) -> tuple[list[dict[str, Any]], str]:
    if not companies_rows:
        return [], ""

    contact_props = [
        "firstname",
        "lastname",
        "email",
        "phone",
        "createdate",
        "hs_object_id",
        OWNER_ID_COL,
    ]

    all_rows: list[dict[str, Any]] = []
    summary_parts: list[str] = []
    for company in companies_rows:
        company_id = clean_str(company.get("id", ""))
        company_name = clean_str(company.get("name", "")) or company_id
        if not company_id:
            continue
        try:
            company_contact_ids = get_associated_ids(client, "companies", company_id, "contacts")
        except Exception:
            company_contact_ids = []
        if not company_contact_ids:
            continue
        contact_rows = _fetch_objects_by_id(
            client.crm.contacts.basic_api.get_by_id,
            company_contact_ids,
            contact_props,
        )
        contact_rows = filter_rows_to_user(contact_rows, token_user_id, owner_col=OWNER_ID_COL)
        if not contact_rows:
            continue
        labels = []
        for c in contact_rows:
            c["source_company_id"] = company_id
            c["source_company_name"] = company_name
            all_rows.append(c)
            label = _format_contact_label(c)
            if label:
                labels.append(label)
        if labels:
            summary_parts.append(f"{company_name}: " + ", ".join(labels))
    return all_rows, " | ".join(summary_parts)



def _meeting_association_details(client: HubSpot, meeting_id: str, token_user_id: str) -> dict[str, Any]:
    company_ids = get_associated_ids(client, "meetings", meeting_id, "companies")
    contact_ids = get_associated_ids(client, "meetings", meeting_id, "contacts")
    deal_ids = get_associated_ids(client, "meetings", meeting_id, "deals")
    ticket_ids = get_associated_ids(client, "meetings", meeting_id, "tickets")

    company_props = ["name", "domain", "website", "createdate", "hs_lastmodifieddate", "hs_object_id", OWNER_ID_COL]
    contact_props = ["firstname", "lastname", "email", "phone", "createdate", "hs_object_id", OWNER_ID_COL]
    deal_props = ["dealname", "dealstage", "amount", "createdate", "hs_lastmodifieddate", "hs_object_id", OWNER_ID_COL]
    ticket_props = ["subject", "content", "hs_pipeline_stage", "hs_object_id"]

    companies_rows = _fetch_objects_by_id(client.crm.companies.basic_api.get_by_id, company_ids, company_props)
    contacts_rows = _fetch_objects_by_id(client.crm.contacts.basic_api.get_by_id, contact_ids, contact_props)
    deals_rows = _fetch_objects_by_id(client.crm.deals.basic_api.get_by_id, deal_ids, deal_props)
    tickets_rows = _fetch_objects_by_id(client.crm.tickets.basic_api.get_by_id, ticket_ids, ticket_props)

    companies_rows = filter_rows_to_user(companies_rows, token_user_id, owner_col=OWNER_ID_COL)
    contacts_rows = filter_rows_to_user(contacts_rows, token_user_id, owner_col=OWNER_ID_COL)
    deals_rows = filter_rows_to_user(deals_rows, token_user_id, owner_col=OWNER_ID_COL)

    company_contacts_rows, company_contacts_summary = _company_contacts_for_companies(client, companies_rows, token_user_id)

    return {
        "company_ids": [clean_str(r.get("id", "")) for r in companies_rows if clean_str(r.get("id", ""))],
        "contact_ids": [clean_str(r.get("id", "")) for r in contacts_rows if clean_str(r.get("id", ""))],
        "deal_ids": [clean_str(r.get("id", "")) for r in deals_rows if clean_str(r.get("id", ""))],
        "ticket_ids": [clean_str(r.get("id", "")) for r in tickets_rows if clean_str(r.get("id", ""))],
        "companies_rows": companies_rows,
        "contacts_rows": contacts_rows,
        "deals_rows": deals_rows,
        "tickets_rows": tickets_rows,
        "company_contacts_rows": company_contacts_rows,
        "company_contacts_summary": company_contacts_summary,
    }



def get_meeting_prep(token: str, limit: int = 100) -> list[dict[str, Any]]:
    client = get_hubspot_client(token)
    login_info = run_hubspot_login(token)
    token_user_id = clean_str(login_info.get("token_user_id", ""))
    if not token_user_id:
        return []

    owned_companies = get_my_owned_companies(token, limit=limit)[1]
    owned_company_ids = {clean_str(r.get("id", "")) for r in owned_companies if clean_str(r.get("id", ""))}
    if not owned_company_ids:
        return []

    page = client.crm.objects.basic_api.get_page(
        object_type="meetings",
        limit=limit,
        properties=[c for c in MEETING_COLUMNS if c != "id"] + [OWNER_ID_COL],
        archived=False,
    )

    rows: list[dict[str, Any]] = []
    for meeting in getattr(page, "results", []) or []:
        row = {"id": getattr(meeting, "id", ""), **(meeting.properties or {})}
        if clean_str(row.get(OWNER_ID_COL, "")) != token_user_id:
            continue
        try:
            assoc = _meeting_association_details(client, clean_str(row.get("id", "")), token_user_id)
        except Exception:
            continue
        assoc_company_ids = assoc["company_ids"]
        matched_company_ids = sorted(owned_company_ids.intersection(assoc_company_ids))
        if not matched_company_ids:
            continue

        company_names = [clean_str(r.get("name", "")) for r in assoc["companies_rows"] if clean_str(r.get("name", ""))]
        contact_names = [_format_contact_label(r) for r in assoc["contacts_rows"] if _format_contact_label(r)]
        contact_emails = [clean_str(r.get("email", "")) for r in assoc["contacts_rows"] if clean_str(r.get("email", ""))]
        deal_names = [clean_str(r.get("dealname", "")) for r in assoc["deals_rows"] if clean_str(r.get("dealname", ""))]

        rows.append({
            "id": clean_str(row.get("id", "")),
            OWNER_ID_COL: clean_str(row.get(OWNER_ID_COL, "")),
            "hs_meeting_start_time": clean_str(row.get("hs_meeting_start_time", "")),
            "hs_meeting_end_time": clean_str(row.get("hs_meeting_end_time", "")),
            "hs_createdate": clean_str(row.get("hs_createdate", "")),
            "hs_object_id": clean_str(row.get("hs_object_id", "")),
            "hs_body_preview": clean_str(row.get("hs_body_preview", "")),
            "associated_company_ids": ", ".join(assoc_company_ids),
            "associated_company_names": ", ".join(company_names),
            "associated_contact_ids": ", ".join(assoc["contact_ids"]),
            "associated_contact_names": ", ".join(contact_names),
            "associated_contact_emails": ", ".join(contact_emails),
            "associated_deal_ids": ", ".join(assoc["deal_ids"]),
            "associated_deal_names": ", ".join(deal_names),
            "company_contacts_summary": assoc.get("company_contacts_summary", ""),
            "matched_company_ids": ", ".join(matched_company_ids),
            "token_user_id": token_user_id,
        })

    rows.sort(key=lambda r: str(r.get("hs_meeting_start_time", "")), reverse=True)
    return rows
