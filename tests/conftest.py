from __future__ import annotations

import sys
from pathlib import Path

import nonebot
from sqlalchemy import StaticPool

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))


def pytest_sessionstart(session) -> None:  # noqa: ARG001
    nonebot.init(
        driver="~fastapi+~httpx",
        command_start={"", "/"},
        sqlalchemy_database_url="sqlite+aiosqlite://",
        sqlalchemy_engine_options={"poolclass": StaticPool},
        alembic_startup_check=False,
    )
