from __future__ import annotations

import asyncio
from dataclasses import dataclass

from PIL import ImageDraw

from .style import (
    BORDER,
    PRIMARY_DARK,
    PRIMARY_SOFT,
    TEXT_DARK,
    TEXT_MUTED,
    create_canvas,
    draw_centered_text,
    draw_panel,
    font,
    image_to_png,
    wrap_text,
)

PAGE_WIDTH = 1100
PAGE_HEIGHT = 760


@dataclass(frozen=True, slots=True)
class ReportCard:
    label: str
    value: str | None
    description: str
    empty_text: str


@dataclass(frozen=True, slots=True)
class FateReport:
    title: str
    scene_id: str
    range_text: str
    cards: tuple[ReportCard, ReportCard, ReportCard]


def _compose_fate_report(report: FateReport) -> bytes:
    canvas = create_canvas(PAGE_WIDTH, PAGE_HEIGHT)
    draw_panel(canvas, (40, 40, PAGE_WIDTH - 40, PAGE_HEIGHT - 40), radius=30)
    draw = ImageDraw.Draw(canvas)
    title_font = font(44, "bold")
    meta_font = font(16, "medium")
    label_font = font(17, "medium")
    value_font = font(30, "bold")
    desc_font = font(18)

    draw_centered_text(
        draw,
        (80, 70, PAGE_WIDTH - 80, 126),
        report.title,
        text_font=title_font,
        fill=TEXT_DARK,
    )
    draw_centered_text(
        draw,
        (80, 126, PAGE_WIDTH - 80, 158),
        f"SCENE ID · {report.scene_id}    RANGE · {report.range_text}",
        text_font=meta_font,
        fill=TEXT_MUTED,
    )
    draw.line((88, 174, PAGE_WIDTH - 88, 174), fill=BORDER, width=2)

    card_top = 204
    card_bottom = 680
    card_left = 88
    gap = 24
    card_width = (PAGE_WIDTH - card_left * 2 - gap * 2) // 3
    for index, card in enumerate(report.cards):
        left = card_left + index * (card_width + gap)
        right = left + card_width
        draw.rounded_rectangle(
            (left, card_top, right, card_bottom),
            radius=20,
            fill="#FFFFFF",
            outline=BORDER,
            width=2,
        )
        label_box = (left + 24, card_top + 26, left + 126, card_top + 64)
        draw.rounded_rectangle(label_box, radius=10, fill=PRIMARY_SOFT, outline=BORDER)
        draw_centered_text(
            draw,
            label_box,
            card.label,
            text_font=label_font,
            fill=PRIMARY_DARK,
        )

        value = card.value
        if value:
            value_lines = wrap_text(
                draw,
                value,
                value_font,
                card_width - 48,
                max_lines=3,
            )
            value_y = card_top + 104
            for line in value_lines:
                draw.text((left + 24, value_y), line, font=value_font, fill=TEXT_DARK)
                value_y += 48
            description = card.description
            description_fill = TEXT_MUTED
        else:
            description = card.empty_text
            description_fill = TEXT_MUTED

        description_lines = wrap_text(
            draw,
            description,
            desc_font,
            card_width - 48,
            max_lines=5,
        )
        description_y = card_bottom - 34 - len(description_lines) * 31
        for line in description_lines:
            draw.text(
                (left + 24, description_y),
                line,
                font=desc_font,
                fill=description_fill,
            )
            description_y += 31

    return image_to_png(canvas)


async def render_fate_report(report: FateReport) -> bytes:
    return await asyncio.to_thread(_compose_fate_report, report)
