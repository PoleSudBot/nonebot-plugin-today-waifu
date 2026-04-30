from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta
import random
from typing import Any

import httpx
import nonebot
from nonebot import logger
from nonebot.adapters import Bot
from nonebot_plugin_alconna import UniMessage
from nonebot_plugin_alconna.uniseg import Target
from nonebot_plugin_uninfo import Interface, SceneType, Uninfo, get_interface

from ..config import plugin_config
from ..constants import (
    DEFAULT_GLOBAL_THEMES,
    MODE_DISPLAY_NAMES,
    NO_WAIFU_TEXT,
    REPORT_EMPTY_TEXT,
    PairStatus,
    PeriodWindow,
    ReportBucket,
    SelectMode,
    ThemeScope,
    get_period_window,
)
from ..member_cache import CachedMember, member_cache
from ..models import DailyWaifuState, GroupSettings, PairCounter
from ..render import render_template_image, render_theme_card
from ..repositories import RepoBundle, with_repos
from ..texts import (
    change_disabled_text,
    change_success_text,
    divorce_text,
    first_pick_text,
    milestone_text,
    mirror_first_pick_text,
    mutual_love_text,
    need_pick_first_text,
    no_waifu_text,
    pure_love_block_change_text,
    repeat_pick_text,
)
from ..themes import (
    build_theme_context,
    build_theme_payload,
    format_theme_keys,
    list_theme_lines,
    parse_theme_selection,
)

CP_ROSTER_COLUMNS = 4


@dataclass(slots=True)
class DisplayUser:
    user_id: str
    name: str
    avatar_url: str | None
    role_tag: str | None
    is_bot: bool = False


@dataclass(slots=True)
class ThemeRollResult:
    theme_key: str | None
    theme_payload: dict[str, Any] | None


@dataclass(slots=True)
class RelationMessage:
    text: str
    target: DisplayUser | None
    theme_key: str | None = None
    theme_payload: dict[str, Any] | None = None
    extra_lines: list[str] | None = None


@dataclass(slots=True)
class ReportSummary:
    sea_king: tuple[str, int] | None
    best_match: tuple[str, str, int] | None
    yandere: tuple[str, str, int] | None


def resolve_effective_theme_keys(
    user_keys: list[str] | None,
    group_keys: list[str] | None,
    global_keys: list[str],
) -> list[str]:
    if user_keys is not None:
        return list(user_keys)
    if group_keys is not None:
        return list(group_keys)
    return list(global_keys)


def build_report_summary(rows: Sequence[PairCounter]) -> ReportSummary:
    if not rows:
        return ReportSummary(None, None, None)

    inbound_counter: Counter[str] = Counter()
    directional: dict[tuple[str, str], int] = {}
    for row in rows:
        inbound_counter[row.target_id] += row.count
        directional[(row.user_id, row.target_id)] = row.count

    sea_king = None
    if inbound_counter:
        target_id, count = max(inbound_counter.items(), key=lambda item: (item[1], item[0]))
        sea_king = (target_id, count)

    best_match = None
    seen_pairs: set[frozenset[str]] = set()
    for (user_id, target_id), count in directional.items():
        pair_key = frozenset({user_id, target_id})
        if len(pair_key) < 2 or pair_key in seen_pairs:
            continue
        reverse = directional.get((target_id, user_id))
        if not reverse:
            continue
        seen_pairs.add(pair_key)
        total = count + reverse
        left_id, right_id = sorted((user_id, target_id))
        current = (left_id, right_id, total)
        if best_match is None or (total, user_id, target_id) > (
            best_match[2],
            best_match[0],
            best_match[1],
        ):
            best_match = current

    yandere = None
    for row in rows:
        current = (row.user_id, row.target_id, row.count)
        if yandere is None or (row.count, row.user_id, row.target_id) > (
            yandere[2],
            yandere[0],
            yandere[1],
        ):
            yandere = current

    return ReportSummary(sea_king, best_match, yandere)


class TodayWaifuService:
    def __init__(self):
        self._ban_ids = set(plugin_config.today_waifu_ban_id_list)

    def _today(self) -> date:
        return date.today()

    def _tomorrow(self) -> date:
        return self._today() + timedelta(days=1)

    def _now(self) -> datetime:
        return datetime.now()

    def _superusers(self) -> set[str]:
        return {str(user_id) for user_id in nonebot.get_driver().config.superusers}

    def is_superuser(self, session: Uninfo) -> bool:
        return bool(session.user and session.user.id in self._superusers())

    def is_group_admin(self, session: Uninfo) -> bool:
        if self.is_superuser(session):
            return True
        if not session.member or not session.member.role:
            return False
        role_id = str(session.member.role.id).upper()
        return role_id in {"OWNER", "ADMINISTRATOR"}

    async def track_message_activity(self, session: Uninfo) -> None:
        if not session.scene or session.scene.is_private or not session.user:
            return
        member_cache.upsert_from_session(session)
        moment = self._now()

        async def _run(repos: RepoBundle):
            await repos.member_activity.touch(session.scene.id, session.user.id, moment)

        await with_repos(_run)

    async def handle_member_join(self, bot: Bot, scene_id: str, user_id: str) -> None:
        if not (interface := get_interface(bot)):
            return
        try:
            member = await interface.get_member(SceneType.GROUP, scene_id, user_id)
        except Exception as exc:
            logger.warning(f"获取新成员资料失败，改为全量刷新: {exc}")
            await member_cache.refresh_scene(bot, scene_id)
            return
        if member is None:
            await member_cache.refresh_scene(bot, scene_id)
            return
        member_cache.upsert_member(scene_id, member)

    async def handle_member_leave(self, scene_id: str, user_id: str) -> None:
        member_cache.remove_member(scene_id, user_id)

    async def refresh_member_cache_for_all_groups(self) -> None:
        for bot in nonebot.get_bots().values():
            interface = get_interface(bot)
            if not interface:
                continue
            try:
                scenes = await interface.get_scenes(SceneType.GROUP)
            except Exception as exc:
                logger.warning(f"刷新群成员缓存时读取群列表失败: {exc}")
                continue
            for scene in scenes:
                if not scene.is_group:
                    continue
                try:
                    await member_cache.refresh_scene(bot, scene.id)
                except Exception as exc:
                    logger.warning(f"刷新群 {scene.id} 成员缓存失败: {exc}")

    async def refresh_scene_members(self, bot: Bot, scene_id: str) -> str:
        members = await member_cache.refresh_scene(bot, scene_id)
        return f"已刷新本群成员缓存，共 {len(members)} 人。"

    async def _get_effective_group_settings(
        self,
        repos: RepoBundle,
        scene_id: str,
    ) -> GroupSettings:
        settings = await repos.group_settings.get(scene_id)
        pending_date = settings.pure_love_pending_enable_date
        if (
            not settings.pure_love_enabled
            and pending_date
            and pending_date <= self._today()
        ):
            settings = await repos.group_settings.update(
                scene_id,
                pure_love_enabled=True,
                pure_love_pending_enable_date=None,
            )
        return settings

    def _format_pure_love_status(self, settings: GroupSettings) -> str:
        if settings.pure_love_enabled:
            return "开启"
        if settings.pure_love_pending_enable_date:
            pending_date = settings.pure_love_pending_enable_date.strftime("%Y-%m-%d")
            return f"关闭（将于 {pending_date} 开启）"
        return "关闭"

    async def get_theme_list_text(self) -> str:
        lines = list_theme_lines()
        return "当前可用老婆主题：\n" + "\n".join(lines) + "\nall = 全部主题\nnone = 无主题"

    async def get_settings_text(self, session: Uninfo) -> str:
        if not session.scene:
            return "当前会话没有群上下文。"

        async def _run(repos: RepoBundle):
            settings = await self._get_effective_group_settings(repos, session.scene.id)
            global_settings = await repos.global_settings.get()
            user_pref = await repos.theme_preferences.get(
                ThemeScope.USER.value,
                scene_id=session.scene.id,
                user_id=session.user.id if session.user else None,
            )
            group_pref = await repos.theme_preferences.get(
                ThemeScope.GROUP.value,
                scene_id=session.scene.id,
            )
            effective_keys = resolve_effective_theme_keys(
                user_pref.enabled_theme_keys if user_pref else None,
                group_pref.enabled_theme_keys if group_pref else None,
                global_settings.enabled_theme_keys,
            )
            milestone_enabled = self._effective_milestone_enabled(
                global_settings.milestone_notify_enabled,
                settings.milestone_notify_override,
            )
            return (
                f"抽取模式：{MODE_DISPLAY_NAMES[settings.select_mode]}\n"
                f"纯爱模式：{self._format_pure_love_status(settings)}\n"
                f"允许换老婆：{'开启' if settings.allow_change else '关闭'}\n"
                f"换老婆次数：{settings.limit_times}\n"
                f"活跃天数：{settings.active_days}\n"
                f"缘分刊物订阅：{'开启' if settings.fate_report_enabled else '关闭'}\n"
                f"里程碑提醒：{'开启' if milestone_enabled else '关闭'}\n"
                f"当前生效主题：{format_theme_keys(effective_keys)}"
            )

        return await with_repos(_run)

    async def view_theme_preferences(self, session: Uninfo) -> str:
        if not session.scene or not session.user:
            return "当前会话没有群上下文。"

        async def _run(repos: RepoBundle):
            global_settings = await repos.global_settings.get()
            user_pref = await repos.theme_preferences.get(
                ThemeScope.USER.value,
                scene_id=session.scene.id,
                user_id=session.user.id,
            )
            group_pref = await repos.theme_preferences.get(
                ThemeScope.GROUP.value,
                scene_id=session.scene.id,
            )
            effective = resolve_effective_theme_keys(
                user_pref.enabled_theme_keys if user_pref else None,
                group_pref.enabled_theme_keys if group_pref else None,
                global_settings.enabled_theme_keys,
            )
            return (
                f"个人主题：{self._format_theme_override(user_pref.enabled_theme_keys if user_pref else None)}\n"
                f"群主题：{self._format_theme_override(group_pref.enabled_theme_keys if group_pref else None)}\n"
                f"全局主题：{format_theme_keys(global_settings.enabled_theme_keys)}\n"
                f"当前生效：{format_theme_keys(effective)}"
            )

        return await with_repos(_run)

    async def set_theme_preference(
        self,
        scope: ThemeScope,
        raw_selection: str,
        *,
        scene_id: str | None = None,
        user_id: str | None = None,
    ) -> str:
        try:
            theme_keys = parse_theme_selection(raw_selection)
        except ValueError as exc:
            return str(exc)

        async def _run(repos: RepoBundle):
            if scope == ThemeScope.GLOBAL:
                await repos.global_settings.set_enabled_theme_keys(theme_keys)
            else:
                await repos.theme_preferences.upsert(
                    scope.value,
                    theme_keys,
                    scene_id=scene_id,
                    user_id=user_id,
                )

        await with_repos(_run)
        scope_name = {
            ThemeScope.USER: "个人",
            ThemeScope.GROUP: "群",
            ThemeScope.GLOBAL: "全局",
        }[scope]
        return f"已将{scope_name}老婆主题设置为：{format_theme_keys(theme_keys)}"

    async def reset_theme_preference(
        self,
        scope: ThemeScope,
        *,
        scene_id: str | None = None,
        user_id: str | None = None,
    ) -> str:
        async def _run(repos: RepoBundle):
            if scope == ThemeScope.GLOBAL:
                await repos.global_settings.set_enabled_theme_keys(list(DEFAULT_GLOBAL_THEMES))
            else:
                await repos.theme_preferences.delete(
                    scope.value,
                    scene_id=scene_id,
                    user_id=user_id,
                )

        await with_repos(_run)
        scope_name = {
            ThemeScope.USER: "个人",
            ThemeScope.GROUP: "群",
            ThemeScope.GLOBAL: "全局",
        }[scope]
        if scope == ThemeScope.GLOBAL:
            return f"已重置{scope_name}老婆主题为默认值：{format_theme_keys(list(DEFAULT_GLOBAL_THEMES))}"
        return f"已重置{scope_name}老婆主题，后续将继续继承上层设置。"

    async def set_pure_love(self, scene_id: str, enabled: bool) -> str:
        async def _run(repos: RepoBundle):
            settings = await self._get_effective_group_settings(repos, scene_id)
            if enabled:
                if settings.pure_love_enabled:
                    return "本群纯爱模式已开启。"
                if settings.pure_love_pending_enable_date:
                    return (
                        "本群纯爱模式已计划于 "
                        f"{settings.pure_love_pending_enable_date:%Y-%m-%d} 开启，"
                        "今天仍按当前模式运行。"
                    )
                scheduled_date = self._tomorrow()
                await repos.group_settings.update(
                    scene_id,
                    pure_love_enabled=False,
                    pure_love_pending_enable_date=scheduled_date,
                )
                return (
                    f"本群纯爱模式将于 {scheduled_date:%Y-%m-%d} 开启，"
                    "今天仍按当前模式运行。"
                )

            pending_date = settings.pure_love_pending_enable_date
            if settings.pure_love_enabled or pending_date:
                await repos.group_settings.update(
                    scene_id,
                    pure_love_enabled=False,
                    pure_love_pending_enable_date=None,
                )
            if pending_date and not settings.pure_love_enabled:
                return f"已取消本群纯爱模式于 {pending_date:%Y-%m-%d} 的开启计划。"
            return "本群纯爱模式已关闭。"

        return await with_repos(_run)

    async def set_allow_change(self, scene_id: str, enabled: bool) -> str:
        async def _run(repos: RepoBundle):
            await repos.group_settings.update(scene_id, allow_change=enabled)

        await with_repos(_run)
        return f"本群换老婆已{'开启' if enabled else '关闭'}。"

    async def set_limit_times(self, scene_id: str, times: int) -> str:
        limit_times = max(0, times)

        async def _run(repos: RepoBundle):
            await repos.group_settings.update(scene_id, limit_times=limit_times)

        await with_repos(_run)
        return f"本群换老婆次数已设置为 {limit_times} 次。"

    async def set_select_mode(self, scene_id: str, raw_value: str) -> str:
        normalized = raw_value.strip()
        mapping = {
            "随机模式": SelectMode.RANDOM.value,
            "random": SelectMode.RANDOM.value,
            "活跃模式": SelectMode.ACTIVE.value,
            "active": SelectMode.ACTIVE.value,
        }
        if normalized not in mapping:
            return "抽取模式仅支持：随机模式 / 活跃模式"
        mode = mapping[normalized]

        async def _run(repos: RepoBundle):
            await repos.group_settings.update(scene_id, select_mode=mode)

        await with_repos(_run)
        return f"本群抽取模式已切换为 {MODE_DISPLAY_NAMES[mode]}。"

    async def set_active_days(self, scene_id: str, days: int) -> str:
        active_days = max(1, days)

        async def _run(repos: RepoBundle):
            await repos.group_settings.update(scene_id, active_days=active_days)

        await with_repos(_run)
        return f"本群活跃天数已设置为 {active_days} 天。"

    async def set_report_subscription(self, scene_id: str, enabled: bool) -> str:
        async def _run(repos: RepoBundle):
            await repos.group_settings.update(scene_id, fate_report_enabled=enabled)

        await with_repos(_run)
        return f"本群缘分刊物订阅已{'开启' if enabled else '关闭'}。"

    async def set_global_milestone(self, enabled: bool) -> str:
        async def _run(repos: RepoBundle):
            await repos.global_settings.set_milestone_notify_enabled(enabled)

        await with_repos(_run)
        return f"全局里程碑提醒已{'开启' if enabled else '关闭'}。"

    async def set_group_milestone(self, scene_id: str, enabled: bool) -> str:
        async def _run(repos: RepoBundle):
            await repos.group_settings.update(scene_id, milestone_notify_override=enabled)

        await with_repos(_run)
        return f"本群里程碑提醒覆盖已{'开启' if enabled else '关闭'}。"

    async def reset_scene_day(self, scene_id: str) -> str:
        today = self._today()
        moment = self._now()

        async def _run(repos: RepoBundle):
            rows = await repos.daily_states.delete_scene(today, scene_id)
            for row in rows:
                await self._rollback_counter_for_state(repos, row, moment)
            return len(rows)

        count = await with_repos(_run)
        return f"已重置本群今天的老婆记录，共清理 {count} 条状态。"

    async def get_today_waifu(
        self,
        bot: Bot,
        session: Uninfo,
        interface: Interface,
    ) -> UniMessage:
        if not session.scene or not session.user:
            return UniMessage.text("当前会话没有群上下文。")
        members = await member_cache.ensure(session, interface)
        payload = await self._resolve_today_waifu(bot, session, members)
        return await self._build_relation_message(payload)

    async def change_waifu(
        self,
        bot: Bot,
        session: Uninfo,
        interface: Interface,
    ) -> UniMessage:
        if not session.scene or not session.user:
            return UniMessage.text("当前会话没有群上下文。")
        members = await member_cache.ensure(session, interface)
        payload = await self._change_waifu(bot, session, members)
        return await self._build_relation_message(payload)

    async def divorce(
        self,
        bot: Bot,
        session: Uninfo,
        interface: Interface,
    ) -> UniMessage:
        if not session.scene or not session.user:
            return UniMessage.text("当前会话没有群上下文。")
        members = await member_cache.ensure(session, interface)
        payload = await self._divorce(bot, session, members)
        return await self._build_relation_message(payload)

    async def get_cp_roster(self, bot: Bot, scene_id: str) -> UniMessage:
        members = await member_cache.ensure_scene(bot, scene_id)
        today = self._today()

        async def _run(repos: RepoBundle):
            rows = await repos.daily_states.list_paired_scene(today, scene_id)
            pairs = [
                (row.user_id, row.target_id)
                for row in rows
                if not row.lock_mirrored and row.target_id
            ]
            return pairs, None

        pairs, text = await with_repos(_run)
        if text:
            return UniMessage.text(text)
        if not pairs:
            return UniMessage.text("今天本群还没有形成任何 CP。")

        pair_context = []
        for user_id, target_id in pairs:
            user = await self._resolve_display_user(bot, scene_id, user_id, members)
            target = await self._resolve_display_user(bot, scene_id, target_id, members)
            pair_context.append(
                {
                    "left_name": user.name,
                    "left_avatar": user.avatar_url,
                    "right_name": target.name,
                    "right_avatar": target.avatar_url,
                }
            )
        columns = CP_ROSTER_COLUMNS
        row_count = (len(pair_context) + columns - 1) // columns
        image = await render_template_image(
            "cp_roster.html",
            {
                "scene_id": scene_id,
                "pairs": pair_context,
                "title": "本群 CP 花名册",
                "columns": columns,
            },
            selector="main",
            width=1000,
            height=max(480, 260 + row_count * 160),
        )
        return UniMessage.image(raw=image)

    async def get_report(self, bot: Bot, scene_id: str, bucket_type: ReportBucket) -> UniMessage:
        period = get_period_window(bucket_type, self._now())
        rows = await self._get_report_rows(scene_id, period)
        if not rows:
            return UniMessage.text(REPORT_EMPTY_TEXT.replace("周刊", period.title[2:]))
        members = await member_cache.ensure_scene(bot, scene_id)
        image = await self._render_report(bot, scene_id, members, period, rows)
        return UniMessage.image(raw=image)

    async def send_period_report(self, bucket_type: ReportBucket) -> None:
        period = get_period_window(bucket_type, self._now())
        for bot in nonebot.get_bots().values():
            async def _run(repos: RepoBundle):
                return await repos.group_settings.get_subscribed_for_reports()

            groups = await with_repos(_run)
            for group in groups:
                try:
                    rows = await self._get_report_rows(group.scene_id, period)
                    if not rows:
                        continue
                    members = await member_cache.ensure_scene(bot, group.scene_id)
                    image = await self._render_report(bot, group.scene_id, members, period, rows)
                    await UniMessage.image(raw=image).send(
                        target=Target.group(group.scene_id),
                        bot=bot,
                    )
                except Exception as exc:
                    logger.warning(f"发送{bucket_type.value}刊物失败 scene={group.scene_id}: {exc}")

    async def _resolve_today_waifu(
        self,
        bot: Bot,
        session: Uninfo,
        members: dict[str, CachedMember],
    ) -> RelationMessage:
        today = self._today()
        moment = self._now()
        scene_id = session.scene.id
        user_id = session.user.id

        async def _run(repos: RepoBundle):
            settings = await self._get_effective_group_settings(repos, scene_id)
            state = await repos.daily_states.get(today, scene_id, user_id)
            global_settings = await repos.global_settings.get()
            milestone_enabled = self._effective_milestone_enabled(
                global_settings.milestone_notify_enabled,
                settings.milestone_notify_override,
            )
            pure_love_enabled = settings.pure_love_enabled
            if state:
                if state.status == PairStatus.EXHAUSTED.value:
                    return RelationMessage(text=no_waifu_text(), target=None)
                extras: list[str] = []
                if state.lock_mirrored and not state.counted and state.target_id:
                    target_user = await self._resolve_display_user(
                        bot, scene_id, state.target_id, members
                    )
                    total_count = await repos.pair_counters.adjust(
                        scene_id,
                        user_id,
                        state.target_id,
                        1,
                        moment,
                    )
                    state.counted = True
                    state.updated_at = moment
                    if milestone_enabled and total_count and total_count % 5 == 0:
                        extras.append(
                            milestone_text(total_count, session.user.name or user_id, target_user.name)
                        )
                    return RelationMessage(
                        text=mirror_first_pick_text(target_user.is_bot),
                        target=target_user,
                        theme_key=state.theme_key,
                        theme_payload=state.theme_payload,
                        extra_lines=extras,
                    )
                target = await self._resolve_display_user(
                    bot,
                    scene_id,
                    state.target_id or bot.self_id,
                    members,
                )
                return RelationMessage(
                    text=repeat_pick_text(target.is_bot),
                    target=target,
                    theme_key=state.theme_key,
                    theme_payload=state.theme_payload,
                )

            target_id = await self._select_candidate(
                repos,
                settings.select_mode,
                settings.active_days,
                scene_id,
                members,
                bot.self_id,
                requester_id=user_id,
                pure_love=pure_love_enabled,
            )
            theme_roll = await self._roll_theme_for_scope(repos, scene_id, user_id)
            target = await self._resolve_display_user(bot, scene_id, target_id, members)
            extras: list[str] = []

            await repos.daily_states.upsert(
                today,
                scene_id,
                user_id,
                status=PairStatus.PAIRED.value,
                target_id=target_id,
                change_used=0,
                lock_source_user_id=None,
                lock_mirrored=False,
                theme_key=theme_roll.theme_key,
                theme_payload=theme_roll.theme_payload,
                counted=True,
            )

            total_count = 0
            if target_id != bot.self_id:
                total_count = await repos.pair_counters.adjust(
                    scene_id,
                    user_id,
                    target_id,
                    1,
                    moment,
                )

            if pure_love_enabled and target_id != bot.self_id:
                mirrored_theme = await self._roll_theme_for_scope(repos, scene_id, target_id)
                await repos.daily_states.upsert(
                    today,
                    scene_id,
                    target_id,
                    status=PairStatus.PAIRED.value,
                    target_id=user_id,
                    change_used=0,
                    lock_source_user_id=user_id,
                    lock_mirrored=True,
                    theme_key=mirrored_theme.theme_key,
                    theme_payload=mirrored_theme.theme_payload,
                    counted=False,
                )
            elif target_id != bot.self_id:
                target_state = await repos.daily_states.get(today, scene_id, target_id)
                if (
                    target_state
                    and target_state.target_id == user_id
                    and not target_state.lock_mirrored
                ):
                    extras.append(mutual_love_text())

            if milestone_enabled and total_count and total_count % 5 == 0:
                extras.append(
                    milestone_text(
                        total_count,
                        session.user.name or user_id,
                        target.name,
                    )
                )
            return RelationMessage(
                text=first_pick_text(target.is_bot),
                target=target,
                theme_key=theme_roll.theme_key,
                theme_payload=theme_roll.theme_payload,
                extra_lines=extras,
            )

        return await with_repos(_run)

    async def _change_waifu(
        self,
        bot: Bot,
        session: Uninfo,
        members: dict[str, CachedMember],
    ) -> RelationMessage:
        today = self._today()
        moment = self._now()
        scene_id = session.scene.id
        user_id = session.user.id

        async def _run(repos: RepoBundle):
            settings = await self._get_effective_group_settings(repos, scene_id)
            state = await repos.daily_states.get(today, scene_id, user_id)
            if settings.pure_love_enabled:
                return RelationMessage(text=pure_love_block_change_text(), target=None)
            if not settings.allow_change:
                return RelationMessage(text=change_disabled_text(), target=None)
            if not state:
                return RelationMessage(text=need_pick_first_text(), target=None)
            if state.status == PairStatus.EXHAUSTED.value:
                return RelationMessage(text=no_waifu_text(), target=None)
            if not state.target_id:
                return RelationMessage(text=no_waifu_text(), target=None)
            if state.change_used >= settings.limit_times:
                await self._rollback_counter_for_state(repos, state, moment)
                await repos.daily_states.upsert(
                    today,
                    scene_id,
                    user_id,
                    status=PairStatus.EXHAUSTED.value,
                    target_id=None,
                    change_used=settings.limit_times,
                    lock_source_user_id=None,
                    lock_mirrored=False,
                    theme_key=None,
                    theme_payload=None,
                    counted=False,
                )
                return RelationMessage(text=no_waifu_text(), target=None)

            old_target_id = state.target_id
            await self._rollback_counter_for_state(repos, state, moment)

            target_id = await self._select_candidate(
                repos,
                settings.select_mode,
                settings.active_days,
                scene_id,
                members,
                bot.self_id,
                requester_id=user_id,
                extra_exclude={old_target_id},
            )
            theme_roll = await self._roll_theme_for_scope(repos, scene_id, user_id)
            target = await self._resolve_display_user(bot, scene_id, target_id, members)

            new_change_used = state.change_used + 1
            await repos.daily_states.upsert(
                today,
                scene_id,
                user_id,
                status=PairStatus.PAIRED.value,
                target_id=target_id,
                change_used=new_change_used,
                lock_source_user_id=None,
                lock_mirrored=False,
                theme_key=theme_roll.theme_key,
                theme_payload=theme_roll.theme_payload,
                counted=True,
            )
            total_count = 0
            if target_id != bot.self_id:
                total_count = await repos.pair_counters.adjust(
                    scene_id,
                    user_id,
                    target_id,
                    1,
                    moment,
                )

            extras: list[str] = []
            global_settings = await repos.global_settings.get()
            milestone_enabled = self._effective_milestone_enabled(
                global_settings.milestone_notify_enabled,
                settings.milestone_notify_override,
            )
            if milestone_enabled and total_count and total_count % 5 == 0:
                extras.append(
                    milestone_text(total_count, session.user.name or user_id, target.name)
                )
            target_state = await repos.daily_states.get(today, scene_id, target_id)
            if (
                target_id != bot.self_id
                and target_state
                and target_state.target_id == user_id
                and not target_state.lock_mirrored
            ):
                extras.append(mutual_love_text())
            return RelationMessage(
                text=change_success_text(target.is_bot, settings.limit_times - new_change_used),
                target=target,
                theme_key=theme_roll.theme_key,
                theme_payload=theme_roll.theme_payload,
                extra_lines=extras,
            )

        return await with_repos(_run)

    async def _divorce(
        self,
        bot: Bot,
        session: Uninfo,
        members: dict[str, CachedMember],
    ) -> RelationMessage:
        today = self._today()
        moment = self._now()
        scene_id = session.scene.id
        user_id = session.user.id

        async def _run(repos: RepoBundle):
            settings = await self._get_effective_group_settings(repos, scene_id)
            state = await repos.daily_states.get(today, scene_id, user_id)
            if not state or state.status == PairStatus.EXHAUSTED.value or not state.target_id:
                return RelationMessage(text=NO_WAIFU_TEXT, target=None)

            await self._rollback_counter_for_state(repos, state, moment)

            if settings.pure_love_enabled and state.target_id != bot.self_id:
                mirrored_state = await repos.daily_states.get(today, scene_id, state.target_id)
                if mirrored_state and mirrored_state.target_id == user_id:
                    await self._rollback_counter_for_state(repos, mirrored_state, moment)
                    await repos.daily_states.delete(today, scene_id, state.target_id)

            await repos.daily_states.upsert(
                today,
                scene_id,
                user_id,
                status=PairStatus.EXHAUSTED.value,
                target_id=None,
                change_used=settings.limit_times,
                lock_source_user_id=None,
                lock_mirrored=False,
                theme_key=None,
                theme_payload=None,
                counted=False,
            )
            return RelationMessage(text=divorce_text(), target=None)

        return await with_repos(_run)

    async def _get_report_rows(
        self,
        scene_id: str,
        period: PeriodWindow,
    ) -> list[PairCounter]:
        async def _run(repos: RepoBundle):
            return await repos.pair_counters.list_bucket(
                scene_id,
                period.bucket_type,
                period.bucket_key,
            )

        return await with_repos(_run)

    async def _render_report(
        self,
        bot: Bot,
        scene_id: str,
        members: dict[str, CachedMember],
        period: PeriodWindow,
        rows: Sequence[PairCounter],
    ) -> bytes:
        summary = build_report_summary(rows)
        sea_king = (
            None
            if not summary.sea_king
            else {
                "name": (await self._resolve_display_user(bot, scene_id, summary.sea_king[0], members)).name,
                "count": summary.sea_king[1],
            }
        )
        best_match = None
        if summary.best_match:
            left = await self._resolve_display_user(bot, scene_id, summary.best_match[0], members)
            right = await self._resolve_display_user(bot, scene_id, summary.best_match[1], members)
            best_match = {
                "left_name": left.name,
                "right_name": right.name,
                "count": summary.best_match[2],
            }
        yandere = None
        if summary.yandere:
            left = await self._resolve_display_user(bot, scene_id, summary.yandere[0], members)
            right = await self._resolve_display_user(bot, scene_id, summary.yandere[1], members)
            yandere = {
                "left_name": left.name,
                "right_name": right.name,
                "count": summary.yandere[2],
            }

        return await render_template_image(
            "fate_report.html",
            {
                "title": period.title,
                "scene_id": scene_id,
                "range_text": f"{period.start:%Y-%m-%d} ~ {period.end:%Y-%m-%d}",
                "sea_king": sea_king,
                "best_match": best_match,
                "yandere": yandere,
            },
            width=1100,
            height=760,
        )

    async def _select_candidate(
        self,
        repos: RepoBundle,
        select_mode: str,
        active_days: int,
        scene_id: str,
        members: dict[str, CachedMember],
        bot_self_id: str,
        *,
        requester_id: str | None,
        extra_exclude: set[str] | None = None,
        pure_love: bool = False,
    ) -> str:
        candidates = set(members) - self._ban_ids
        if requester_id:
            candidates.discard(requester_id)
        if pure_love:
            locked_ids = await repos.daily_states.list_locked_user_ids(self._today(), scene_id)
            candidates -= locked_ids
        if extra_exclude:
            candidates -= extra_exclude

        final_candidates = candidates
        if select_mode == SelectMode.ACTIVE.value and candidates:
            active_ids = await repos.member_activity.list_active(scene_id, active_days, self._now())
            active_candidates = candidates & active_ids
            if active_candidates:
                final_candidates = active_candidates

        if final_candidates:
            return random.choice(sorted(final_candidates))
        return bot_self_id

    async def _roll_theme_for_scope(
        self,
        repos: RepoBundle,
        scene_id: str,
        user_id: str | None,
    ) -> ThemeRollResult:
        global_settings = await repos.global_settings.get()
        group_pref = await repos.theme_preferences.get(
            ThemeScope.GROUP.value,
            scene_id=scene_id,
        )
        user_pref = None
        if user_id:
            user_pref = await repos.theme_preferences.get(
                ThemeScope.USER.value,
                scene_id=scene_id,
                user_id=user_id,
            )
        theme_keys = resolve_effective_theme_keys(
            user_pref.enabled_theme_keys if user_pref else None,
            group_pref.enabled_theme_keys if group_pref else None,
            global_settings.enabled_theme_keys,
        )
        if not theme_keys:
            return ThemeRollResult(None, None)
        theme_key = random.choice(theme_keys)
        return ThemeRollResult(theme_key, build_theme_payload(theme_key))

    async def _resolve_display_user(
        self,
        bot: Bot,
        scene_id: str,
        user_id: str,
        members: dict[str, CachedMember],
    ) -> DisplayUser:
        if cached := members.get(user_id):
            return DisplayUser(
                user_id=user_id,
                name=cached.name,
                avatar_url=cached.avatar_url,
                role_tag=self._resolve_role_tag(user_id, cached.role_id),
                is_bot=user_id == bot.self_id,
            )

        if interface := get_interface(bot):
            try:
                member = await interface.get_member(SceneType.GROUP, scene_id, user_id)
            except Exception:
                member = None
            if member:
                member_cache.upsert_member(scene_id, member)
                role_id = member.role.id if member.role else None
                return DisplayUser(
                    user_id=user_id,
                    name=member.nick or member.user.nick or member.user.name or user_id,
                    avatar_url=member.user.avatar,
                    role_tag=self._resolve_role_tag(user_id, role_id),
                    is_bot=user_id == bot.self_id,
                )
            try:
                user = await interface.get_user(user_id)
            except Exception:
                user = None
            if user:
                return DisplayUser(
                    user_id=user_id,
                    name=user.nick or user.name or user_id,
                    avatar_url=user.avatar,
                    role_tag=self._resolve_role_tag(user_id, None),
                    is_bot=user_id == bot.self_id,
                )

        return DisplayUser(
            user_id=user_id,
            name="Bot" if user_id == bot.self_id else user_id,
            avatar_url=None,
            role_tag=self._resolve_role_tag(user_id, None),
            is_bot=user_id == bot.self_id,
        )

    def _resolve_role_tag(self, user_id: str, role_id: str | None) -> str | None:
        if user_id in self._superusers():
            return "SUPERUSER"
        if not role_id:
            return None
        role = str(role_id).upper()
        if role in {"OWNER", "ADMINISTRATOR"}:
            return role
        return None

    async def _build_relation_message(self, payload: RelationMessage) -> UniMessage:
        message = UniMessage.text(payload.text)
        if payload.target:
            message += UniMessage.text(f"\n{payload.target.name}({payload.target.user_id})")
            themed = await self._render_user_card(
                payload.target,
                payload.theme_key,
                payload.theme_payload,
            )
            if themed:
                message += UniMessage.image(raw=themed)
            elif payload.target.avatar_url:
                message += UniMessage.image(url=payload.target.avatar_url)
        if payload.extra_lines:
            message += UniMessage.text("\n" + "\n".join(payload.extra_lines))
        return message

    async def _render_user_card(
        self,
        target: DisplayUser,
        theme_key: str | None,
        theme_payload: dict[str, Any] | None,
    ) -> bytes | None:
        if not target.avatar_url:
            return None
        if not theme_key or not theme_payload:
            return None
        try:
            theme_data = build_theme_context(theme_key, theme_payload)
            return await render_theme_card(
                target.avatar_url,
                theme_key,
                theme_data,
            )
        except (httpx.HTTPError, OSError, ValueError) as exc:
            logger.warning(f"渲染主题卡片失败，回退头像模式: {exc}")
            return None

    async def _rollback_counter_for_state(
        self,
        repos: RepoBundle,
        state: DailyWaifuState,
        moment: datetime,
    ) -> None:
        if not state.counted or not state.target_id:
            return
        if state.target_id == "":
            return
        await repos.pair_counters.adjust(
            state.scene_id,
            state.user_id,
            state.target_id,
            -1,
            moment,
        )

    def _effective_milestone_enabled(
        self,
        global_enabled: bool,
        group_override: bool | None,
    ) -> bool:
        if group_override is None:
            return global_enabled
        return group_override

    def _format_theme_override(self, value: list[str] | None) -> str:
        if value is None:
            return "未设置（继承上层）"
        return format_theme_keys(value)


waifu_service = TodayWaifuService()
