from __future__ import annotations

from io import BytesIO
from typing import Any

from nonebot.utils import run_sync
from PIL import Image
from PIL.Image import Image as PILImage

from ..theme_kits import get_theme_module
from .runtime import get_avatar_bytes


def _open_image(image_bytes: bytes) -> PILImage:
    with Image.open(BytesIO(image_bytes)) as image:
        return image.convert("RGBA")


def compose_theme_card(avatar_bytes: bytes, theme_key: str, theme_data: dict) -> bytes:
    avatar = _open_image(avatar_bytes)
    image = get_theme_module(theme_key).render_card(avatar, theme_data)

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
