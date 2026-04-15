from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


def load_environment() -> None:
    """Load environment variables from a local .env file if one exists."""
    cwd_env = Path.cwd() / ".env"
    package_root_env = Path(__file__).resolve().parents[1] / ".env"

    if cwd_env.exists():
        load_dotenv(cwd_env)
    elif package_root_env.exists():
        load_dotenv(package_root_env)
    else:
        load_dotenv()


class Config:
    APP_TITLE = os.getenv("APP_TITLE", "Stack")
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "stack-dev-secret")
    HS_TOKEN = os.getenv("HS_TOKEN", "")
    DEFAULT_PORT = int(os.getenv("PORT", "8000"))
    DEBUG_USERID = str(os.getenv("DEBUG_USERID", "false")).strip().lower() in {"1", "true", "yes", "on"}
