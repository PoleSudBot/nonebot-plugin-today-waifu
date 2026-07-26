from __future__ import annotations

from io import BytesIO

from PIL import Image, ImageDraw, ImageFilter, ImageOps
from PIL.Image import Image as PILImage
from PIL.ImageFont import FreeTypeFont

from zhenxun.configs.path_config import FONT_PATH
from zhenxun.utils._build_image import BuildImage

from .avatar import AvatarSource, load_avatar_image

PRIMARY = "#FF6699"
PRIMARY_DARK = "#D14775"
PRIMARY_SOFT = "#FFF5F8"
PAGE_BACKGROUND = "#FFF0F5"
SURFACE = "#FFFFFF"
BORDER = "#FFE0EA"
TEXT_DARK = "#4A2C36"
TEXT_MUTED = "#9B7582"

FONT_DIR = FONT_PATH / "HarmonyOS_Sans_SC"
FONT_FILES = {
    "regular": FONT_DIR / "HarmonyOS_SansSC_Regular.ttf",
    "medium": FONT_DIR / "HarmonyOS_SansSC_Medium.ttf",
    "bold": FONT_DIR / "HarmonyOS_SansSC_Bold.ttf",
}


def font(size: int, weight: str = "regular") -> FreeTypeFont:
    return BuildImage.load_font(FONT_FILES[weight], size)


def create_canvas(width: int, height: int, color: str = PAGE_BACKGROUND) -> PILImage:
    return BuildImage(width, height, color=color).markImg.convert("RGBA")


def image_to_png(image: PILImage) -> bytes:
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def draw_panel(
    canvas: PILImage,
    box: tuple[int, int, int, int],
    *,
    fill: str = SURFACE,
    outline: str = BORDER,
    radius: int = 24,
    shadow: bool = True,
) -> None:
    if shadow:
        shadow_layer = Image.new("RGBA", canvas.size)
        shadow_draw = ImageDraw.Draw(shadow_layer)
        x1, y1, x2, y2 = box
        shadow_draw.rounded_rectangle(
            (x1, y1 + 6, x2, y2 + 6),
            radius=radius,
            fill=(209, 71, 117, 24),
        )
        canvas.alpha_composite(shadow_layer.filter(ImageFilter.GaussianBlur(10)))
    ImageDraw.Draw(canvas).rounded_rectangle(
        box,
        radius=radius,
        fill=fill,
        outline=outline,
        width=2,
    )


def text_width(draw: ImageDraw.ImageDraw, text: str, text_font: FreeTypeFont) -> int:
    box = draw.textbbox((0, 0), text or " ", font=text_font)
    return box[2] - box[0]


def ellipsize_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    text_font: FreeTypeFont,
    max_width: int,
) -> str:
    value = str(text)
    if text_width(draw, value, text_font) <= max_width:
        return value
    suffix = "…"
    while value and text_width(draw, value + suffix, text_font) > max_width:
        value = value[:-1]
    return value + suffix if value else suffix


def wrap_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    text_font: FreeTypeFont,
    max_width: int,
    *,
    max_lines: int,
) -> list[str]:
    lines: list[str] = []
    current = ""
    for character in str(text):
        candidate = current + character
        if current and text_width(draw, candidate, text_font) > max_width:
            lines.append(current)
            current = character
            if len(lines) == max_lines:
                lines[-1] = ellipsize_text(draw, lines[-1], text_font, max_width)
                return lines
        else:
            current = candidate
    if current and len(lines) < max_lines:
        lines.append(current)
    return lines or [""]


def draw_centered_text(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    text: str,
    *,
    text_font: FreeTypeFont,
    fill: str,
) -> None:
    left, top, right, bottom = box
    bounds = draw.textbbox((0, 0), text or " ", font=text_font)
    width = bounds[2] - bounds[0]
    height = bounds[3] - bounds[1]
    draw.text(
        ((left + right - width) // 2, (top + bottom - height) // 2 - bounds[1]),
        text,
        font=text_font,
        fill=fill,
    )


def paste_circle_avatar(
    canvas: PILImage,
    source: AvatarSource | None,
    box: tuple[int, int, int, int],
    *,
    name: str,
) -> None:
    left, top, right, bottom = box
    size = min(right - left, bottom - top)
    mask = Image.new("L", (size * 4, size * 4))
    ImageDraw.Draw(mask).ellipse((0, 0, size * 4 - 1, size * 4 - 1), fill=255)
    mask = mask.resize((size, size), Image.Resampling.LANCZOS)

    if source is not None:
        avatar = ImageOps.fit(
            load_avatar_image(source),
            (size, size),
            method=Image.Resampling.LANCZOS,
        )
    else:
        avatar = Image.new("RGBA", (size, size), PRIMARY_SOFT)
        draw = ImageDraw.Draw(avatar)
        initial = str(name).strip()[:1] or "?"
        draw_centered_text(
            draw,
            (0, 0, size, size),
            initial,
            text_font=font(max(20, size // 2), "medium"),
            fill=PRIMARY_DARK,
        )

    outline_size = size + 6
    outline = Image.new("RGBA", (outline_size, outline_size))
    ImageDraw.Draw(outline).ellipse(
        (0, 0, outline_size - 1, outline_size - 1),
        fill=SURFACE,
    )
    canvas.alpha_composite(outline, (left - 3, top - 3))
    canvas.paste(avatar, (left, top), mask)
