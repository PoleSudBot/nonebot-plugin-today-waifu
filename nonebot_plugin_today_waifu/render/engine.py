from __future__ import annotations

from pathlib import Path
from typing import Any

import jinja2

from ..config import TEMPLATE_DIR

jinja_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(TEMPLATE_DIR),
    autoescape=jinja2.select_autoescape(["html", "xml"]),
    enable_async=True,
)


async def render_template_image(
    template_name: str,
    context: dict[str, Any],
    *,
    selector: str = "main",
    width: int = 800,
    height: int = 600,
    image_type: str = "png",
) -> bytes:
    from nonebot_plugin_htmlrender import get_new_page

    html = await jinja_env.get_template(template_name).render_async(**context)
    async with get_new_page() as page:
        await page.set_viewport_size({"width": width, "height": height})
        await page.set_content(html, wait_until="networkidle")
        element = await page.query_selector(selector)
        assert element is not None
        return await element.screenshot(type=image_type)
