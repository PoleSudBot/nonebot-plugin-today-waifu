from __future__ import annotations

from pathlib import Path
from typing import Literal

from nonebot import get_plugin_config
from pydantic import BaseModel, Field, field_validator

BASE_DIR = Path(__file__).parent
TEMPLATE_DIR = BASE_DIR / "render" / "templates"
ASSET_DIR = BASE_DIR / "assets"
PJSK_ASSET_DIR = ASSET_DIR / "pjsk"
BANGDREAM_ASSET_DIR = ASSET_DIR / "bangdream"

THEME_KEYS = ("bangdream", "pjsk")


class Config(BaseModel):
    today_waifu_aliases: list[str] = Field(default_factory=list)
    today_waifu_ban_id_list: set[str] = Field(default_factory=set)
    today_waifu_default_change_waifu: bool = True
    today_waifu_default_limit_times: int = 2
    today_waifu_default_select_mode: Literal["random", "active"] = "active"
    today_waifu_default_active_days: int = 3
    today_waifu_member_cache_ttl_seconds: int = 1800
    today_waifu_theme_avatar_cache_ttl_seconds: int = 300
    today_waifu_theme_http_timeout_seconds: int = 10
    today_waifu_member_refresh_hour: int = 3
    today_waifu_member_refresh_minute: int = 0
    today_waifu_report_hour: int = 23
    today_waifu_report_minute: int = 59
    today_waifu_global_milestone_notify: bool = False
    today_waifu_bot_pick_probability: float = 0.015

    @field_validator(
        "today_waifu_default_limit_times",
        "today_waifu_default_active_days",
        "today_waifu_member_cache_ttl_seconds",
        "today_waifu_theme_avatar_cache_ttl_seconds",
    )
    @classmethod
    def _ensure_non_negative(cls, value: int) -> int:
        return max(0, value)

    @field_validator("today_waifu_theme_http_timeout_seconds")
    @classmethod
    def _ensure_positive_timeout(cls, value: int) -> int:
        return max(1, value)

    @field_validator("today_waifu_bot_pick_probability")
    @classmethod
    def _probability_range(cls, value: float) -> float:
        return max(0.0, min(1.0, value))

    @field_validator(
        "today_waifu_member_refresh_hour",
        "today_waifu_report_hour",
    )
    @classmethod
    def _hour_range(cls, value: int) -> int:
        return max(0, min(23, value))

    @field_validator(
        "today_waifu_member_refresh_minute",
        "today_waifu_report_minute",
    )
    @classmethod
    def _minute_range(cls, value: int) -> int:
        return max(0, min(59, value))


plugin_config = get_plugin_config(Config)
