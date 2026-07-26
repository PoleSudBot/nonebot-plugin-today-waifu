from __future__ import annotations

import asyncio
from typing import Any

from ..theme_kits.common import render_card_by_spec
from ..themes import build_theme_render_spec
from .avatar import AvatarRef, AvatarSource, load_avatar_image, resolve_avatar_source
from .style import image_to_png


def compose_theme_card(
    avatar_source: AvatarSource,
    theme_key: str,
    payload: dict[str, Any],
) -> bytes:
    avatar = load_avatar_image(avatar_source)
    image = render_card_by_spec(avatar, build_theme_render_spec(theme_key, payload))
    return image_to_png(image)


async def render_theme_card(
    avatar_ref: AvatarRef,
    theme_key: str,
    payload: dict[str, Any],
) -> bytes:
    avatar_source = await resolve_avatar_source(avatar_ref)
    if avatar_source is None:
        raise ValueError(f"avatar unavailable: {avatar_ref.user_id}")
    return await asyncio.to_thread(
        compose_theme_card,
        avatar_source,
        theme_key,
        payload,
    )
