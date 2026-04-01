from __future__ import annotations

import random
from typing import Any

from PIL import Image
from PIL.Image import Image as PILImage

from ..config import PJSK_ASSET_DIR
from .common import (
    OUTPUT_SIZE,
    choose_by_weight,
    clone_overlay_resized,
    fit_square,
    paste,
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
AVATAR_XY = (2, 2)
AVATAR_SIZE = 152
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


def build_context(payload: dict[str, Any]) -> dict[str, Any]:
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
        star_render_count = payload["star_count"]
    else:
        star_name = "rare_star_normal.png"
        star_render_count = payload["star_count"]
    return {
        "output_size": OUTPUT_SIZE,
        "frame_path": PJSK_ASSET_DIR / frame_name,
        "attr_path": PJSK_ASSET_DIR / f"attr_{payload['attribute']}.png",
        "star_path": PJSK_ASSET_DIR / star_name,
        "star_count": payload["star_count"],
        "star_render_count": star_render_count,
    }


def render_card(avatar: PILImage, theme_data: dict[str, Any]) -> PILImage:
    canvas_size = int(theme_data.get("output_size", OUTPUT_SIZE))
    scale = canvas_size / BASE_CANVAS_SIZE
    star_render_count = int(theme_data.get("star_render_count", theme_data["star_count"]))
    base = Image.new("RGBA", (canvas_size, canvas_size))

    avatar_size = round(AVATAR_SIZE * scale)
    avatar_region = fit_square(avatar, avatar_size)
    paste(
        base,
        avatar_region,
        (round(AVATAR_XY[0] * scale), round(AVATAR_XY[1] * scale)),
    )

    frame = clone_overlay_resized(
        theme_data["frame_path"],
        (canvas_size, canvas_size),
    )
    attr = clone_overlay_resized(
        theme_data["attr_path"],
        (round(ATTR_SIZE * scale), round(ATTR_SIZE * scale)),
    )
    star = clone_overlay_resized(
        theme_data["star_path"],
        (round(STAR_SIZE * scale), round(STAR_SIZE * scale)),
    )

    paste(base, frame, (0, 0))
    paste(base, attr, (0, 0))
    for x, y in STAR_POSITIONS[:star_render_count]:
        paste(base, star, (round(x * scale), round(y * scale)))

    return base
