from __future__ import annotations

from datetime import date, datetime

from nonebot_plugin_orm import Model
from sqlalchemy import JSON, Boolean, Date, DateTime, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

json_type = JSON().with_variant(JSONB, "postgresql")


class GlobalSettings(Model):
    __tablename__ = "nonebot_plugin_today_waifu_global_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    enabled_theme_keys: Mapped[list[str]] = mapped_column(json_type)
    milestone_notify_enabled: Mapped[bool] = mapped_column(Boolean, default=False)


class GroupSettings(Model):
    __tablename__ = "nonebot_plugin_today_waifu_group_settings"

    scene_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    allow_change: Mapped[bool] = mapped_column(Boolean, default=True)
    limit_times: Mapped[int] = mapped_column(Integer, default=2)
    select_mode: Mapped[str] = mapped_column(String(16), default="active")
    active_days: Mapped[int] = mapped_column(Integer, default=3)
    pure_love_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    pure_love_pending_enable_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        default=None,
    )
    rbq_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    fate_report_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    milestone_notify_override: Mapped[bool | None] = mapped_column(
        Boolean, nullable=True, default=None
    )


class ThemePreference(Model):
    __tablename__ = "nonebot_plugin_today_waifu_theme_preference"
    __table_args__ = (
        UniqueConstraint(
            "scope",
            "scene_id",
            "user_id",
            name="uq_nonebot_plugin_today_waifu_theme_preference",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scope: Mapped[str] = mapped_column(String(16))
    scene_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    enabled_theme_keys: Mapped[list[str]] = mapped_column(json_type)


class DailyWaifuState(Model):
    __tablename__ = "nonebot_plugin_today_waifu_daily_state"
    __table_args__ = (
        UniqueConstraint(
            "date",
            "scene_id",
            "user_id",
            name="uq_nonebot_plugin_today_waifu_daily_state",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    date: Mapped[date] = mapped_column(Date)
    scene_id: Mapped[str] = mapped_column(String(64))
    user_id: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16))
    target_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    change_used: Mapped[int] = mapped_column(Integer, default=0)
    lock_source_user_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    lock_mirrored: Mapped[bool] = mapped_column(Boolean, default=False)
    theme_key: Mapped[str | None] = mapped_column(String(32), nullable=True)
    theme_payload: Mapped[dict | None] = mapped_column(json_type, nullable=True)
    counted: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class PairCounter(Model):
    __tablename__ = "nonebot_plugin_today_waifu_pair_counter"
    __table_args__ = (
        UniqueConstraint(
            "scene_id",
            "bucket_type",
            "bucket_key",
            "user_id",
            "target_id",
            name="uq_nonebot_plugin_today_waifu_pair_counter",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scene_id: Mapped[str] = mapped_column(String(64))
    bucket_type: Mapped[str] = mapped_column(String(16))
    bucket_key: Mapped[str] = mapped_column(String(32))
    user_id: Mapped[str] = mapped_column(String(64))
    target_id: Mapped[str] = mapped_column(String(64))
    count: Mapped[int] = mapped_column(Integer, default=0)


class MemberActivity(Model):
    __tablename__ = "nonebot_plugin_today_waifu_member_activity"
    __table_args__ = (
        UniqueConstraint(
            "scene_id",
            "user_id",
            name="uq_nonebot_plugin_today_waifu_member_activity",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scene_id: Mapped[str] = mapped_column(String(64))
    user_id: Mapped[str] = mapped_column(String(64))
    last_speak_at: Mapped[datetime] = mapped_column(DateTime)
