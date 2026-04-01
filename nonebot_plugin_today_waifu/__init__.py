from __future__ import annotations

import os
import sys

from nonebot import get_driver, on_type, require
from nonebot.adapters import Bot, Event
from nonebot.adapters.onebot.v11 import (
    GroupDecreaseNoticeEvent,
    GroupIncreaseNoticeEvent,
)
from nonebot.message import event_postprocessor
from nonebot.plugin import PluginMetadata, inherit_supported_adapters

from .bootstrap import inject_orm_database_url
from .config import Config
from .constants import ReportBucket
from .render.runtime import close_theme_card_client
from .texts import HELP_TEXT

_TEST_MODE = bool(os.environ.get("PYTEST_CURRENT_TEST")) or "pytest" in sys.modules

inject_orm_database_url()

require("nonebot_plugin_orm")
if not _TEST_MODE:
    require("nonebot_plugin_htmlrender")
require("nonebot_plugin_apscheduler")
require("nonebot_plugin_alconna")
require("nonebot_plugin_uninfo")

from nonebot_plugin_apscheduler import scheduler
from nonebot_plugin_uninfo import Uninfo

from . import commands, migrations
from .config import plugin_config
from .services import waifu_service

__plugin_meta__ = PluginMetadata(
    name="今日老婆",
    description="随机抽群友当老婆，还支持纯爱、主题卡面和缘分刊物。",
    usage=HELP_TEXT,
    type="application",
    config=Config,
    homepage="https://github.com/glamorgan9826/nonebot-plugin-today-waifu",
    supported_adapters=inherit_supported_adapters(
        "nonebot_plugin_alconna",
        "nonebot_plugin_uninfo",
    ),
    extra={
        "author": "k1yuyu",
        "version": "0.2.0",
    },
)

driver = get_driver()


@event_postprocessor
async def _track_group_activity(event: Event, session: Uninfo):
    if event.get_type() != "message":
        return
    await waifu_service.track_message_activity(session)


group_member_increase = on_type(GroupIncreaseNoticeEvent, priority=1, block=False)
group_member_decrease = on_type(GroupDecreaseNoticeEvent, priority=1, block=False)


@group_member_increase.handle()
async def _(bot: Bot, event: GroupIncreaseNoticeEvent):
    await waifu_service.handle_member_join(bot, str(event.group_id), str(event.user_id))


@group_member_decrease.handle()
async def _(event: GroupDecreaseNoticeEvent):
    await waifu_service.handle_member_leave(str(event.group_id), str(event.user_id))


@driver.on_startup
async def _startup() -> None:
    return None


@driver.on_shutdown
async def _shutdown() -> None:
    await close_theme_card_client()


@scheduler.scheduled_job(
    "cron",
    hour=plugin_config.today_waifu_member_refresh_hour,
    minute=plugin_config.today_waifu_member_refresh_minute,
    max_instances=1,
    coalesce=True,
)
async def _nightly_member_refresh() -> None:
    await waifu_service.refresh_member_cache_for_all_groups()


@scheduler.scheduled_job(
    "cron",
    day_of_week="sun",
    hour=plugin_config.today_waifu_report_hour,
    minute=plugin_config.today_waifu_report_minute,
    max_instances=1,
    coalesce=True,
)
async def _send_week_report() -> None:
    await waifu_service.send_period_report(ReportBucket.WEEK)


@scheduler.scheduled_job(
    "cron",
    day="last",
    hour=plugin_config.today_waifu_report_hour,
    minute=plugin_config.today_waifu_report_minute,
    max_instances=1,
    coalesce=True,
)
async def _send_month_report() -> None:
    await waifu_service.send_period_report(ReportBucket.MONTH)


@scheduler.scheduled_job(
    "cron",
    month=12,
    day=31,
    hour=plugin_config.today_waifu_report_hour,
    minute=plugin_config.today_waifu_report_minute,
    max_instances=1,
    coalesce=True,
)
async def _send_year_report() -> None:
    await waifu_service.send_period_report(ReportBucket.YEAR)


__all__ = [
    "commands",
    "migrations",
]
