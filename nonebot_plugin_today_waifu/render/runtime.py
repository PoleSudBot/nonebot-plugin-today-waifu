from __future__ import annotations

import asyncio
from collections import OrderedDict
import time

import httpx

from ..config import plugin_config

_AVATAR_CACHE_MAX_ITEMS = 256

_client: httpx.AsyncClient | None = None
_avatar_cache: OrderedDict[str, tuple[float, bytes]] = OrderedDict()
_avatar_inflight: dict[str, asyncio.Task[bytes]] = {}
_avatar_lock = asyncio.Lock()


def _avatar_cache_ttl() -> float:
    return float(max(0, plugin_config.today_waifu_theme_avatar_cache_ttl_seconds))


def _http_timeout() -> float:
    return float(max(1, plugin_config.today_waifu_theme_http_timeout_seconds))


def _create_theme_card_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(follow_redirects=True)


def _get_theme_card_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = _create_theme_card_client()
    return _client


def _get_cached_avatar_bytes_nolock(url: str) -> bytes | None:
    entry = _avatar_cache.get(url)
    if not entry:
        return None
    expire_at, avatar_bytes = entry
    if expire_at <= time.monotonic():
        _avatar_cache.pop(url, None)
        return None
    _avatar_cache.move_to_end(url)
    return avatar_bytes


def _cleanup_avatar_cache_nolock() -> None:
    now = time.monotonic()
    while _avatar_cache:
        expire_at, _ = next(iter(_avatar_cache.values()))
        if expire_at > now:
            break
        _avatar_cache.popitem(last=False)
    while len(_avatar_cache) > _AVATAR_CACHE_MAX_ITEMS:
        _avatar_cache.popitem(last=False)


async def _fetch_avatar_bytes(url: str) -> bytes:
    response = await _get_theme_card_client().get(url, timeout=_http_timeout())
    response.raise_for_status()
    return response.content


async def get_avatar_bytes(url: str) -> bytes:
    ttl = _avatar_cache_ttl()

    async with _avatar_lock:
        if ttl > 0:
            cached = _get_cached_avatar_bytes_nolock(url)
            if cached is not None:
                return cached

        task = _avatar_inflight.get(url)
        if task is None:
            task = asyncio.create_task(_fetch_avatar_bytes(url))
            _avatar_inflight[url] = task

            def _cleanup(_: asyncio.Task[bytes], key: str = url) -> None:
                _avatar_inflight.pop(key, None)

            task.add_done_callback(_cleanup)

    avatar_bytes = await task
    if ttl <= 0:
        return avatar_bytes

    async with _avatar_lock:
        _avatar_cache[url] = (time.monotonic() + ttl, avatar_bytes)
        _avatar_cache.move_to_end(url)
        _cleanup_avatar_cache_nolock()
    return avatar_bytes


async def close_theme_card_client() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
    _avatar_cache.clear()
    _avatar_inflight.clear()
