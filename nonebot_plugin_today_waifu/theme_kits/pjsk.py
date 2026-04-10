from __future__ import annotations

import random
from typing import Any

from PIL.Image import Image as PILImage

from ..config import PJSK_ASSET_DIR
from .common import (
    OverlaySpec,
    OUTPUT_SIZE,
    RoundedRectClipSpec,
    ThemeCardSpec,
    choose_by_weight,
    render_card_by_spec,
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
    context = {
        "output_size": OUTPUT_SIZE,
        "frame_path": PJSK_ASSET_DIR / frame_name,
        "attr_path": PJSK_ASSET_DIR / f"attr_{payload['attribute']}.png",
        "star_path": PJSK_ASSET_DIR / star_name,
        "star_count": payload["star_count"],
        "star_render_count": star_render_count,
    }
    return {**context, "render_spec": build_render_spec(context)}


def build_render_spec(theme_data: dict[str, Any]) -> ThemeCardSpec:
    star_render_count = int(theme_data.get("star_render_count", theme_data["star_count"]))
    return ThemeCardSpec(
        base_canvas_size=BASE_CANVAS_SIZE,
        avatar_box=(0, 0, CARD_SIZE, CARD_SIZE),
        output_size=int(theme_data.get("output_size", OUTPUT_SIZE)),
        post_clip=RoundedRectClipSpec(box=(2, 2, 152, 152), radius=8),
        overlays=(
            OverlaySpec(
                path=theme_data["frame_path"],
                size=(CARD_SIZE, CARD_SIZE),
            ),
            OverlaySpec(
                path=theme_data["attr_path"],
                size=(ATTR_SIZE, ATTR_SIZE),
            ),
            OverlaySpec(
                path=theme_data["star_path"],
                positions=STAR_POSITIONS[:star_render_count],
                size=(STAR_SIZE, STAR_SIZE),
            ),
        ),
    )


def render_card(avatar: PILImage, theme_data: dict[str, Any]) -> PILImage:
    return render_card_by_spec(avatar, build_render_spec(theme_data))
