from __future__ import annotations

import random
from typing import Any

from ..config import BANGDREAM_ASSET_DIR
from .common import (
    OUTPUT_SIZE,
    ClosedFrameCropSpec,
    OverlaySpec,
    ThemeCardSpec,
    choose_by_weight,
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
FULL_CARD_SIZE = 1000
FRAME_SIZE = 1000
ATTR_XY = (734, 6)
ATTR_SIZE = 260
BAND_XY = (30, 30)
BAND_LONGEST_EDGE = 240
STAR_X = 20
STAR_Y = 800
STAR_STEP = 120
STAR_WIDTH = 180


def build_payload() -> dict[str, Any]:
    return {
        "attribute": random.choice(ATTRIBUTES),
        "band": random.choice(BANDS),
        "star_count": choose_by_weight(STAR_WEIGHTS),
        "star_type": choose_by_weight(STAR_TYPE_WEIGHTS),
    }


def build_render_spec(payload: dict[str, Any]) -> ThemeCardSpec:
    border_path = BANGDREAM_ASSET_DIR / f"card-{payload['star_count']}.png"
    star_path = BANGDREAM_ASSET_DIR / (
        "color_star.png" if payload["star_type"] == "color" else "normal_star.png"
    )
    positions = tuple(
        (STAR_X, STAR_Y - index * STAR_STEP)
        for index in range(int(payload["star_count"]))
    )
    return ThemeCardSpec(
        base_canvas_size=BASE_CANVAS_SIZE,
        avatar_box=(0, 0, FULL_CARD_SIZE, FULL_CARD_SIZE),
        output_size=OUTPUT_SIZE,
        overlays=(
            OverlaySpec(
                path=border_path,
                size=(FRAME_SIZE, FRAME_SIZE),
            ),
            OverlaySpec(
                path=BANGDREAM_ASSET_DIR / f"{payload['attribute']}.png",
                positions=(ATTR_XY,),
                size=(ATTR_SIZE, ATTR_SIZE),
            ),
            OverlaySpec(
                path=BANGDREAM_ASSET_DIR / f"{payload['band']}.png",
                positions=(BAND_XY,),
                resize_mode="longest_edge",
                longest_edge=BAND_LONGEST_EDGE,
            ),
            OverlaySpec(
                path=star_path,
                positions=positions,
                resize_mode="width",
                width=STAR_WIDTH,
            ),
        ),
        final_crop=ClosedFrameCropSpec(frame_path=border_path),
    )
