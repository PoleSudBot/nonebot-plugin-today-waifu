"""add pure love pending enable date

修订 ID: 7d8b7d8d9c2e
父修订: 2a58f9ddbb20
创建时间: 2026-04-01 12:00:00.000000
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from alembic import op
import sqlalchemy as sa

if TYPE_CHECKING:
    from collections.abc import Sequence

revision: str = "7d8b7d8d9c2e"
down_revision: str | Sequence[str] | None = "2a58f9ddbb20"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade(name: str = "") -> None:
    if name:
        return
    op.add_column(
        "nonebot_plugin_today_waifu_group_settings",
        sa.Column("pure_love_pending_enable_date", sa.Date(), nullable=True),
    )


def downgrade(name: str = "") -> None:
    if name:
        return
    op.drop_column(
        "nonebot_plugin_today_waifu_group_settings",
        "pure_love_pending_enable_date",
    )
