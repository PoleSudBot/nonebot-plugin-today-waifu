from __future__ import annotations

import nonebot

from .config import plugin_config


def inject_orm_database_url() -> None:
    driver = nonebot.get_driver()
    config = driver.config
    current_url = getattr(config, "sqlalchemy_database_url", "")
    if current_url:
        return
    legacy_url = getattr(config, "db_url", "")
    if legacy_url:
        setattr(config, "sqlalchemy_database_url", legacy_url)
