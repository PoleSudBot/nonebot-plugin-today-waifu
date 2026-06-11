from __future__ import annotations

import nonebot


def _normalize_legacy_database_url(url: str) -> str:
    if url.startswith("sqlite+aiosqlite:") or url.startswith("postgresql+asyncpg:"):
        return url
    if url.startswith("sqlite://"):
        return f"sqlite+aiosqlite://{url.removeprefix('sqlite://')}"
    if url.startswith("sqlite:"):
        path = url.split(":", 1)[1]
        if not path or path == ":memory:":
            return "sqlite+aiosqlite://"
        # 旧 Tortoise 配置常用 sqlite:./data/db.sqlite，SQLAlchemy 需要显式 async dialect。
        return f"sqlite+aiosqlite:///{path}"
    if url.startswith("postgres://"):
        return f"postgresql+asyncpg://{url.removeprefix('postgres://')}"
    if url.startswith("postgresql://"):
        return f"postgresql+asyncpg://{url.removeprefix('postgresql://')}"
    return url


def inject_orm_database_url() -> None:
    driver = nonebot.get_driver()
    config = driver.config
    current_url = getattr(config, "sqlalchemy_database_url", "")
    if current_url:
        return
    legacy_url = getattr(config, "db_url", "")
    if legacy_url:
        setattr(config, "sqlalchemy_database_url", _normalize_legacy_database_url(legacy_url))
