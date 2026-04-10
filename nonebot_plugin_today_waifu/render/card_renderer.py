from __future__ import annotations

from io import BytesIO
from typing import Any

from nonebot.utils import run_sync
from PIL import Image
from PIL.Image import Image as PILImage

from ..theme_kits import get_theme_module
from ..theme_kits.common import render_card_by_spec
from .runtime import get_avatar_bytes


def _open_image(image_bytes: bytes) -> PILImage:
    with Image.open(BytesIO(image_bytes)) as image:
        return image.convert("RGBA")


def compose_theme_card(avatar_bytes: bytes, theme_key: str, theme_data: dict) -> bytes:
    avatar = _open_image(avatar_bytes)
    module = get_theme_module(theme_key)
    spec = None
    if hasattr(module, "build_render_spec"):
        spec = module.build_render_spec(theme_data)
    elif theme_data.get("render_spec") is not None:
        spec = theme_data["render_spec"]
    image = render_card_by_spec(avatar, spec) if spec is not None else module.render_card(avatar, theme_data)

    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


async def render_theme_card(
    avatar_url: str,
    theme_key: str,
    theme_data: dict[str, Any],
) -> bytes:
    avatar_bytes = await get_avatar_bytes(avatar_url)
    return await run_sync(compose_theme_card)(avatar_bytes, theme_key, theme_data)
