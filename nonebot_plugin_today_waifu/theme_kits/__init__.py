from __future__ import annotations

from . import bangdream, pjsk

THEME_MODULES = {
    bangdream.KEY: bangdream,
    pjsk.KEY: pjsk,
}


def get_theme_module(theme_key: str):
    try:
        return THEME_MODULES[theme_key]
    except KeyError as exc:
        raise ValueError(f"unknown theme: {theme_key}") from exc


__all__ = ["get_theme_module"]
