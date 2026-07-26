from __future__ import annotations

import asyncio
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import TypeAlias

import httpx
from nonebot import logger
from PIL import Image, UnidentifiedImageError
from PIL.Image import Image as PILImage

from ..config import plugin_config

AvatarSource: TypeAlias = Path | bytes
AVATAR_FETCH_CONCURRENCY = 8


@dataclass(frozen=True, slots=True)
class AvatarRef:
    platform: str
    user_id: str
    fallback_url: str | None = None


def _get_avatar_service():
    from zhenxun.services import avatar_service

    return avatar_service


def _get_http_client():
    from zhenxun.utils.http_utils import AsyncHttpx

    return AsyncHttpx


def load_avatar_image(source: AvatarSource) -> PILImage:
    if isinstance(source, Path):
        with Image.open(source) as image:
            return image.convert("RGBA")
    with Image.open(BytesIO(source)) as image:
        return image.convert("RGBA")


def _validate_avatar_source(source: AvatarSource) -> None:
    if isinstance(source, Path):
        with Image.open(source) as image:
            image.verify()
        return
    with Image.open(BytesIO(source)) as image:
        image.verify()


async def _validated_cached_avatar(ref: AvatarRef) -> Path | None:
    service = _get_avatar_service()
    try:
        avatar_path = await service.get_avatar_path(ref.platform, ref.user_id)
    except (httpx.HTTPError, OSError, ValueError) as exc:
        logger.warning(
            f"TodayWaifu 头像缓存不可用，尝试原始地址: {exc}",
            "TodayWaifu",
            target=ref.user_id,
            platform=ref.platform,
        )
        return None
    if avatar_path is None:
        return None
    try:
        await asyncio.to_thread(_validate_avatar_source, avatar_path)
        return avatar_path
    except (OSError, UnidentifiedImageError) as exc:
        logger.warning(
            f"TodayWaifu 头像缓存损坏，尝试强制刷新: {exc}",
            "TodayWaifu",
            target=ref.user_id,
            platform=ref.platform,
        )

    try:
        refreshed_path = await service.get_avatar_path(
            ref.platform,
            ref.user_id,
            force_refresh=True,
        )
    except (httpx.HTTPError, OSError, ValueError) as exc:
        logger.warning(
            f"TodayWaifu 头像缓存刷新失败，尝试原始地址: {exc}",
            "TodayWaifu",
            target=ref.user_id,
            platform=ref.platform,
        )
        return None
    if refreshed_path is None:
        return None
    try:
        await asyncio.to_thread(_validate_avatar_source, refreshed_path)
    except (OSError, UnidentifiedImageError) as exc:
        logger.warning(
            f"TodayWaifu 刷新后的头像仍无法解码: {exc}",
            "TodayWaifu",
            target=ref.user_id,
            platform=ref.platform,
        )
        return None
    return refreshed_path


async def resolve_avatar_source(ref: AvatarRef) -> AvatarSource | None:
    cached_path = await _validated_cached_avatar(ref)
    if cached_path is not None:
        return cached_path
    if not ref.fallback_url:
        return None

    try:
        avatar_bytes = await _get_http_client().get_content(
            ref.fallback_url,
            timeout=float(plugin_config.today_waifu_theme_http_timeout_seconds),
        )
        await asyncio.to_thread(_validate_avatar_source, avatar_bytes)
        return avatar_bytes
    except (httpx.HTTPError, OSError, UnidentifiedImageError, ValueError) as exc:
        logger.warning(
            f"TodayWaifu 头像获取失败，使用占位图: {exc}",
            "TodayWaifu",
            target=ref.user_id,
            platform=ref.platform,
        )
        return None


async def resolve_avatar_sources(
    refs: list[AvatarRef],
) -> dict[AvatarRef, AvatarSource | None]:
    unique_refs = list(dict.fromkeys(refs))
    if not unique_refs:
        return {}
    semaphore = asyncio.Semaphore(min(AVATAR_FETCH_CONCURRENCY, len(unique_refs)))

    async def _resolve(ref: AvatarRef) -> tuple[AvatarRef, AvatarSource | None]:
        async with semaphore:
            return ref, await resolve_avatar_source(ref)

    results = await asyncio.gather(*[_resolve(ref) for ref in unique_refs])
    return dict(results)
