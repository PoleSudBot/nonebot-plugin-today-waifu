from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import random
from typing import TypeVar

from PIL import Image, ImageOps
from PIL.Image import Image as PILImage
from PIL.Image import Resampling

OUTPUT_SIZE = 1024

T = TypeVar("T")


def choose_by_weight(options: tuple[tuple[T, int], ...]) -> T:
    values = [item[0] for item in options]
    weights = [item[1] for item in options]
    return random.choices(values, weights=weights, k=1)[0]


@lru_cache(maxsize=128)
def load_overlay(path: str) -> PILImage:
    with Image.open(path) as image:
        return image.convert("RGBA")


def clone_overlay(path: Path) -> PILImage:
    return load_overlay(str(path)).copy()


@lru_cache(maxsize=256)
def load_overlay_resized(path: str, width: int, height: int) -> PILImage:
    return load_overlay(path).resize((width, height), Resampling.LANCZOS)


def clone_overlay_resized(path: Path, size: tuple[int, int]) -> PILImage:
    return load_overlay_resized(str(path), size[0], size[1]).copy()


@lru_cache(maxsize=256)
def load_overlay_longest_edge(path: str, size: int) -> PILImage:
    image = load_overlay(path).copy()
    image.thumbnail((size, size), Resampling.LANCZOS)
    return image


def clone_overlay_longest_edge(path: Path, size: int) -> PILImage:
    return load_overlay_longest_edge(str(path), size).copy()


@lru_cache(maxsize=256)
def load_overlay_width(path: str, width: int) -> PILImage:
    image = load_overlay(path)
    ratio = width / image.width
    height = max(1, round(image.height * ratio))
    return image.resize((width, height), Resampling.LANCZOS)


def clone_overlay_width(path: Path, width: int) -> PILImage:
    return load_overlay_width(str(path), width).copy()


def fit_square(image: PILImage, size: int) -> PILImage:
    return ImageOps.fit(
        image,
        (size, size),
        method=Resampling.LANCZOS,
        centering=(0.5, 0.5),
    )


def resize_longest_edge(image: PILImage, size: int) -> PILImage:
    copy = image.copy()
    copy.thumbnail((size, size), Resampling.LANCZOS)
    return copy


def resize_width(image: PILImage, width: int) -> PILImage:
    ratio = width / image.width
    height = max(1, round(image.height * ratio))
    return image.resize((width, height), Resampling.LANCZOS)


def paste(base: PILImage, overlay: PILImage, xy: tuple[int, int]) -> None:
    base.paste(overlay, xy, overlay)
