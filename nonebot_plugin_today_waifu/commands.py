from __future__ import annotations

import re
from typing import Any

from nonebot import on_regex
from nonebot.adapters import Bot
from nonebot.internal.rule import Rule
from nonebot.params import RegexDict
from nonebot.permission import SUPERUSER
from nonebot_plugin_alconna import UniMessage
from nonebot_plugin_uninfo import GROUP, Uninfo

from .config import plugin_config
from .constants import ReportBucket, ThemeScope
from .services import waifu_service


def _not_private(session: Uninfo) -> bool:
    return bool(session.scene and not session.scene.is_private)


NOT_PRIVATE = Rule(_not_private)
PATTERN_STR = "|".join(re.escape(name) for name in ["今日老婆", *plugin_config.today_waifu_aliases])


today_waifu = on_regex(
    rf"^\s*({PATTERN_STR})\s*$",
    permission=GROUP | SUPERUSER,
    rule=NOT_PRIVATE,
    priority=7,
    block=True,
)
today_waifu_change = on_regex(
    r"^\s*换老婆\s*$",
    permission=GROUP | SUPERUSER,
    rule=NOT_PRIVATE,
    priority=7,
    block=True,
)
today_waifu_divorce = on_regex(
    r"^\s*(离婚|分手)\s*$",
    permission=GROUP | SUPERUSER,
    rule=NOT_PRIVATE,
    priority=7,
    block=True,
)
today_waifu_refresh = on_regex(
    rf"^\s*(刷新|重置)(?P<name>{PATTERN_STR})\s*$",
    permission=SUPERUSER,
    rule=NOT_PRIVATE,
    priority=7,
    block=True,
)
waifu_settings = on_regex(
    r"^\s*老婆设置\s*$",
    permission=GROUP | SUPERUSER,
    rule=NOT_PRIVATE,
    priority=7,
    block=True,
)

theme_list = on_regex(
    r"^\s*老婆主题列表\s*$",
    permission=GROUP | SUPERUSER,
    rule=NOT_PRIVATE,
    priority=7,
    block=True,
)
theme_view = on_regex(
    r"^\s*查看老婆主题\s*$",
    permission=GROUP | SUPERUSER,
    rule=NOT_PRIVATE,
    priority=7,
    block=True,
)
theme_set_user = on_regex(
    r"^\s*老婆主题设置\s+(?P<selection>.+)\s*$",
    permission=GROUP | SUPERUSER,
    rule=NOT_PRIVATE,
    priority=7,
    block=True,
)
theme_set_group = on_regex(
    r"^\s*群老婆主题设置\s+(?P<selection>.+)\s*$",
    permission=GROUP | SUPERUSER,
    rule=NOT_PRIVATE,
    priority=7,
    block=True,
)
theme_set_global = on_regex(
    r"^\s*全局老婆主题设置\s+(?P<selection>.+)\s*$",
    permission=SUPERUSER,
    priority=7,
    block=True,
)
theme_reset_user = on_regex(
    r"^\s*重置老婆主题\s*$",
    permission=GROUP | SUPERUSER,
    rule=NOT_PRIVATE,
    priority=7,
    block=True,
)
theme_reset_group = on_regex(
    r"^\s*重置群老婆主题\s*$",
    permission=GROUP | SUPERUSER,
    rule=NOT_PRIVATE,
    priority=7,
    block=True,
)
theme_reset_global = on_regex(
    r"^\s*重置全局老婆主题\s*$",
    permission=SUPERUSER,
    priority=7,
    block=True,
)

cp_roster = on_regex(
    r"^\s*(本群cp|花名册)\s*$",
    permission=GROUP | SUPERUSER,
    rule=NOT_PRIVATE,
    priority=7,
    block=True,
)
fate_report = on_regex(
    r"^\s*缘分(?P<period>周刊|月刊|年刊)\s*$",
    permission=GROUP | SUPERUSER,
    rule=NOT_PRIVATE,
    priority=7,
    block=True,
)

pure_love_toggle = on_regex(
    r"^\s*((?P<action1>开启|关闭)纯爱模式|纯爱模式\s*(?P<action2>on|off|开启|关闭))\s*$",
    permission=GROUP | SUPERUSER,
    rule=NOT_PRIVATE,
    priority=7,
    block=True,
)
change_toggle = on_regex(
    r"^\s*((?P<action1>开启|关闭)换老婆|换老婆\s*(?P<action2>on|off|开启|关闭))\s*$",
    permission=GROUP | SUPERUSER,
    rule=NOT_PRIVATE,
    priority=7,
    block=True,
)
limit_times_set = on_regex(
    r"^\s*设置换老婆次数\s*(?P<times>\d+)\s*$",
    permission=GROUP | SUPERUSER,
    rule=NOT_PRIVATE,
    priority=7,
    block=True,
)
select_mode_set = on_regex(
    r"^\s*设置抽取模式\s*(?P<mode>随机|活跃|随机模式|活跃模式|random|active)\s*$",
    permission=GROUP | SUPERUSER,
    rule=NOT_PRIVATE,
    priority=7,
    block=True,
)
active_days_set = on_regex(
    r"^\s*设置活跃天数\s*(?P<days>\d+)\s*$",
    permission=GROUP | SUPERUSER,
    rule=NOT_PRIVATE,
    priority=7,
    block=True,
)

report_subscription = on_regex(
    r"^\s*((?P<action1>开启|关闭)缘分周刊|缘分周刊\s*(?P<action2>on|off|开启|关闭))\s*$",
    permission=GROUP | SUPERUSER,
    rule=NOT_PRIVATE,
    priority=7,
    block=True,
)

global_milestone_toggle = on_regex(
    r"^\s*((?P<action1>开启|关闭)里程碑提醒|全局里程碑提醒\s*(?P<action2>on|off|开启|关闭))\s*$",
    permission=SUPERUSER,
    priority=7,
    block=True,
)
group_milestone_toggle = on_regex(
    r"^\s*(本群(?P<action1>开启|关闭)里程碑提醒|本群里程碑提醒\s*(?P<action2>on|off|开启|关闭))\s*$",
    permission=GROUP | SUPERUSER,
    rule=NOT_PRIVATE,
    priority=7,
    block=True,
)


def _ensure_group_admin(session: Uninfo) -> str | None:
    if waifu_service.is_group_admin(session):
        return None
    return "这个操作需要群管理或超级用户。"


async def _finish_message(matcher, message: str | UniMessage) -> None:
    if isinstance(message, UniMessage):
        await message.finish(reply_to=True)
        return
    await UniMessage.text(message).finish(reply_to=True)


@today_waifu.handle()
async def _(bot: Bot, session: Uninfo):
    await _finish_message(
        today_waifu,
        await waifu_service.get_today_waifu(bot, session),
    )


@today_waifu_change.handle()
async def _(bot: Bot, session: Uninfo):
    await _finish_message(
        today_waifu_change,
        await waifu_service.change_waifu(bot, session),
    )


@today_waifu_divorce.handle()
async def _(bot: Bot, session: Uninfo):
    await _finish_message(
        today_waifu_divorce,
        await waifu_service.divorce(bot, session),
    )


@today_waifu_refresh.handle()
async def _(session: Uninfo):
    await _finish_message(
        today_waifu_refresh,
        await waifu_service.reset_scene_day(session.scene.id),
    )


@waifu_settings.handle()
async def _(session: Uninfo):
    await _finish_message(waifu_settings, await waifu_service.get_settings_text(session))


@theme_list.handle()
async def _():
    await _finish_message(theme_list, await waifu_service.get_theme_list_text())


@theme_view.handle()
async def _(session: Uninfo):
    await _finish_message(theme_view, await waifu_service.view_theme_preferences(session))


@theme_set_user.handle()
async def _(session: Uninfo, data: dict[str, Any] = RegexDict()):
    await _finish_message(
        theme_set_user,
        await waifu_service.set_theme_preference(
            ThemeScope.USER,
            data["selection"].strip(),
            scene_id=session.scene.id,
            user_id=session.user.id,
        )
    )


@theme_set_group.handle()
async def _(session: Uninfo, data: dict[str, Any] = RegexDict()):
    if error := _ensure_group_admin(session):
        await _finish_message(theme_set_group, error)
    await _finish_message(
        theme_set_group,
        await waifu_service.set_theme_preference(
            ThemeScope.GROUP,
            data["selection"].strip(),
            scene_id=session.scene.id,
        )
    )


@theme_set_global.handle()
async def _(session: Uninfo, data: dict[str, Any] = RegexDict()):
    await _finish_message(
        theme_set_global,
        await waifu_service.set_theme_preference(
            ThemeScope.GLOBAL,
            data["selection"].strip(),
        )
    )


@theme_reset_user.handle()
async def _(session: Uninfo):
    await _finish_message(
        theme_reset_user,
        await waifu_service.reset_theme_preference(
            ThemeScope.USER,
            scene_id=session.scene.id,
            user_id=session.user.id,
        )
    )


@theme_reset_group.handle()
async def _(session: Uninfo):
    if error := _ensure_group_admin(session):
        await _finish_message(theme_reset_group, error)
    await _finish_message(
        theme_reset_group,
        await waifu_service.reset_theme_preference(
            ThemeScope.GROUP,
            scene_id=session.scene.id,
        )
    )


@theme_reset_global.handle()
async def _():
    await _finish_message(
        theme_reset_global,
        await waifu_service.reset_theme_preference(ThemeScope.GLOBAL)
    )


@cp_roster.handle()
async def _(bot: Bot, session: Uninfo):
    await _finish_message(cp_roster, await waifu_service.get_cp_roster(bot, session.scene.id))


@fate_report.handle()
async def _(bot: Bot, session: Uninfo, data: dict[str, Any] = RegexDict()):
    bucket_type = {
        "周刊": ReportBucket.WEEK,
        "月刊": ReportBucket.MONTH,
        "年刊": ReportBucket.YEAR,
    }[data["period"]]
    await _finish_message(
        fate_report,
        await waifu_service.get_report(bot, session.scene.id, bucket_type),
    )


@pure_love_toggle.handle()
async def _(session: Uninfo, data: dict[str, Any] = RegexDict()):
    if error := _ensure_group_admin(session):
        await _finish_message(pure_love_toggle, error)
    action = data.get("action1") or data.get("action2")
    enabled = action in ("开启", "on")
    await _finish_message(
        pure_love_toggle,
        await waifu_service.set_pure_love(session.scene.id, enabled),
    )


@change_toggle.handle()
async def _(session: Uninfo, data: dict[str, Any] = RegexDict()):
    if error := _ensure_group_admin(session):
        await _finish_message(change_toggle, error)
    action = data.get("action1") or data.get("action2")
    enabled = action in ("开启", "on")
    await _finish_message(
        change_toggle,
        await waifu_service.set_allow_change(session.scene.id, enabled),
    )


@limit_times_set.handle()
async def _(session: Uninfo, data: dict[str, Any] = RegexDict()):
    if error := _ensure_group_admin(session):
        await _finish_message(limit_times_set, error)
    await _finish_message(
        limit_times_set,
        await waifu_service.set_limit_times(session.scene.id, int(data["times"])),
    )


@select_mode_set.handle()
async def _(session: Uninfo, data: dict[str, Any] = RegexDict()):
    if error := _ensure_group_admin(session):
        await _finish_message(select_mode_set, error)
    await _finish_message(
        select_mode_set,
        await waifu_service.set_select_mode(session.scene.id, data["mode"]),
    )


@active_days_set.handle()
async def _(session: Uninfo, data: dict[str, Any] = RegexDict()):
    if error := _ensure_group_admin(session):
        await _finish_message(active_days_set, error)
    await _finish_message(
        active_days_set,
        await waifu_service.set_active_days(session.scene.id, int(data["days"])),
    )


@report_subscription.handle()
async def _(session: Uninfo, data: dict[str, Any] = RegexDict()):
    if error := _ensure_group_admin(session):
        await _finish_message(report_subscription, error)
    action = data.get("action1") or data.get("action2")
    enabled = action in ("开启", "on")
    await _finish_message(
        report_subscription,
        await waifu_service.set_report_subscription(session.scene.id, enabled)
    )


@global_milestone_toggle.handle()
async def _(session: Uninfo, data: dict[str, Any] = RegexDict()):
    action = data.get("action1") or data.get("action2")
    enabled = action in ("开启", "on")
    await _finish_message(
        global_milestone_toggle,
        await waifu_service.set_global_milestone(enabled),
    )


@group_milestone_toggle.handle()
async def _(session: Uninfo, data: dict[str, Any] = RegexDict()):
    if error := _ensure_group_admin(session):
        await _finish_message(group_milestone_toggle, error)
    action = data.get("action1") or data.get("action2")
    enabled = action in ("开启", "on")
    await _finish_message(
        group_milestone_toggle,
        await waifu_service.set_group_milestone(session.scene.id, enabled),
    )
