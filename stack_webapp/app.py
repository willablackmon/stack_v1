from __future__ import annotations

from typing import Any

from flask import Flask, jsonify, render_template

from .config import Config, load_environment
from .utils.data_providers import (
    build_connected_agent_text,
    build_login_preload_payload,
    get_meeting_prep,
    get_my_owned_companies,
    get_opp_insights,
    get_opp_search,
    run_hubspot_login,
    run_userid_debug_probes,
)
from .utils.table_helpers import normalize_rows


def _table_response(title: str, agent_text: str, rows: list[dict[str, Any]], columns: list[str] | None = None, **extra):
    cols, normalized_rows = normalize_rows(rows, columns)
    payload = {
        "title": title,
        "agent_text": agent_text,
        "type": "table",
        "columns": cols,
        "rows": normalized_rows,
    }
    payload.update(extra)
    return jsonify(payload)


def _browser_response(title: str, agent_text: str, rows: list[dict[str, Any]], item_type: str, **extra):
    payload = {
        "title": title,
        "agent_text": agent_text,
        "type": item_type,
        "rows": rows,
    }
    payload.update(extra)
    return jsonify(payload)


def _login_preload_response(title: str, agent_text: str, preload_text: str, rows: list[dict[str, Any]], columns: list[str] | None = None, **extra):
    cols, normalized_rows = normalize_rows(rows, columns)
    payload = {
        "title": title,
        "agent_text": agent_text,
        "type": "login_preload",
        "preload_text": preload_text,
        "columns": cols,
        "rows": normalized_rows,
    }
    payload.update(extra)
    return jsonify(payload)


def _message_response(title: str, agent_text: str, message: str, status: int = 200, **extra):
    payload = {
        "title": title,
        "agent_text": agent_text,
        "type": "message",
        "message": message,
    }
    payload.update(extra)
    return jsonify(payload), status


def create_app() -> Flask:
    load_environment()

    app = Flask(__name__)
    app.config.from_object(Config)

    @app.get("/")
    def index():
        return render_template(
            "index.html",
            app_title=app.config["APP_TITLE"],
            debug_userid=bool(app.config.get("DEBUG_USERID", False)),
        )

    @app.get("/health")
    def health():
        return jsonify({"status": "ok", "app": app.config["APP_TITLE"]})

    @app.post("/api/login")
    def api_login():
        token = app.config.get("HS_TOKEN", "")
        try:
            login_info = run_hubspot_login(token)
            preload = build_login_preload_payload(token, force_refresh=True)
            _login_info, owned_companies = get_my_owned_companies(token)
            owner_ids = sorted({str(r.get("hubspot_owner_id", "")).strip() for r in owned_companies if str(r.get("hubspot_owner_id", "")).strip()})
            debug = run_userid_debug_probes(token, login_info, owner_ids=owner_ids) if app.config.get("DEBUG_USERID") else None
            return _login_preload_response(
                "Log In",
                build_connected_agent_text(login_info),
                preload.get("preload_text", ""),
                preload.get("my_meetings_seed_rows", []),
                debug=debug,
            )
        except Exception as exc:
            return _message_response("Log In", "HubSpot connection failed.", f"Login failed:\n\n{exc}", status=500)

    @app.post("/api/logout")
    def api_logout():
        return _message_response("Logout", "Logged out of HubSpot. Click Log In to test again.", "HubSpot session cleared.")

    @app.get("/api/opp-insights")
    def api_opp_insights():
        try:
            return _table_response(
                "Opp Insights",
                "Opportunity Insights complete.",
                get_opp_insights(),
            )
        except Exception as exc:
            return _message_response("Opp Insights", "Opportunity Insights failed.", f"Error:\n\n{exc}", status=500)

    @app.get("/api/my-companies")
    def api_my_companies():
        try:
            login_info, rows = get_my_owned_companies(app.config.get("HS_TOKEN", ""))
            return _browser_response(
                "My Companies",
                f"My Companies loaded: {len(rows)} row(s).",
                rows,
                "companies_browser",
                token_user_id=login_info.get("token_user_id", ""),
            )
        except Exception as exc:
            return _message_response("My Companies", "My Companies failed.", f"Error:\n\n{exc}", status=500)

    @app.get("/api/meeting-prep")
    def api_meeting_prep():
        try:
            login_info = run_hubspot_login(app.config.get("HS_TOKEN", ""))
            rows = get_meeting_prep(app.config.get("HS_TOKEN", ""))
            return _browser_response(
                "Meeting Prep",
                f"Meeting Prep complete for userId {login_info.get('token_user_id', '')}: {len(rows)} meeting(s).",
                rows,
                "meetings_browser",
            )
        except Exception as exc:
            return _message_response("Meeting Prep", "Meeting Prep failed.", f"Error:\n\n{exc}", status=500)

    @app.get("/api/opp-search")
    def api_opp_search():
        try:
            return _table_response(
                "Opp Search (not ready)",
                "Opportunity search complete.",
                get_opp_search(),
            )
        except Exception as exc:
            return _message_response("Opp Search (not ready)", "Opportunity search failed.", f"Error:\n\n{exc}", status=500)

    @app.errorhandler(404)
    def not_found(_exc):
        return _message_response("Not Found", "Route not found.", "The requested page does not exist.", status=404)

    return app
