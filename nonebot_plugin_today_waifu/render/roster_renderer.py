from __future__ import annotations

import asyncio
from dataclasses import dataclass
from math import ceil

from PIL import ImageDraw

from .avatar import AvatarRef, AvatarSource, resolve_avatar_sources
from .style import (
    BORDER,
    PRIMARY,
    PRIMARY_SOFT,
    TEXT_DARK,
    TEXT_MUTED,
    create_canvas,
    draw_centered_text,
    draw_panel,
    ellipsize_text,
    font,
    image_to_png,
    paste_circle_avatar,
)

PAGE_WIDTH = 1000
PAGE_PADDING = 40
PANEL_PADDING = 32
COLUMNS = 4
GRID_GAP = 16
CARD_HEIGHT = 170
HEADER_HEIGHT = 100


@dataclass(frozen=True, slots=True)
class RosterPair:
    left_name: str
    left_avatar: AvatarRef
    right_name: str
    right_avatar: AvatarRef


def _draw_heart(
    draw: ImageDraw.ImageDraw,
    center: tuple[int, int],
    *,
    size: int,
    fill: str,
) -> None:
    center_x, center_y = center
    radius = max(2, size // 4)
    lobe_top = center_y - radius
    lobe_bottom = center_y + radius
    draw.ellipse(
        (center_x - radius * 2, lobe_top, center_x, lobe_bottom),
        fill=fill,
    )
    draw.ellipse(
        (center_x, lobe_top, center_x + radius * 2, lobe_bottom),
        fill=fill,
    )
    draw.polygon(
        (
            (center_x - radius * 2, center_y),
            (center_x + radius * 2, center_y),
            (center_x, center_y + radius * 3),
        ),
        fill=fill,
    )


def _compose_cp_roster(
    scene_id: str,
    pairs: list[RosterPair],
    avatar_sources: dict[AvatarRef, AvatarSource | None],
) -> bytes:
    row_count = ceil(len(pairs) / COLUMNS)
    panel_height = (
        PANEL_PADDING * 2
        + HEADER_HEIGHT
        + 24
        + row_count * CARD_HEIGHT
        + max(0, row_count - 1) * GRID_GAP
    )
    page_height = panel_height + PAGE_PADDING * 2
    canvas = create_canvas(PAGE_WIDTH, page_height)
    panel_box = (
        PAGE_PADDING,
        PAGE_PADDING,
        PAGE_WIDTH - PAGE_PADDING,
        PAGE_PADDING + panel_height,
    )
    draw_panel(canvas, panel_box, radius=30)
    draw = ImageDraw.Draw(canvas)
    title_font = font(38, "bold")
    meta_font = font(16, "medium")
    name_font = font(17, "medium")

    content_left = PAGE_PADDING + PANEL_PADDING
    content_right = PAGE_WIDTH - PAGE_PADDING - PANEL_PADDING
    draw_centered_text(
        draw,
        (content_left, PAGE_PADDING + 24, content_right, PAGE_PADDING + 78),
        "本群 CP 花名册",
        text_font=title_font,
        fill=TEXT_DARK,
    )
    draw_centered_text(
        draw,
        (content_left, PAGE_PADDING + 76, content_right, PAGE_PADDING + 104),
        f"SCENE ID · {scene_id}",
        text_font=meta_font,
        fill=TEXT_MUTED,
    )
    divider_y = PAGE_PADDING + PANEL_PADDING + HEADER_HEIGHT
    draw.line((content_left, divider_y, content_right, divider_y), fill=BORDER, width=2)

    grid_top = divider_y + 24
    grid_width = content_right - content_left
    card_width = (grid_width - GRID_GAP * (COLUMNS - 1)) // COLUMNS
    avatar_size = 68
    avatar_overlap = 18

    for index, pair in enumerate(pairs):
        row, column = divmod(index, COLUMNS)
        left = content_left + column * (card_width + GRID_GAP)
        top = grid_top + row * (CARD_HEIGHT + GRID_GAP)
        right = left + card_width
        bottom = top + CARD_HEIGHT
        draw.rounded_rectangle(
            (left, top, right, bottom),
            radius=18,
            fill=PRIMARY_SOFT,
            outline=BORDER,
            width=2,
        )

        avatars_width = avatar_size * 2 - avatar_overlap
        avatar_left = left + (card_width - avatars_width) // 2
        avatar_top = top + 16
        paste_circle_avatar(
            canvas,
            avatar_sources.get(pair.left_avatar),
            (
                avatar_left,
                avatar_top,
                avatar_left + avatar_size,
                avatar_top + avatar_size,
            ),
            name=pair.left_name,
        )
        right_avatar_left = avatar_left + avatar_size - avatar_overlap
        paste_circle_avatar(
            canvas,
            avatar_sources.get(pair.right_avatar),
            (
                right_avatar_left,
                avatar_top,
                right_avatar_left + avatar_size,
                avatar_top + avatar_size,
            ),
            name=pair.right_name,
        )

        text_max_width = card_width - 20
        left_name = ellipsize_text(draw, pair.left_name, name_font, text_max_width)
        right_name = ellipsize_text(draw, pair.right_name, name_font, text_max_width)
        draw_centered_text(
            draw,
            (left + 10, top + 96, right - 10, top + 120),
            left_name,
            text_font=name_font,
            fill=TEXT_DARK,
        )
        _draw_heart(
            draw,
            ((left + right) // 2, top + 128),
            size=16,
            fill=PRIMARY,
        )
        draw_centered_text(
            draw,
            (left + 10, top + 141, right - 10, bottom - 6),
            right_name,
            text_font=name_font,
            fill=TEXT_DARK,
        )

    return image_to_png(canvas)


async def render_cp_roster(scene_id: str, pairs: list[RosterPair]) -> bytes:
    refs = [ref for pair in pairs for ref in (pair.left_avatar, pair.right_avatar)]
    avatar_sources = await resolve_avatar_sources(refs)
    return await asyncio.to_thread(_compose_cp_roster, scene_id, pairs, avatar_sources)
