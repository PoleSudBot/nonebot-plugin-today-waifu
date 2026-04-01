from __future__ import annotations

import random
from typing import Any

from PIL.Image import Image as PILImage

from ..config import BANGDREAM_ASSET_DIR
from .common import (
    OUTPUT_SIZE,
    choose_by_weight,
    clone_overlay_longest_edge,
    clone_overlay_resized,
    clone_overlay_width,
    fit_square,
    paste,
)

KEY = "bangdream"
ATTRIBUTES = ("cool", "happy", "powerful", "pure")
BANDS = ("ppp", "ag", "pp", "r", "hhw", "ras", "mnk", "go")
STAR_WEIGHTS = (
    (3, 30),
    (4, 40),
    (5, 30),
)
STAR_TYPE_WEIGHTS = (
    ("normal", 50),
    ("color", 50),
)
BASE_CANVAS_SIZE = 1000


def build_payload() -> dict[str, Any]:
    return {
        "attribute": random.choice(ATTRIBUTES),
        "band": random.choice(BANDS),
        "star_count": choose_by_weight(STAR_WEIGHTS),
        "star_type": choose_by_weight(STAR_TYPE_WEIGHTS),
    }


def build_context(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "output_size": OUTPUT_SIZE,
        "border_path": BANGDREAM_ASSET_DIR / f"card-{payload['star_count']}.png",
        "attr_path": BANGDREAM_ASSET_DIR / f"{payload['attribute']}.png",
        "band_path": BANGDREAM_ASSET_DIR / f"{payload['band']}.png",
        "star_path": BANGDREAM_ASSET_DIR
        / ("color_star.png" if payload["star_type"] == "color" else "normal_star.png"),
        "star_count": payload["star_count"],
    }


def render_card(avatar: PILImage, theme_data: dict[str, Any]) -> PILImage:
    canvas_size = int(theme_data.get("output_size", OUTPUT_SIZE))
    ratio = canvas_size / BASE_CANVAS_SIZE
    base = fit_square(avatar, canvas_size)

    border = clone_overlay_resized(
        theme_data["border_path"],
        (canvas_size, canvas_size),
    )
    attr = clone_overlay_resized(
        theme_data["attr_path"],
        (round(260 * ratio), round(260 * ratio)),
    )
    band = clone_overlay_longest_edge(theme_data["band_path"], round(240 * ratio))
    star = clone_overlay_width(theme_data["star_path"], round(180 * ratio))

    paste(base, border, (0, 0))
    paste(base, attr, (round(734 * ratio), round(6 * ratio)))
    paste(base, band, (round(30 * ratio), round(30 * ratio)))

    star_x = round(20 * ratio)
    star_y = round(820 * ratio)
    star_step = round(120 * ratio)
    for index in range(theme_data["star_count"]):
        paste(base, star, (star_x, star_y - index * star_step))

    return base
