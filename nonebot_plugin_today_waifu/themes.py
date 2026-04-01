from __future__ import annotations

from dataclasses import dataclass

from .constants import (
    THEME_DISPLAY_NAMES,
    THEME_INDEX_TO_KEY,
    THEME_KEY_TO_INDEX,
)
from .theme_kits import get_theme_module


@dataclass(slots=True)
class ThemeDefinition:
    key: str
    index: int
    display_name: str


THEMES = [
    ThemeDefinition("bangdream", 1, THEME_DISPLAY_NAMES["bangdream"]),
    ThemeDefinition("pjsk", 2, THEME_DISPLAY_NAMES["pjsk"]),
]


def list_theme_lines() -> list[str]:
    return [
        f"{theme.index}. {theme.display_name} ({theme.key})"
        for theme in THEMES
    ]


def parse_theme_selection(raw: str) -> list[str]:
    normalized = raw.replace("，", ",").strip().lower()
    if normalized == "all":
        return [theme.key for theme in THEMES]
    if normalized == "none":
        return []
    results: list[str] = []
    for token in [item.strip() for item in normalized.split(",") if item.strip()]:
        if not token.isdigit():
            raise ValueError("主题参数只支持 all / none / 主题序号列表")
        index = int(token)
        if index not in THEME_INDEX_TO_KEY:
            raise ValueError(f"未知主题序号: {token}")
        key = THEME_INDEX_TO_KEY[index]
        if key not in results:
            results.append(key)
    return results


def format_theme_keys(keys: list[str]) -> str:
    if not keys:
        return "无主题"
    return "、".join(f"{THEME_KEY_TO_INDEX[key]}.{THEME_DISPLAY_NAMES[key]}" for key in keys)


def build_theme_payload(theme_key: str) -> dict:
    return get_theme_module(theme_key).build_payload()


def build_theme_context(theme_key: str, payload: dict) -> dict:
    return get_theme_module(theme_key).build_context(payload)
