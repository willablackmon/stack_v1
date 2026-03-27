from __future__ import annotations

import os

from .app import create_app
from .config import Config, load_environment


def _env_flag(name: str, default: bool = False) -> bool:
    raw = str(os.getenv(name, str(default))).strip().lower()
    return raw in {"1", "true", "yes", "on"}


def main() -> None:
    load_environment()
    app = create_app()
    app.run(
        host="0.0.0.0",
        port=Config.DEFAULT_PORT,
        debug=_env_flag("FLASK_DEBUG", default=False),
    )


if __name__ == "__main__":
    main()
