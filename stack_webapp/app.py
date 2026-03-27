from __future__ import annotations

from typing import Any

from flask import Flask, jsonify, render_template

from .config import Config, load_environment
from .utils.data_providers import (
    MEETING_COLUMNS,
    get_meeting_prep,
    get_opp_insights,
    get_opp_search,
)
from .utils.hubspot_client import login_preview
from .utils.table_helpers import normalize_rows


def _table_response(title: str, agent_text: str, rows: list[dict[str, Any]], columns: list[str] | None = None):
    cols, normalized_rows = normalize_rows(rows, columns)
    return jsonify(
        {
            "title": title,
            "agent_text": agent_text,
            "type": "table",
            "columns": cols,
            "rows": normalized_rows,
        }
    )


def _message_response(title: str, agent_text: str, message: str, status: int = 200):
    return (
        jsonify(
            {
                "title": title,
                "agent_text": agent_text,
                "type": "message",
                "message": message,
            }
        ),
        status,
    )


def create_app() -> Flask:
    load_environment()

    app = Flask(__name__)
    app.config.from_object(Config)

    @app.get("/")
    def index():
        return render_template("index.html", app_title=app.config["APP_TITLE"])

    @app.get("/health")
    def health():
        return jsonify({"status": "ok", "app": app.config["APP_TITLE"]})

    @app.post("/api/login")
    def api_login():
        try:
            preview = login_preview(app.config.get("HS_TOKEN", ""))
            if preview:
                return _table_response("Log In", "HubSpot login successful.", [preview])
            return _message_response(
                "Log In",
                "HubSpot login successful.",
                "Logged in successfully. Test contact returned no properties.",
            )
        except Exception as exc:
            return _message_response("Log In", "HubSpot login failed.", f"Login failed:\n\n{exc}", status=500)

    @app.get("/api/opp-insights")
    def api_opp_insights():
        try:
            return _table_response(
                "Opp Insights",
                "Opportunity Insights complete.",
                get_opp_insights(),
            )
        except Exception as exc:
            return _message_response(
                "Opp Insights",
                "Opportunity Insights failed.",
                f"Error:\n\n{exc}",
                status=500,
            )

    @app.get("/api/meeting-prep")
    def api_meeting_prep():
        try:
            rows = get_meeting_prep(app.config.get("HS_TOKEN", ""))
            return _table_response(
                "Meeting Prep",
                "Meeting Prep complete.",
                rows,
                MEETING_COLUMNS,
            )
        except Exception as exc:
            return _message_response(
                "Meeting Prep",
                "Meeting Prep failed.",
                f"Error:\n\n{exc}",
                status=500,
            )

    @app.get("/api/opp-search")
    def api_opp_search():
        try:
            return _table_response(
                "Opp Search",
                "Opportunity search complete.",
                get_opp_search(),
            )
        except Exception as exc:
            return _message_response(
                "Opp Search",
                "Opportunity search failed.",
                f"Error:\n\n{exc}",
                status=500,
            )

    @app.errorhandler(404)
    def not_found(_exc):
        return _message_response("Not Found", "Route not found.", "The requested page does not exist.", status=404)

    return app
