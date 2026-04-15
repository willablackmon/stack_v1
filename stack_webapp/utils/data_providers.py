from __future__ import annotations

from typing import Any

import requests

from .hubspot_client import OWNER_ID_COL, clean_str, get_hubspot_client, get_token_headers

HS_TIMEOUT_S = 30

COMPANY_PROPS = [
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

MEETING_PROPS = [
    "hs_body_preview",
    "hs_createdate",
    "hs_object_id",
    "hs_meeting_start_time",
    "hs_meeting_end_time",
    OWNER_ID_COL,
]

MEETING_SEED_COLUMNS = [
    "id",
    OWNER_ID_COL,
    "hs_meeting_start_time",
    "hs_meeting_end_time",
    "hs_createdate",
    "hs_object_id",
    "hs_body_preview",
    "associated_company_ids",
    "matched_company_ids",
    "matched_company_names",
]

PLACEHOLDER_OPP_INSIGHTS = [
    {"Opportunity": "Opp Insights not ready", "Stage": "", "Value": ""},
]

PLACEHOLDER_OPP_SEARCH = [
    {"Opportunity Search": "Opp Search not ready"},
]

_CACHE: dict[str, dict[str, Any]] = {}


def _get_cache(token: str) -> dict[str, Any]:
    token = token or "__default__"
    return _CACHE.setdefault(token, {})


def _copy_rows(rows: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    return [dict(row) for row in (rows or [])]


def _paging_after(page_obj):
    paging = getattr(page_obj, "paging", None)
    next_obj = getattr(paging, "next", None)
    return getattr(next_obj, "after", None)


def _probe_endpoint(label: str, method: str, url: str, headers: dict[str, str], json_body=None) -> dict[str, Any]:
    try:
        method = method.upper()
        if method == "GET":
            resp = requests.get(url, headers=headers, timeout=HS_TIMEOUT_S)
        elif method == "POST":
            resp = requests.post(url, headers=headers, json=json_body, timeout=HS_TIMEOUT_S)
        else:
            raise ValueError(f"Unsupported method: {method}")

        try:
            payload = resp.json()
        except Exception:
            payload = {"raw_text": resp.text[:1000]}

        return {
            "label": label,
            "method": method,
            "url": url,
            "status_code": resp.status_code,
            "ok": resp.ok,
            "payload": payload,
        }
    except Exception as exc:
        return {
            "label": label,
            "method": method,
            "url": url,
            "status_code": None,
            "ok": False,
            "payload": {"error": str(exc)},
        }


def _objects_to_rows(objects, out_cols: list[str]) -> list[dict[str, Any]]:
    rows = [{"id": getattr(obj, "id", ""), **(obj.properties or {})} for obj in (objects or [])]
    return [{col: row.get(col, "") for col in out_cols} for row in rows]


def filter_rows_to_user(rows: list[dict[str, Any]], token_user_id: str, owner_col: str = OWNER_ID_COL) -> list[dict[str, Any]]:
    token_user_id = clean_str(token_user_id)
    if not token_user_id:
        return []
    return [dict(row) for row in (rows or []) if clean_str(row.get(owner_col, "")) == token_user_id]


def get_opp_insights() -> list[dict[str, Any]]:
    return PLACEHOLDER_OPP_INSIGHTS


def get_opp_search() -> list[dict[str, Any]]:
    return PLACEHOLDER_OPP_SEARCH


def run_hubspot_login(token: str) -> dict[str, Any]:
    cache = _get_cache(token)
    cached = cache.get("login_info")
    if cached:
        return dict(cached)

    headers = get_token_headers(token)

    acct_resp = requests.get(
        "https://api.hubapi.com/account-info/2026-03/details",
        headers=headers,
        timeout=HS_TIMEOUT_S,
    )
    acct_resp.raise_for_status()
    acct = acct_resp.json()

    tokn_resp = requests.post(
        "https://api.hubapi.com/oauth/v2/private-apps/get/access-token-info",
        headers=headers,
        json={"tokenKey": token},
        timeout=HS_TIMEOUT_S,
    )
    tokn_resp.raise_for_status()
    tokn = tokn_resp.json()

    login_info = {
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
    cache["login_info"] = dict(login_info)
    return login_info


def build_connected_agent_text(login_info: dict[str, Any]) -> str:
    login_info = dict(login_info or {})
    user_id = clean_str(login_info.get("token_user_id", ""))
    hub_id = clean_str(login_info.get("token_hub_id", ""))
    app_id = clean_str(login_info.get("token_app_id", ""))
    email = clean_str(login_info.get("token_user_email", ""))
    portal_name = clean_str(login_info.get("portal_name", ""))
    portal_id = clean_str(login_info.get("portal_id", ""))

    who = email or (f"userId {user_id}" if user_id else "") or portal_name or (f"Portal {portal_id}" if portal_id else "HubSpot")

    lines = [f"Connected as {who}."]
    if user_id:
        lines.append(f"userId = {user_id}")
    if hub_id:
        lines.append(f"hubId = {hub_id}")
    if app_id:
        lines.append(f"appId = {app_id}")
    return "\n".join(lines)


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
        _probe_endpoint("Owners", "GET", "https://api.hubapi.com/crm/owners/2026-03", headers),
        _probe_endpoint("Users", "GET", "https://api.hubapi.com/settings/users/2026-03", headers),
    ]

    if token_user_id:
        probes.append(_probe_endpoint(
            f"User By Token userId {token_user_id}",
            "GET",
            f"https://api.hubapi.com/settings/users/2026-03/{token_user_id}",
            headers,
        ))
        probes.append(_probe_endpoint(
            f"Owner By Token userId As OwnerId {token_user_id}",
            "GET",
            f"https://api.hubapi.com/crm/owners/2026-03/{token_user_id}",
            headers,
        ))

    for owner_id in (owner_ids or [])[:max_owner_ids]:
        probes.append(_probe_endpoint(
            f"Owner By Company Owner ID {owner_id}",
            "GET",
            f"https://api.hubapi.com/crm/owners/2026-03/{owner_id}",
            headers,
        ))

    return {
        "login_info": dict(login_info or {}),
        "owner_ids": list(owner_ids or []),
        "probes": probes,
    }


def _get_all_companies_rows(token: str, page_size: int = 100, force_refresh: bool = False) -> list[dict[str, Any]]:
    cache = _get_cache(token)
    if not force_refresh and cache.get("all_companies_rows") is not None:
        return _copy_rows(cache.get("all_companies_rows"))

    client = get_hubspot_client(token)
    rows: list[dict[str, Any]] = []
    after = None

    while True:
        kwargs = {
            "limit": page_size,
            "properties": COMPANY_PROPS,
            "archived": False,
        }
        if after is not None:
            kwargs["after"] = after

        page = client.crm.companies.basic_api.get_page(**kwargs)
        rows.extend([{"id": str(obj.id), **(obj.properties or {})} for obj in (page.results or [])])

        after = _paging_after(page)
        if after in (None, ""):
            break

    for row in rows:
        homepage_url = clean_str(row.get("website", "")) or clean_str(row.get("domain", ""))
        if homepage_url and not homepage_url.startswith(("http://", "https://")):
            homepage_url = f"https://{homepage_url}"
        row["homepage_url"] = homepage_url

    cache["all_companies_rows"] = _copy_rows(rows)
    return _copy_rows(rows)


def get_my_owned_companies(token: str, limit: int = 100, force_refresh: bool = False) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    cache = _get_cache(token)
    login_info = run_hubspot_login(token)
    if not force_refresh and cache.get("my_owned_companies_rows") is not None:
        return login_info, _copy_rows(cache.get("my_owned_companies_rows"))

    token_user_id = clean_str(login_info.get("token_user_id", ""))
    rows = _get_all_companies_rows(token, page_size=limit, force_refresh=force_refresh)
    rows = filter_rows_to_user(rows, token_user_id, owner_col=OWNER_ID_COL)

    for row in rows:
        company_id = clean_str(row.get("id", ""))
        company_name = clean_str(row.get("name", "")) or clean_str(row.get("website", "")) or company_id
        row["company_label"] = f"{company_name} ({company_id})" if company_id else company_name
        row["website_display"] = clean_str(row.get("website", "")) or clean_str(row.get("homepage_url", ""))

    cache["my_owned_companies_rows"] = _copy_rows(rows)
    cache["my_company_ids"] = [clean_str(row.get("id", "")) for row in rows if clean_str(row.get("id", ""))]
    return login_info, _copy_rows(rows)


def _get_all_meetings_rows(token: str, page_size: int = 100, force_refresh: bool = False) -> list[dict[str, Any]]:
    cache = _get_cache(token)
    if not force_refresh and cache.get("all_meetings_rows") is not None:
        return _copy_rows(cache.get("all_meetings_rows"))

    client = get_hubspot_client(token)
    rows: list[dict[str, Any]] = []
    after = None

    while True:
        kwargs = {
            "object_type": "meetings",
            "limit": page_size,
            "properties": MEETING_PROPS,
            "archived": False,
        }
        if after is not None:
            kwargs["after"] = after

        page = client.crm.objects.basic_api.get_page(**kwargs)
        rows.extend([{"id": str(obj.id), **(obj.properties or {})} for obj in (page.results or [])])

        after = _paging_after(page)
        if after in (None, ""):
            break

    cache["all_meetings_rows"] = _copy_rows(rows)
    cache["all_meeting_ids"] = [clean_str(row.get("id", "")) for row in rows if clean_str(row.get("id", ""))]
    return _copy_rows(rows)


def _get_all_associated_ids(client, from_type: str, from_id: str, to_type: str, page_size: int = 100) -> list[str]:
    ids: list[str] = []
    after = None

    while True:
        kwargs = {
            "object_type": from_type,
            "object_id": str(from_id),
            "to_object_type": to_type,
            "limit": page_size,
        }
        if after is not None:
            kwargs["after"] = after

        page = client.crm.associations.v4.basic_api.get_page(**kwargs)
        ids.extend([str(x.to_object_id) for x in (page.results or [])])

        after = _paging_after(page)
        if after in (None, ""):
            break

    return ids


def build_login_preload_payload(token: str, page_size: int = 100, force_refresh: bool = False) -> dict[str, Any]:
    cache = _get_cache(token)
    if not force_refresh and cache.get("login_preload") is not None:
        preload = dict(cache.get("login_preload") or {})
        preload["my_meetings_seed_rows"] = _copy_rows(preload.get("my_meetings_seed_rows", []))
        return preload

    client = get_hubspot_client(token)
    login_info, owned_companies_rows = get_my_owned_companies(token, limit=page_size, force_refresh=force_refresh)
    my_company_ids = [clean_str(row.get("id", "")) for row in owned_companies_rows if clean_str(row.get("id", ""))]
    my_company_id_set = set(my_company_ids)
    company_name_map = {
        clean_str(row.get("id", "")): clean_str(row.get("name", "")) or clean_str(row.get("website", ""))
        for row in owned_companies_rows
        if clean_str(row.get("id", ""))
    }

    all_meetings_rows = _get_all_meetings_rows(token, page_size=page_size, force_refresh=force_refresh)
    all_meeting_ids = [clean_str(row.get("id", "")) for row in all_meetings_rows if clean_str(row.get("id", ""))]

    all_meeting_company_pairs: list[str] = []
    my_meeting_ids: list[str] = []
    meeting_company_ids_map: dict[str, list[str]] = {}
    my_meetings_seed_rows: list[dict[str, Any]] = []

    for row in all_meetings_rows:
        meeting_id = clean_str(row.get("id", ""))
        if not meeting_id:
            continue

        company_ids = _get_all_associated_ids(client, "meetings", meeting_id, "companies", page_size=page_size)
        meeting_company_ids_map[meeting_id] = list(company_ids)

        for company_id in company_ids:
            all_meeting_company_pairs.append(f"{meeting_id},{company_id}")

        matched_company_ids = [cid for cid in company_ids if cid in my_company_id_set]
        if not matched_company_ids:
            continue

        matched_company_names = [company_name_map.get(cid, cid) for cid in matched_company_ids]
        my_meeting_ids.append(meeting_id)
        my_meetings_seed_rows.append({
            "id": meeting_id,
            OWNER_ID_COL: clean_str(row.get(OWNER_ID_COL, "")),
            "hs_meeting_start_time": clean_str(row.get("hs_meeting_start_time", "")),
            "hs_meeting_end_time": clean_str(row.get("hs_meeting_end_time", "")),
            "hs_createdate": clean_str(row.get("hs_createdate", "")),
            "hs_object_id": clean_str(row.get("hs_object_id", "")),
            "hs_body_preview": clean_str(row.get("hs_body_preview", "")),
            "associated_company_ids": ", ".join(company_ids),
            "matched_company_ids": ", ".join(matched_company_ids),
            "matched_company_names": ", ".join(matched_company_names),
        })

    my_meetings_seed_rows.sort(key=lambda row: str(row.get("hs_meeting_start_time", "")), reverse=True)

    preload_text = "\n\n".join([
        f"all_meeting_ids = {all_meeting_ids}",
        f"my_company_ids = {my_company_ids}",
        f"all_meeting_company_pairs = {all_meeting_company_pairs}",
        f"my_meeting_ids = {my_meeting_ids}",
    ])

    preload = {
        "login_info": dict(login_info),
        "all_meeting_ids": all_meeting_ids,
        "my_company_ids": my_company_ids,
        "all_meeting_company_pairs": all_meeting_company_pairs,
        "my_meeting_ids": my_meeting_ids,
        "meeting_company_ids_map": meeting_company_ids_map,
        "my_meetings_seed_rows": my_meetings_seed_rows,
        "preload_text": preload_text,
    }

    cache["login_preload"] = {
        **preload,
        "my_meetings_seed_rows": _copy_rows(my_meetings_seed_rows),
    }
    cache["all_meeting_ids"] = list(all_meeting_ids)
    cache["my_company_ids"] = list(my_company_ids)
    cache["all_meeting_company_pairs"] = list(all_meeting_company_pairs)
    cache["my_meeting_ids"] = list(my_meeting_ids)
    cache["meeting_company_ids_map"] = {k: list(v) for k, v in meeting_company_ids_map.items()}
    cache["my_meetings_seed_rows"] = _copy_rows(my_meetings_seed_rows)

    return {
        **preload,
        "my_meetings_seed_rows": _copy_rows(my_meetings_seed_rows),
    }


def get_meeting_prep(token: str, limit: int = 100) -> list[dict[str, Any]]:
    cache = _get_cache(token)
    rows = cache.get("my_meetings_seed_rows")
    if rows is None:
        rows = build_login_preload_payload(token, page_size=limit).get("my_meetings_seed_rows", [])
    return _copy_rows(rows)
