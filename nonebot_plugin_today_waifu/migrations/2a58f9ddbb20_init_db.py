"""init db

修订 ID: 2a58f9ddbb20
父修订:
创建时间: 2026-03-29 07:00:00.000000
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

if TYPE_CHECKING:
    from collections.abc import Sequence

revision: str = "2a58f9ddbb20"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = ("nonebot_plugin_today_waifu",)
depends_on: str | Sequence[str] | None = None


def _json_type() -> sa.JSON:
    return sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade(name: str = "") -> None:
    if name:
        return
    op.create_table(
        "nonebot_plugin_today_waifu_global_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("enabled_theme_keys", _json_type(), nullable=False),
        sa.Column("milestone_notify_enabled", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint(
            "id", name=op.f("pk_nonebot_plugin_today_waifu_global_settings")
        ),
    )
    op.create_table(
        "nonebot_plugin_today_waifu_group_settings",
        sa.Column("scene_id", sa.String(length=64), nullable=False),
        sa.Column("allow_change", sa.Boolean(), nullable=False),
        sa.Column("limit_times", sa.Integer(), nullable=False),
        sa.Column("select_mode", sa.String(length=16), nullable=False),
        sa.Column("active_days", sa.Integer(), nullable=False),
        sa.Column("pure_love_enabled", sa.Boolean(), nullable=False),
        sa.Column("rbq_enabled", sa.Boolean(), nullable=False),
        sa.Column("fate_report_enabled", sa.Boolean(), nullable=False),
        sa.Column("milestone_notify_override", sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint(
            "scene_id", name=op.f("pk_nonebot_plugin_today_waifu_group_settings")
        ),
    )
    op.create_table(
        "nonebot_plugin_today_waifu_theme_preference",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("scope", sa.String(length=16), nullable=False),
        sa.Column("scene_id", sa.String(length=64), nullable=True),
        sa.Column("user_id", sa.String(length=64), nullable=True),
        sa.Column("enabled_theme_keys", _json_type(), nullable=False),
        sa.PrimaryKeyConstraint(
            "id", name=op.f("pk_nonebot_plugin_today_waifu_theme_preference")
        ),
        sa.UniqueConstraint(
            "scope",
            "scene_id",
            "user_id",
            name="uq_nonebot_plugin_today_waifu_theme_preference",
        ),
    )
    op.create_table(
        "nonebot_plugin_today_waifu_daily_state",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("scene_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("target_id", sa.String(length=64), nullable=True),
        sa.Column("change_used", sa.Integer(), nullable=False),
        sa.Column("lock_source_user_id", sa.String(length=64), nullable=True),
        sa.Column("lock_mirrored", sa.Boolean(), nullable=False),
        sa.Column("theme_key", sa.String(length=32), nullable=True),
        sa.Column("theme_payload", _json_type(), nullable=True),
        sa.Column("counted", sa.Boolean(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint(
            "id", name=op.f("pk_nonebot_plugin_today_waifu_daily_state")
        ),
        sa.UniqueConstraint(
            "date",
            "scene_id",
            "user_id",
            name="uq_nonebot_plugin_today_waifu_daily_state",
        ),
    )
    op.create_table(
        "nonebot_plugin_today_waifu_pair_counter",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("scene_id", sa.String(length=64), nullable=False),
        sa.Column("bucket_type", sa.String(length=16), nullable=False),
        sa.Column("bucket_key", sa.String(length=32), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("target_id", sa.String(length=64), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint(
            "id", name=op.f("pk_nonebot_plugin_today_waifu_pair_counter")
        ),
        sa.UniqueConstraint(
            "scene_id",
            "bucket_type",
            "bucket_key",
            "user_id",
            "target_id",
            name="uq_nonebot_plugin_today_waifu_pair_counter",
        ),
    )
    op.create_table(
        "nonebot_plugin_today_waifu_member_activity",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("scene_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("last_speak_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint(
            "id", name=op.f("pk_nonebot_plugin_today_waifu_member_activity")
        ),
        sa.UniqueConstraint(
            "scene_id",
            "user_id",
            name="uq_nonebot_plugin_today_waifu_member_activity",
        ),
    )


def downgrade(name: str = "") -> None:
    if name:
        return
    op.drop_table("nonebot_plugin_today_waifu_member_activity")
    op.drop_table("nonebot_plugin_today_waifu_pair_counter")
    op.drop_table("nonebot_plugin_today_waifu_daily_state")
    op.drop_table("nonebot_plugin_today_waifu_theme_preference")
    op.drop_table("nonebot_plugin_today_waifu_group_settings")
    op.drop_table("nonebot_plugin_today_waifu_global_settings")
