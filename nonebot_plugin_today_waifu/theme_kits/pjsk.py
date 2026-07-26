from __future__ import annotations

import random
from typing import Any

from ..config import PJSK_ASSET_DIR
from .common import (
    OUTPUT_SIZE,
    OverlaySpec,
    RoundedRectCropSpec,
    ThemeCardSpec,
    choose_by_weight,
)

KEY = "pjsk"
ATTRIBUTES = ("cool", "cute", "happy", "mysterious", "pure")
RARITY_WEIGHTS = (
    ("3", 60),
    ("birthday", 10),
    ("4", 30),
)
TRAINING_WEIGHTS = (
    ("normal", 50),
    ("after_training", 50),
)
BASE_CANVAS_SIZE = 156
CARD_SIZE = 156
ATTR_SIZE = 35
STAR_SIZE = 24
STAR_POSITIONS = (
    (5, 125),
    (29, 125),
    (53, 125),
    (77, 125),
)


def build_payload() -> dict[str, Any]:
    rarity = str(choose_by_weight(RARITY_WEIGHTS))
    return {
        "attribute": random.choice(ATTRIBUTES),
        "rarity": rarity,
        "training_state": choose_by_weight(TRAINING_WEIGHTS),
        "star_count": 4 if rarity in {"4", "birthday"} else 3,
    }


def build_render_spec(payload: dict[str, Any]) -> ThemeCardSpec:
    rarity = payload["rarity"]
    frame_name = {
        "3": "frame_rarity_3.png",
        "4": "frame_rarity_4.png",
        "birthday": "frame_rarity_birthday.png",
    }[rarity]
    if rarity == "birthday":
        star_name = "rare_birthday.png"
        star_render_count = 1
    elif payload["training_state"] == "after_training":
        star_name = "rarity-star-after-training.png"
        star_render_count = int(payload["star_count"])
    else:
        star_name = "rare_star_normal.png"
        star_render_count = int(payload["star_count"])

    return ThemeCardSpec(
        base_canvas_size=BASE_CANVAS_SIZE,
        avatar_box=(0, 0, CARD_SIZE, CARD_SIZE),
        output_size=OUTPUT_SIZE,
        overlays=(
            OverlaySpec(
                path=PJSK_ASSET_DIR / frame_name,
                size=(CARD_SIZE, CARD_SIZE),
            ),
            OverlaySpec(
                path=PJSK_ASSET_DIR / f"attr_{payload['attribute']}.png",
                size=(ATTR_SIZE, ATTR_SIZE),
            ),
            OverlaySpec(
                path=PJSK_ASSET_DIR / star_name,
                positions=STAR_POSITIONS[:star_render_count],
                size=(STAR_SIZE, STAR_SIZE),
            ),
        ),
        final_crop=RoundedRectCropSpec(
            box=(0, 0, CARD_SIZE, CARD_SIZE),
            radius=8,
        ),
    )
