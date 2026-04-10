from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import random
from typing import Literal, TypeAlias, TypeVar

from PIL import Image, ImageChops, ImageDraw, ImageOps
from PIL.Image import Image as PILImage
from PIL.Image import Resampling

OUTPUT_SIZE = 1024

T = TypeVar("T")
Point: TypeAlias = tuple[int, int]
Size: TypeAlias = tuple[int, int]
Rect: TypeAlias = tuple[int, int, int, int]
OverlayResizeMode: TypeAlias = Literal["stretch", "longest_edge", "width"]


@dataclass(frozen=True, slots=True)
class RoundedRectClipSpec:
    box: Rect
    radius: int
    kind: Literal["rounded_rect"] = "rounded_rect"


@dataclass(frozen=True, slots=True)
class FrameWindowClipSpec:
    frame_path: Path
    kind: Literal["frame_window"] = "frame_window"


@dataclass(frozen=True, slots=True)
class MaskClipSpec:
    mask_path: Path
    kind: Literal["mask"] = "mask"


CardClipSpec: TypeAlias = (
    RoundedRectClipSpec
    | FrameWindowClipSpec
    | MaskClipSpec
)


@dataclass(frozen=True, slots=True)
class OverlaySpec:
    path: Path
    positions: tuple[Point, ...] = ((0, 0),)
    resize_mode: OverlayResizeMode = "stretch"
    size: Size | None = None
    longest_edge: int | None = None
    width: int | None = None


@dataclass(frozen=True, slots=True)
class ThemeCardSpec:
    base_canvas_size: int
    avatar_box: Rect
    output_size: int = OUTPUT_SIZE
    clip: CardClipSpec | None = None
    post_clip: CardClipSpec | None = None
    overlays: tuple[OverlaySpec, ...] = ()


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


@lru_cache(maxsize=128)
def load_mask(path: str) -> PILImage:
    with Image.open(path) as image:
        if "A" in image.getbands():
            return image.getchannel("A")
        return image.convert("L")


def clone_mask(path: Path) -> PILImage:
    return load_mask(str(path)).copy()


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


@lru_cache(maxsize=128)
def load_frame_window_mask(path: str) -> PILImage:
    alpha = load_overlay(path).getchannel("A")
    width, height = alpha.size
    solid = [[alpha.getpixel((x, y)) > 0 for x in range(width)] for y in range(height)]
    outside = [[False] * width for _ in range(height)]
    queue: deque[Point] = deque()

    for x in range(width):
        for y in (0, height - 1):
            if solid[y][x] or outside[y][x]:
                continue
            outside[y][x] = True
            queue.append((x, y))
    for y in range(height):
        for x in (0, width - 1):
            if solid[y][x] or outside[y][x]:
                continue
            outside[y][x] = True
            queue.append((x, y))

    while queue:
        x, y = queue.popleft()
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if not (0 <= nx < width and 0 <= ny < height):
                continue
            if solid[ny][nx] or outside[ny][nx]:
                continue
            outside[ny][nx] = True
            queue.append((nx, ny))

    mask = Image.new("L", (width, height))
    for y in range(height):
        for x in range(width):
            if not solid[y][x] and not outside[y][x]:
                mask.putpixel((x, y), 255)
    return mask


def clone_frame_window_mask(path: Path) -> PILImage:
    return load_frame_window_mask(str(path)).copy()

def fit_size(image: PILImage, size: Size) -> PILImage:
    return ImageOps.fit(
        image,
        size,
        method=Resampling.LANCZOS,
        centering=(0.5, 0.5),
    )


def fit_square(image: PILImage, size: int) -> PILImage:
    return fit_size(image, (size, size))


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


def scale_value(value: int, ratio: float) -> int:
    return max(1, round(value * ratio))


def scale_size(size: Size, ratio: float) -> Size:
    return (scale_value(size[0], ratio), scale_value(size[1], ratio))


def scale_point(point: Point, ratio: float) -> Point:
    return (round(point[0] * ratio), round(point[1] * ratio))


def scale_box(box: Rect, ratio: float) -> Rect:
    return (
        round(box[0] * ratio),
        round(box[1] * ratio),
        scale_value(box[2], ratio),
        scale_value(box[3], ratio),
    )


def _resolve_overlay(overlay: OverlaySpec, ratio: float) -> PILImage:
    if overlay.resize_mode == "stretch":
        if overlay.size is None:
            raise ValueError("stretch overlay requires size")
        return clone_overlay_resized(overlay.path, scale_size(overlay.size, ratio))
    if overlay.resize_mode == "longest_edge":
        if overlay.longest_edge is None:
            raise ValueError("longest_edge overlay requires longest_edge")
        return clone_overlay_longest_edge(
            overlay.path,
            scale_value(overlay.longest_edge, ratio),
        )
    if overlay.resize_mode == "width":
        if overlay.width is None:
            raise ValueError("width overlay requires width")
        return clone_overlay_width(overlay.path, scale_value(overlay.width, ratio))
    raise ValueError(f"unknown overlay resize mode: {overlay.resize_mode}")


def _build_clip_mask(clip: CardClipSpec, canvas_size: int, ratio: float) -> PILImage:
    if clip.kind == "rounded_rect":
        x, y, width, height = scale_box(clip.box, ratio)
        mask = Image.new("L", (canvas_size, canvas_size))
        draw = ImageDraw.Draw(mask)
        draw.rounded_rectangle(
            (x, y, x + width, y + height),
            radius=max(0, round(clip.radius * ratio)),
            fill=255,
        )
        return mask
    if clip.kind == "frame_window":
        return clone_frame_window_mask(clip.frame_path).resize(
            (canvas_size, canvas_size),
            Resampling.LANCZOS,
        )
    if clip.kind == "mask":
        return clone_mask(clip.mask_path).resize(
            (canvas_size, canvas_size),
            Resampling.LANCZOS,
        )
    raise ValueError(f"unknown clip kind: {clip.kind}")


def _apply_clip_mask(image: PILImage, mask: PILImage) -> None:
    alpha = ImageChops.multiply(image.getchannel("A"), mask)
    image.putalpha(alpha)


def render_card_by_spec(avatar: PILImage, spec: ThemeCardSpec) -> PILImage:
    canvas_size = int(spec.output_size)
    ratio = canvas_size / spec.base_canvas_size
    base = Image.new("RGBA", (canvas_size, canvas_size))

    avatar_x, avatar_y, avatar_width, avatar_height = scale_box(spec.avatar_box, ratio)
    avatar_region = fit_size(avatar, (avatar_width, avatar_height))
    base.paste(avatar_region, (avatar_x, avatar_y), avatar_region)

    if spec.clip is not None:
        mask = _build_clip_mask(spec.clip, canvas_size, ratio)
        _apply_clip_mask(base, mask)

    for overlay in spec.overlays:
        image = _resolve_overlay(overlay, ratio)
        for position in overlay.positions:
            paste(base, image, scale_point(position, ratio))

    if spec.post_clip is not None:
        mask = _build_clip_mask(spec.post_clip, canvas_size, ratio)
        _apply_clip_mask(base, mask)

    return base
