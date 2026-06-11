"""normalize theme preference keys

修订 ID: b6b8f7b6d0a2
父修订: 7d8b7d8d9c2e
创建时间: 2026-05-13 12:00:00.000000
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from alembic import op
import sqlalchemy as sa

if TYPE_CHECKING:
    from collections.abc import Sequence

revision: str = "b6b8f7b6d0a2"
down_revision: str | Sequence[str] | None = "7d8b7d8d9c2e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE_NAME = "nonebot_plugin_today_waifu_theme_preference"


def upgrade(name: str = "") -> None:
    if name:
        return

    # 历史表里 NULL 会绕过唯一约束，先归一化并去重，再收紧列约束。
    op.execute(sa.text(f"UPDATE {TABLE_NAME} SET scene_id = '' WHERE scene_id IS NULL"))
    op.execute(sa.text(f"UPDATE {TABLE_NAME} SET user_id = '' WHERE user_id IS NULL"))
    op.execute(
        sa.text(
            f"""
            DELETE FROM {TABLE_NAME}
            WHERE id NOT IN (
                SELECT keep_id FROM (
                    SELECT MAX(id) AS keep_id
                    FROM {TABLE_NAME}
                    GROUP BY scope, scene_id, user_id
                ) AS keep_rows
            )
            """
        )
    )
    with op.batch_alter_table(TABLE_NAME) as batch_op:
        batch_op.alter_column(
            "scene_id",
            existing_type=sa.String(length=64),
            nullable=False,
            server_default="",
        )
        batch_op.alter_column(
            "user_id",
            existing_type=sa.String(length=64),
            nullable=False,
            server_default="",
        )


def downgrade(name: str = "") -> None:
    if name:
        return
    with op.batch_alter_table(TABLE_NAME) as batch_op:
        batch_op.alter_column(
            "scene_id",
            existing_type=sa.String(length=64),
            nullable=True,
            server_default=None,
        )
        batch_op.alter_column(
            "user_id",
            existing_type=sa.String(length=64),
            nullable=True,
            server_default=None,
        )
