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

from zhenxun.utils._build_image import BuildImage

OUTPUT_SIZE = 1024
MASK_SUPERSAMPLE_SCALE = 4

T = TypeVar("T")
Point: TypeAlias = tuple[int, int]
Size: TypeAlias = tuple[int, int]
Rect: TypeAlias = tuple[int, int, int, int]
OverlayResizeMode: TypeAlias = Literal["stretch", "longest_edge", "width"]


@dataclass(frozen=True, slots=True)
class RoundedRectCropSpec:
    box: Rect
    radius: int
    kind: Literal["rounded_rect"] = "rounded_rect"


@dataclass(frozen=True, slots=True)
class ClosedFrameCropSpec:
    frame_path: Path
    kind: Literal["closed_frame"] = "closed_frame"


@dataclass(frozen=True, slots=True)
class MaskCropSpec:
    mask_path: Path
    kind: Literal["mask"] = "mask"


FinalCropSpec: TypeAlias = RoundedRectCropSpec | ClosedFrameCropSpec | MaskCropSpec


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
    overlays: tuple[OverlaySpec, ...] = ()
    final_crop: FinalCropSpec | None = None


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


def clone_overlay_resized(path: Path, size: Size) -> PILImage:
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
def load_closed_frame_mask(path: str) -> PILImage:
    alpha = load_overlay(path).getchannel("A")
    width, height = alpha.size
    pixel_count = width * height
    source_alpha = alpha.tobytes()
    filled_alpha = bytearray(pixel_count)

    for threshold in range(1, 256):
        outside = bytearray(pixel_count)
        queue: deque[int] = deque()

        def enqueue(pixel_index: int) -> None:
            if source_alpha[pixel_index] < threshold and not outside[pixel_index]:
                outside[pixel_index] = 1
                queue.append(pixel_index)

        for x_coordinate in range(width):
            enqueue(x_coordinate)
            enqueue((height - 1) * width + x_coordinate)
        for y_coordinate in range(height):
            enqueue(y_coordinate * width)
            enqueue(y_coordinate * width + width - 1)

        while queue:
            pixel_index = queue.popleft()
            x_coordinate = pixel_index % width
            y_coordinate = pixel_index // width
            if x_coordinate > 0:
                enqueue(pixel_index - 1)
            if x_coordinate + 1 < width:
                enqueue(pixel_index + 1)
            if y_coordinate > 0:
                enqueue(pixel_index - width)
            if y_coordinate + 1 < height:
                enqueue(pixel_index + width)

        for pixel_index, is_outside in enumerate(outside):
            if not is_outside:
                filled_alpha[pixel_index] = threshold

    return Image.frombytes("L", (width, height), bytes(filled_alpha))


def clone_closed_frame_mask(path: Path) -> PILImage:
    return load_closed_frame_mask(str(path)).copy()


def fit_size(image: PILImage, size: Size) -> PILImage:
    return ImageOps.fit(
        image,
        size,
        method=Resampling.LANCZOS,
        centering=(0.5, 0.5),
    )


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


def _build_antialiased_rounded_rect_mask(
    canvas_size: int,
    box: Rect,
    radius: int,
) -> PILImage:
    scale = MASK_SUPERSAMPLE_SCALE
    mask = Image.new("L", (canvas_size * scale, canvas_size * scale))
    draw = ImageDraw.Draw(mask)
    x, y, width, height = box
    left = x * scale
    top = y * scale
    right = left + max(1, width * scale) - 1
    bottom = top + max(1, height * scale) - 1
    draw.rounded_rectangle(
        (left, top, right, bottom),
        radius=max(0, radius * scale),
        fill=255,
    )
    return mask.resize((canvas_size, canvas_size), Resampling.LANCZOS)


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


def _build_final_crop_mask(
    crop: FinalCropSpec,
    canvas_size: int,
    ratio: float,
) -> PILImage:
    if crop.kind == "rounded_rect":
        return _build_antialiased_rounded_rect_mask(
            canvas_size,
            scale_box(crop.box, ratio),
            max(0, round(crop.radius * ratio)),
        )
    if crop.kind == "closed_frame":
        return clone_closed_frame_mask(crop.frame_path).resize(
            (canvas_size, canvas_size),
            Resampling.LANCZOS,
        )
    if crop.kind == "mask":
        return clone_mask(crop.mask_path).resize(
            (canvas_size, canvas_size),
            Resampling.LANCZOS,
        )
    raise ValueError(f"unknown final crop kind: {crop.kind}")


def _apply_final_crop(image: PILImage, mask: PILImage) -> None:
    image.putalpha(ImageChops.multiply(image.getchannel("A"), mask))


def render_card_by_spec(avatar: PILImage, spec: ThemeCardSpec) -> PILImage:
    canvas_size = int(spec.output_size)
    ratio = canvas_size / spec.base_canvas_size
    build_image = BuildImage(canvas_size, canvas_size, color=(0, 0, 0, 0))
    canvas = build_image.markImg

    avatar_x, avatar_y, avatar_width, avatar_height = scale_box(spec.avatar_box, ratio)
    avatar_region = fit_size(avatar.convert("RGBA"), (avatar_width, avatar_height))
    canvas.alpha_composite(avatar_region, (avatar_x, avatar_y))

    for overlay in spec.overlays:
        image = _resolve_overlay(overlay, ratio)
        for position in overlay.positions:
            canvas.alpha_composite(image, scale_point(position, ratio))

    if spec.final_crop is not None:
        mask = _build_final_crop_mask(spec.final_crop, canvas_size, ratio)
        _apply_final_crop(canvas, mask)

    return canvas
