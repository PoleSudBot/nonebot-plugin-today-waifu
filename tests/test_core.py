from __future__ import annotations

import asyncio
from collections import Counter
from dataclasses import dataclass
from datetime import date
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace

import nonebot
from nonebot_plugin_today_waifu import texts
from nonebot_plugin_today_waifu.bootstrap import inject_orm_database_url
import nonebot_plugin_today_waifu.commands as commands_module
from nonebot_plugin_today_waifu.config import plugin_config
from nonebot_plugin_today_waifu.constants import PairStatus, SelectMode
from nonebot_plugin_today_waifu.render import compose_theme_card, render_theme_card
import nonebot_plugin_today_waifu.render.card_renderer as card_renderer_module
import nonebot_plugin_today_waifu.render.runtime as runtime_module
from nonebot_plugin_today_waifu.services import app as app_module
from nonebot_plugin_today_waifu.services.app import (
    DisplayUser,
    ThemeRollResult,
    TodayWaifuService,
    build_report_summary,
    resolve_effective_theme_keys,
)
from nonebot_plugin_today_waifu.theme_kits import bangdream, pjsk
from nonebot_plugin_today_waifu.theme_kits.common import (
    OverlaySpec,
    RoundedRectClipSpec,
    ThemeCardSpec,
    clone_frame_window_mask,
    clone_overlay_longest_edge,
    clone_overlay_resized,
    clone_overlay_width,
    render_card_by_spec,
)
from nonebot_plugin_today_waifu.themes import (
    build_theme_context,
    build_theme_payload,
    parse_theme_selection,
)
from PIL import Image, ImageChops


@dataclass(slots=True)
class FakeCounter:
    user_id: str
    target_id: str
    count: int


@dataclass(slots=True)
class FakeGroupSettings:
    scene_id: str = "1000"
    allow_change: bool = True
    limit_times: int = 2
    select_mode: str = SelectMode.RANDOM.value
    active_days: int = 3
    pure_love_enabled: bool = False
    pure_love_pending_enable_date: date | None = None
    rbq_enabled: bool = False
    fate_report_enabled: bool = False
    milestone_notify_override: bool | None = None


@dataclass(slots=True)
class FakeGlobalSettings:
    enabled_theme_keys: list[str]
    milestone_notify_enabled: bool = False


class FakeGroupSettingsRepo:
    def __init__(self, settings: FakeGroupSettings):
        self.settings = settings
        self.updates: list[dict] = []

    async def get(self, scene_id: str) -> FakeGroupSettings:
        assert scene_id == self.settings.scene_id
        return self.settings

    async def update(self, scene_id: str, **fields) -> FakeGroupSettings:
        assert scene_id == self.settings.scene_id
        self.updates.append(fields)
        for key, value in fields.items():
            setattr(self.settings, key, value)
        return self.settings


class FakeGlobalSettingsRepo:
    def __init__(self):
        self.settings = FakeGlobalSettings(["bangdream", "pjsk"])

    async def get(self) -> FakeGlobalSettings:
        return self.settings


class FakeThemePreferenceRepo:
    async def get(
        self,
        scope: str,
        *,
        scene_id: str | None = None,
        user_id: str | None = None,
    ):
        return None


class FakeDailyStateRepo:
    def __init__(self):
        self.items: dict[tuple[date, str, str], SimpleNamespace] = {}

    async def get(self, day: date, scene_id: str, user_id: str):
        return self.items.get((day, scene_id, user_id))

    async def upsert(self, day: date, scene_id: str, user_id: str, **fields):
        key = (day, scene_id, user_id)
        item = self.items.get(key)
        if item is None:
            item = SimpleNamespace(
                date=day,
                scene_id=scene_id,
                user_id=user_id,
                **fields,
            )
            self.items[key] = item
            return item
        for key_name, value in fields.items():
            setattr(item, key_name, value)
        return item

    async def delete(self, day: date, scene_id: str, user_id: str) -> None:
        self.items.pop((day, scene_id, user_id), None)

    async def list_locked_user_ids(self, day: date, scene_id: str) -> set[str]:
        return {
            item.target_id
            for item in self.items.values()
            if item.date == day
            and item.scene_id == scene_id
            and item.status == PairStatus.PAIRED.value
            and item.target_id
        }


class FakePairCounterRepo:
    def __init__(self):
        self.adjustments: list[tuple[str, str, str, int]] = []

    async def adjust(
        self,
        scene_id: str,
        user_id: str,
        target_id: str,
        delta: int,
        moment,
    ) -> int:
        self.adjustments.append((scene_id, user_id, target_id, delta))
        return 1 if delta > 0 else 0


class FakeMemberActivityRepo:
    async def list_active(self, scene_id: str, active_days: int, moment) -> set[str]:
        return set()


def _make_fake_repos(settings: FakeGroupSettings) -> SimpleNamespace:
    return SimpleNamespace(
        group_settings=FakeGroupSettingsRepo(settings),
        global_settings=FakeGlobalSettingsRepo(),
        theme_preferences=FakeThemePreferenceRepo(),
        daily_states=FakeDailyStateRepo(),
        pair_counters=FakePairCounterRepo(),
        member_activity=FakeMemberActivityRepo(),
        session=None,
    )


def _patch_with_repos(monkeypatch, repos: SimpleNamespace) -> None:
    async def _fake_with_repos(callback):
        return await callback(repos)

    monkeypatch.setattr(app_module, "with_repos", _fake_with_repos)


def _make_session(
    scene_id: str = "1000",
    user_id: str = "1001",
    user_name: str = "Alice",
):
    return SimpleNamespace(
        scene=SimpleNamespace(id=scene_id),
        user=SimpleNamespace(id=user_id, name=user_name),
        member=None,
    )


def _make_bot(self_id: str = "9999"):
    return SimpleNamespace(self_id=self_id)


def _patch_user_resolution(monkeypatch, service: TodayWaifuService) -> None:
    async def _fake_resolve_display_user(bot, scene_id: str, user_id: str, members):
        return DisplayUser(
            user_id=user_id,
            name=f"User {user_id}",
            avatar_url=None,
            role_tag=None,
            is_bot=user_id == bot.self_id,
        )

    async def _fake_roll_theme(*args, **kwargs):
        return ThemeRollResult(None, None)

    monkeypatch.setattr(service, "_resolve_display_user", _fake_resolve_display_user)
    monkeypatch.setattr(service, "_roll_theme_for_scope", _fake_roll_theme)


def _make_avatar_bytes(color: tuple[int, int, int] = (240, 32, 32)) -> bytes:
    image = Image.new("RGB", (256, 192), color)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _reset_theme_card_runtime() -> None:
    asyncio.run(runtime_module.close_theme_card_client())


def _assert_distribution_close(
    counts: Counter[str | int],
    expected: dict[str | int, float],
    total: int,
    tolerance: float,
) -> None:
    for key, expected_ratio in expected.items():
        observed_ratio = counts[key] / total
        assert abs(observed_ratio - expected_ratio) <= tolerance


def test_finish_message_uses_reply_to_for_plain_text(monkeypatch):
    from nonebot_plugin_alconna import UniMessage

    captured: dict[str, object] = {}

    async def _fake_finish(self, *args, **kwargs):
        captured["message"] = self
        captured["reply_to"] = kwargs.get("reply_to")

    monkeypatch.setattr(UniMessage, "finish", _fake_finish)

    class _Matcher:
        async def finish(self, message):
            raise AssertionError(f"unexpected matcher.finish call: {message}")

    asyncio.run(commands_module._finish_message(_Matcher(), "测试消息"))

    assert isinstance(captured["message"], UniMessage)
    assert captured["reply_to"] is True


def test_finish_message_uses_reply_to_for_unimessage(monkeypatch):
    from nonebot_plugin_alconna import UniMessage

    captured: dict[str, object] = {}

    async def _fake_finish(self, *args, **kwargs):
        captured["message"] = self
        captured["reply_to"] = kwargs.get("reply_to")

    monkeypatch.setattr(UniMessage, "finish", _fake_finish)

    class _Matcher:
        async def finish(self, message):
            raise AssertionError(f"unexpected matcher.finish call: {message}")

    message = UniMessage.text("测试消息")
    asyncio.run(commands_module._finish_message(_Matcher(), message))

    assert captured["message"] is message
    assert captured["reply_to"] is True


def test_inject_orm_database_url_from_db_url(monkeypatch):
    config = nonebot.get_driver().config
    monkeypatch.setattr(config, "sqlalchemy_database_url", "", raising=False)
    monkeypatch.setattr(config, "db_url", "postgresql+asyncpg://tester:pass@localhost/db", raising=False)

    inject_orm_database_url()

    assert config.sqlalchemy_database_url == "postgresql+asyncpg://tester:pass@localhost/db"


def test_inject_orm_database_url_prefers_existing(monkeypatch):
    config = nonebot.get_driver().config
    monkeypatch.setattr(config, "sqlalchemy_database_url", "sqlite+aiosqlite://", raising=False)
    monkeypatch.setattr(config, "db_url", "postgresql+asyncpg://tester:pass@localhost/db", raising=False)

    inject_orm_database_url()

    assert config.sqlalchemy_database_url == "sqlite+aiosqlite://"


def test_theme_selection_and_local_assets():
    assert parse_theme_selection("all") == ["bangdream", "pjsk"]
    assert parse_theme_selection("none") == []
    assert parse_theme_selection("2,1,2") == ["pjsk", "bangdream"]

    bangdream = build_theme_context(
        "bangdream",
        {
            "attribute": "cool",
            "band": "ppp",
            "star_count": 4,
            "star_type": "color",
        },
    )
    pjsk = build_theme_context(
        "pjsk",
        {
            "attribute": "cute",
            "rarity": "4",
            "training_state": "after_training",
            "star_count": 4,
        },
    )

    assert isinstance(bangdream["border_path"], Path)
    assert bangdream["border_path"].exists()
    assert bangdream["star_path"].exists()
    assert "assets/bangdream" in str(bangdream["border_path"])
    assert bangdream["render_spec"].output_size == 1024
    assert bangdream["render_spec"].clip.kind == "frame_window"
    assert bangdream["render_spec"].post_clip is None
    assert isinstance(pjsk["frame_path"], Path)
    assert pjsk["frame_path"].exists()
    assert "assets/pjsk" in str(pjsk["frame_path"])
    assert "assets-direct.unipjsk.com" not in str(pjsk["frame_path"])
    assert pjsk["render_spec"].output_size == 1024
    assert pjsk["render_spec"].clip is None
    assert pjsk["render_spec"].post_clip is not None
    assert pjsk["render_spec"].post_clip.kind == "rounded_rect"
    assert pjsk["render_spec"].post_clip.box == (0, 0, 156, 156)
    assert pjsk["render_spec"].post_clip.radius == 8


def test_bangdream_card_composition():
    avatar_bytes = _make_avatar_bytes()
    bangdream = build_theme_context(
        "bangdream",
        {
            "attribute": "cool",
            "band": "ppp",
            "star_count": 4,
            "star_type": "color",
        },
    )

    output = compose_theme_card(avatar_bytes, "bangdream", bangdream)

    assert output.startswith(b"\x89PNG")
    with Image.open(BytesIO(output)) as image:
        assert image.size == (1024, 1024)
        colors = image.getcolors(maxcolors=200000)
        assert colors is not None
        assert len(colors) > 1
        for point in ((0, 0), (1023, 0), (0, 1023), (1023, 1023)):
            assert image.getpixel(point) != (240, 32, 32, 255)
        assert image.getpixel((512, 512)) == (240, 32, 32, 255)
        assert image.getpixel((884, 140)) != (240, 32, 32, 255)
        assert image.getpixel((112, 930)) != (240, 32, 32, 255)


def test_pjsk_card_composition():
    avatar_bytes = _make_avatar_bytes((32, 160, 240))
    pjsk = build_theme_context(
        "pjsk",
        {
            "attribute": "cute",
            "rarity": "4",
            "training_state": "after_training",
            "star_count": 4,
        },
    )

    output = compose_theme_card(avatar_bytes, "pjsk", pjsk)

    assert output.startswith(b"\x89PNG")
    with Image.open(BytesIO(output)) as image:
        assert image.size == (1024, 1024)
        colors = image.getcolors(maxcolors=200000)
        assert colors is not None
        assert len(colors) > 1
        for point in ((0, 0), (1023, 0), (0, 1023), (1023, 1023)):
            assert image.getpixel(point)[3] == 0
        for point in ((16, 16), (1007, 16), (16, 1007), (1007, 1007)):
            assert image.getpixel(point)[3] > 0
        assert image.getpixel((512, 512)) == (32, 160, 240, 255)
        assert image.getpixel((512, 40))[3] >= 180
        assert image.getpixel((512, 60))[3] >= 180
        assert image.getpixel((120, 120)) != (32, 160, 240, 255)
        assert image.getpixel((111, 900)) != (32, 160, 240, 255)


def test_theme_card_client_reuses_single_instance(monkeypatch):
    class FakeClient:
        def __init__(self):
            self.closed = False

        async def aclose(self):
            self.closed = True

    created: list[FakeClient] = []

    def _fake_create_theme_card_client() -> FakeClient:
        client = FakeClient()
        created.append(client)
        return client

    _reset_theme_card_runtime()
    monkeypatch.setattr(
        runtime_module,
        "_create_theme_card_client",
        _fake_create_theme_card_client,
    )

    client1 = runtime_module._get_theme_card_client()
    client2 = runtime_module._get_theme_card_client()

    assert client1 is client2
    assert len(created) == 1

    _reset_theme_card_runtime()
    assert created[0].closed is True


def test_get_avatar_bytes_uses_ttl_cache(monkeypatch):
    _reset_theme_card_runtime()
    monkeypatch.setattr(
        plugin_config,
        "today_waifu_theme_avatar_cache_ttl_seconds",
        300,
    )
    call_count = 0

    async def _fake_fetch_avatar_bytes(url: str) -> bytes:
        nonlocal call_count
        call_count += 1
        return f"avatar:{url}".encode()

    monkeypatch.setattr(runtime_module, "_fetch_avatar_bytes", _fake_fetch_avatar_bytes)

    async def _run() -> tuple[bytes, bytes]:
        first = await runtime_module.get_avatar_bytes("https://example.com/avatar.png")
        second = await runtime_module.get_avatar_bytes("https://example.com/avatar.png")
        return first, second

    first, second = asyncio.run(_run())

    assert first == second == b"avatar:https://example.com/avatar.png"
    assert call_count == 1
    _reset_theme_card_runtime()


def test_get_avatar_bytes_deduplicates_inflight_requests(monkeypatch):
    _reset_theme_card_runtime()
    monkeypatch.setattr(
        plugin_config,
        "today_waifu_theme_avatar_cache_ttl_seconds",
        300,
    )
    call_count = 0
    started = asyncio.Event()
    release = asyncio.Event()

    async def _fake_fetch_avatar_bytes(url: str) -> bytes:
        nonlocal call_count
        call_count += 1
        started.set()
        await release.wait()
        return f"inflight:{url}".encode()

    monkeypatch.setattr(runtime_module, "_fetch_avatar_bytes", _fake_fetch_avatar_bytes)

    async def _run() -> tuple[bytes, bytes]:
        first_task = asyncio.create_task(
            runtime_module.get_avatar_bytes("https://example.com/avatar.png")
        )
        await started.wait()
        second_task = asyncio.create_task(
            runtime_module.get_avatar_bytes("https://example.com/avatar.png")
        )
        release.set()
        return await asyncio.gather(first_task, second_task)

    first, second = asyncio.run(_run())

    assert first == second == b"inflight:https://example.com/avatar.png"
    assert call_count == 1
    _reset_theme_card_runtime()


def test_render_theme_card_async_path_returns_png(monkeypatch):
    avatar_bytes = _make_avatar_bytes()
    theme_data = build_theme_context(
        "bangdream",
        {
            "attribute": "cool",
            "band": "ppp",
            "star_count": 4,
            "star_type": "color",
        },
    )

    async def _fake_get_avatar_bytes(url: str) -> bytes:
        return avatar_bytes

    monkeypatch.setattr(card_renderer_module, "get_avatar_bytes", _fake_get_avatar_bytes)

    output = asyncio.run(
        render_theme_card("https://example.com/avatar.png", "bangdream", theme_data)
    )

    assert output.startswith(b"\x89PNG")
    with Image.open(BytesIO(output)) as image:
        assert image.size == (1024, 1024)


def test_scaled_overlay_helpers_return_independent_copies():
    asset_path = (
        Path(__file__).resolve().parents[1]
        / "nonebot_plugin_today_waifu"
        / "assets"
        / "bangdream"
        / "cool.png"
    )

    resized = clone_overlay_resized(asset_path, (64, 64))
    cached_copy = clone_overlay_resized(asset_path, (64, 64))
    original_pixel = cached_copy.getpixel((0, 0))
    mutated_pixel = (
        (original_pixel[0] + 1) % 256,
        original_pixel[1],
        original_pixel[2],
        original_pixel[3],
    )

    resized.putpixel((0, 0), mutated_pixel)
    fresh_copy = clone_overlay_resized(asset_path, (64, 64))
    longest = clone_overlay_longest_edge(asset_path, 48)
    width_fixed = clone_overlay_width(asset_path, 32)

    assert cached_copy.getpixel((0, 0)) == original_pixel
    assert fresh_copy.getpixel((0, 0)) == original_pixel
    assert max(longest.size) == 48
    assert width_fixed.width == 32


def test_bangdream_frame_window_masks_are_stable():
    asset_dir = (
        Path(__file__).resolve().parents[1]
        / "nonebot_plugin_today_waifu"
        / "assets"
        / "bangdream"
    )
    expected_pixels = {
        "card-3.png": 25016,
        "card-4.png": 25016,
        "card-5.png": 24970,
    }

    for name, pixel_count in expected_pixels.items():
        mask = clone_frame_window_mask(asset_dir / name)
        assert mask.size == (180, 180)
        assert mask.getbbox() == (8, 8, 172, 172)
        assert mask.getpixel((0, 0)) == 0
        assert mask.getpixel((90, 90)) == 255
        assert sum(1 for value in mask.getdata() if value) == pixel_count


def test_post_clip_applies_after_overlays(tmp_path: Path):
    overlay_path = tmp_path / "overlay.png"
    overlay = Image.new("RGBA", (100, 100), (48, 96, 240, 255))
    overlay.save(overlay_path)

    avatar = Image.new("RGBA", (100, 100), (240, 48, 48, 255))
    image = render_card_by_spec(
        avatar,
        ThemeCardSpec(
            base_canvas_size=100,
            avatar_box=(0, 0, 100, 100),
            output_size=100,
            overlays=(OverlaySpec(path=overlay_path, size=(100, 100)),),
            post_clip=RoundedRectClipSpec(box=(10, 10, 80, 80), radius=12),
        ),
    )

    assert image.getpixel((50, 50)) == (48, 96, 240, 255)
    assert image.getpixel((5, 5))[3] == 0
    assert image.getpixel((95, 5))[3] == 0
    assert image.getpixel((5, 95))[3] == 0
    assert image.getpixel((95, 95))[3] == 0


def test_post_clip_rounded_rect_mask_is_antialiased():
    avatar = Image.new("RGBA", (100, 100), (240, 48, 48, 255))
    image = render_card_by_spec(
        avatar,
        ThemeCardSpec(
            base_canvas_size=100,
            avatar_box=(0, 0, 100, 100),
            output_size=100,
            post_clip=RoundedRectClipSpec(box=(10, 10, 80, 80), radius=12),
        ),
    )

    sampled_alphas = {
        image.getpixel((x, y))[3]
        for x in range(0, 25)
        for y in range(0, 25)
    }

    assert any(0 < alpha < 255 for alpha in sampled_alphas)


def test_bangdream_payload_branches(monkeypatch):
    monkeypatch.setattr(bangdream.random, "choice", lambda seq: seq[0])

    cases = [
        (3, "normal", "card-3.png", "normal_star.png"),
        (4, "color", "card-4.png", "color_star.png"),
        (5, "normal", "card-5.png", "normal_star.png"),
    ]
    for star_count, star_type, border_name, star_name in cases:
        picks = iter([star_count, star_type])
        monkeypatch.setattr(bangdream, "choose_by_weight", lambda options: next(picks))

        payload = build_theme_payload("bangdream")
        context = build_theme_context("bangdream", payload)

        assert payload == {
            "attribute": "cool",
            "band": "ppp",
            "star_count": star_count,
            "star_type": star_type,
        }
        assert context["border_path"].name == border_name
        assert context["attr_path"].name == "cool.png"
        assert context["band_path"].name == "ppp.png"
        assert context["star_path"].name == star_name
        assert context["star_count"] == star_count


def test_pjsk_payload_branches(monkeypatch):
    monkeypatch.setattr(pjsk.random, "choice", lambda seq: seq[1])

    cases = [
        ("3", "normal", 3, "frame_rarity_3.png", "rare_star_normal.png", 3),
        ("4", "after_training", 4, "frame_rarity_4.png", "rarity-star-after-training.png", 4),
        ("birthday", "after_training", 4, "frame_rarity_birthday.png", "rare_birthday.png", 1),
    ]
    for rarity, training_state, star_count, frame_name, star_name, star_render_count in cases:
        picks = iter([rarity, training_state])
        monkeypatch.setattr(pjsk, "choose_by_weight", lambda options: next(picks))

        payload = build_theme_payload("pjsk")
        context = build_theme_context("pjsk", payload)

        assert payload == {
            "attribute": "cute",
            "rarity": rarity,
            "training_state": training_state,
            "star_count": star_count,
        }
        assert context["frame_path"].name == frame_name
        assert context["attr_path"].name == "attr_cute.png"
        assert context["star_path"].name == star_name
        assert context["star_count"] == star_count
        assert context["star_render_count"] == star_render_count


def test_pjsk_post_clip_rounds_card_corners():
    avatar_bytes = _make_avatar_bytes((32, 160, 240))
    theme_data = build_theme_context(
        "pjsk",
        {
            "attribute": "cute",
            "rarity": "4",
            "training_state": "after_training",
            "star_count": 4,
        },
    )

    output = compose_theme_card(avatar_bytes, "pjsk", theme_data)

    with Image.open(BytesIO(output)) as image:
        for point in ((0, 0), (1023, 0), (0, 1023), (1023, 1023)):
            assert image.getpixel(point)[3] == 0
        for point in ((16, 16), (1007, 16), (16, 1007), (1007, 1007)):
            assert image.getpixel(point)[3] > 0
        assert image.getpixel((image.width // 2, 40))[3] >= 180
        assert image.getpixel((image.width // 2, 60))[3] >= 180
        assert image.getpixel((20, image.height // 2)) == (32, 160, 240, 255)

        thumbnail = image.resize((156, 156), Image.Resampling.LANCZOS)
        thumbnail_on_white = Image.new("RGBA", thumbnail.size, (255, 255, 255, 255))
        thumbnail_on_white.alpha_composite(thumbnail)
        for point in ((2, 2), (153, 2), (2, 153), (153, 153)):
            assert thumbnail.getpixel(point)[3] > 0
            assert thumbnail_on_white.getpixel(point) != (255, 255, 255, 255)


def test_pjsk_birthday_post_clip_preserves_badge_and_attr():
    avatar_bytes = _make_avatar_bytes((32, 160, 240))
    theme_data = build_theme_context(
        "pjsk",
        {
            "attribute": "happy",
            "rarity": "birthday",
            "training_state": "normal",
            "star_count": 4,
        },
    )

    output = compose_theme_card(avatar_bytes, "pjsk", theme_data)

    with Image.open(BytesIO(output)) as image:
        for point in ((0, 0), (1023, 0), (0, 1023), (1023, 1023)):
            assert image.getpixel(point)[3] == 0
        for point in ((16, 16), (1007, 16), (16, 1007), (1007, 1007)):
            assert image.getpixel(point)[3] > 0
        assert image.getpixel((120, 120)) != (32, 160, 240, 255)
        assert image.getpixel((145, 900)) != (32, 160, 240, 255)
        assert image.getpixel((512, 40))[3] >= 180


def test_theme_rarity_distribution_regression():
    sample_count = 20000

    bangdream.random.seed(20260401)
    bangdream_counts: Counter[int] = Counter(
        build_theme_payload("bangdream")["star_count"]
        for _ in range(sample_count)
    )
    _assert_distribution_close(
        bangdream_counts,
        {3: 0.3, 4: 0.4, 5: 0.3},
        sample_count,
        tolerance=0.025,
    )

    pjsk.random.seed(20260401)
    pjsk_counts: Counter[str] = Counter(
        build_theme_payload("pjsk")["rarity"]
        for _ in range(sample_count)
    )
    _assert_distribution_close(
        pjsk_counts,
        {"3": 0.6, "4": 0.3, "birthday": 0.1},
        sample_count,
        tolerance=0.025,
    )


def test_pjsk_birthday_card_renders_single_badge():
    avatar = Image.open(BytesIO(_make_avatar_bytes((32, 160, 240)))).convert("RGBA")
    theme_data = build_theme_context(
        "pjsk",
        {
            "attribute": "cute",
            "rarity": "birthday",
            "training_state": "after_training",
            "star_count": 4,
        },
    )

    with_badge = pjsk.render_card(avatar, theme_data)
    without_badge = pjsk.render_card(avatar, {**theme_data, "star_render_count": 0})

    scale = int(theme_data["output_size"]) / pjsk.BASE_CANVAS_SIZE
    badge_size = round(pjsk.STAR_SIZE * scale)
    inset = max(8, badge_size // 6)

    for index, (x, y) in enumerate(pjsk.STAR_POSITIONS):
        left = round(x * scale)
        top = round(y * scale)
        box = (
            left + inset,
            top + inset,
            left + badge_size - inset,
            top + badge_size - inset,
        )
        diff = ImageChops.difference(with_badge.crop(box), without_badge.crop(box))
        if index == 0:
            assert diff.getbbox() is not None
        else:
            assert diff.getbbox() is None


def test_resolve_effective_theme_keys():
    assert resolve_effective_theme_keys(["pjsk"], ["bangdream"], ["bangdream", "pjsk"]) == ["pjsk"]
    assert resolve_effective_theme_keys(None, [], ["bangdream", "pjsk"]) == []
    assert resolve_effective_theme_keys(None, None, ["bangdream", "pjsk"]) == ["bangdream", "pjsk"]


def test_build_report_summary():
    rows = [
        FakeCounter("1001", "1002", 3),
        FakeCounter("1003", "1002", 5),
        FakeCounter("1001", "1003", 4),
        FakeCounter("1003", "1001", 2),
    ]

    summary = build_report_summary(rows)

    assert summary.sea_king == ("1002", 8)
    assert summary.best_match == ("1001", "1003", 6)
    assert summary.yandere == ("1003", "1002", 5)


def test_usage_and_command_cleanup():
    command_source = (
        Path(__file__).resolve().parents[1] / "nonebot_plugin_today_waifu" / "commands.py"
    ).read_text(encoding="utf-8")

    assert "今日老婆帮助" not in texts.HELP_TEXT
    assert "今日RBQ" not in texts.HELP_TEXT
    assert "今日老婆信息" not in texts.HELP_TEXT
    assert "老婆设置" in texts.HELP_TEXT

    assert "今日老婆帮助" not in command_source
    assert "今日RBQ状态" not in command_source
    assert "开启今日RBQ" not in command_source
    assert "关闭今日RBQ" not in command_source
    assert "今日老婆信息" not in command_source
    assert "老婆设置" in command_source
    assert "开启次日生效，关闭立即生效" in texts.HELP_TEXT


def test_set_pure_love_enable_schedules_for_next_day(monkeypatch):
    service = TodayWaifuService()
    settings = FakeGroupSettings()
    repos = _make_fake_repos(settings)
    _patch_with_repos(monkeypatch, repos)
    monkeypatch.setattr(service, "_today", lambda: date(2026, 4, 1))

    message = asyncio.run(service.set_pure_love("1000", True))

    assert message == "本群纯爱模式将于 2026-04-02 开启，今天仍按当前模式运行。"
    assert settings.pure_love_enabled is False
    assert settings.pure_love_pending_enable_date == date(2026, 4, 2)


def test_get_settings_text_shows_pending_pure_love_date(monkeypatch):
    service = TodayWaifuService()
    settings = FakeGroupSettings(pure_love_pending_enable_date=date(2026, 4, 2))
    repos = _make_fake_repos(settings)
    _patch_with_repos(monkeypatch, repos)
    monkeypatch.setattr(service, "_today", lambda: date(2026, 4, 1))

    text = asyncio.run(service.get_settings_text(_make_session()))

    assert "纯爱模式：关闭（将于 2026-04-02 开启）" in text


def test_pending_pure_love_does_not_affect_same_day_pick_or_change(monkeypatch):
    service = TodayWaifuService()
    settings = FakeGroupSettings(pure_love_pending_enable_date=date(2026, 4, 2))
    repos = _make_fake_repos(settings)
    _patch_with_repos(monkeypatch, repos)
    monkeypatch.setattr(service, "_today", lambda: date(2026, 4, 1))
    _patch_user_resolution(monkeypatch, service)
    block_text = "纯爱模式阻止换老婆"
    monkeypatch.setattr(app_module, "pure_love_block_change_text", lambda: block_text)

    picks = iter(["2002", "2003"])

    async def _fake_select_candidate(*args, **kwargs):
        return next(picks)

    monkeypatch.setattr(service, "_select_candidate", _fake_select_candidate)
    session = _make_session()
    bot = _make_bot()

    first_pick = asyncio.run(service._resolve_today_waifu(bot, session, {}))
    changed_pick = asyncio.run(service._change_waifu(bot, session, {}))

    assert first_pick.target is not None
    assert first_pick.target.user_id == "2002"
    assert changed_pick.target is not None
    assert changed_pick.target.user_id == "2003"
    assert changed_pick.text != block_text
    assert (date(2026, 4, 1), "1000", "2002") not in repos.daily_states.items


def test_pending_pure_love_activates_next_day_and_blocks_change(monkeypatch):
    service = TodayWaifuService()
    today = date(2026, 4, 2)
    settings = FakeGroupSettings(pure_love_pending_enable_date=today)
    repos = _make_fake_repos(settings)
    repos.daily_states.items[(today, "1000", "1001")] = SimpleNamespace(
        date=today,
        scene_id="1000",
        user_id="1001",
        status=PairStatus.PAIRED.value,
        target_id="2002",
        change_used=0,
        lock_source_user_id=None,
        lock_mirrored=False,
        theme_key=None,
        theme_payload=None,
        counted=True,
    )
    _patch_with_repos(monkeypatch, repos)
    monkeypatch.setattr(service, "_today", lambda: today)
    block_text = "纯爱模式阻止换老婆"
    monkeypatch.setattr(app_module, "pure_love_block_change_text", lambda: block_text)

    settings_text = asyncio.run(service.get_settings_text(_make_session()))
    blocked_pick = asyncio.run(service._change_waifu(_make_bot(), _make_session(), {}))

    assert "纯爱模式：开启" in settings_text
    assert settings.pure_love_enabled is True
    assert settings.pure_love_pending_enable_date is None
    assert blocked_pick.text == block_text


def test_set_pure_love_off_clears_pending_or_active(monkeypatch):
    service = TodayWaifuService()
    monkeypatch.setattr(service, "_today", lambda: date(2026, 4, 1))

    pending_settings = FakeGroupSettings(pure_love_pending_enable_date=date(2026, 4, 2))
    pending_repos = _make_fake_repos(pending_settings)
    _patch_with_repos(monkeypatch, pending_repos)
    pending_message = asyncio.run(service.set_pure_love("1000", False))

    assert pending_message == "已取消本群纯爱模式于 2026-04-02 的开启计划。"
    assert pending_settings.pure_love_enabled is False
    assert pending_settings.pure_love_pending_enable_date is None

    active_settings = FakeGroupSettings(pure_love_enabled=True)
    active_repos = _make_fake_repos(active_settings)
    _patch_with_repos(monkeypatch, active_repos)
    active_message = asyncio.run(service.set_pure_love("1000", False))

    assert active_message == "本群纯爱模式已关闭。"
    assert active_settings.pure_love_enabled is False
    assert active_settings.pure_love_pending_enable_date is None
