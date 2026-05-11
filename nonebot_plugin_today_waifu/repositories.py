from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from nonebot_plugin_orm import get_session
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import plugin_config
from .constants import (
    DEFAULT_GLOBAL_THEMES,
    ReportBucket,
    get_month_bucket_key,
    get_week_bucket_key,
    get_year_bucket_key,
)
from .models import (
    DailyWaifuState,
    GlobalSettings,
    GroupSettings,
    MemberActivity,
    PairCounter,
    ThemePreference,
)


@dataclass(slots=True)
class RepoBundle:
    session: AsyncSession
    global_settings: "GlobalSettingsRepo"
    group_settings: "GroupSettingsRepo"
    theme_preferences: "ThemePreferenceRepo"
    daily_states: "DailyStateRepo"
    pair_counters: "PairCounterRepo"
    member_activity: "MemberActivityRepo"


async def create_repo_bundle() -> RepoBundle:
    session = get_session()
    return RepoBundle(
        session=session,
        global_settings=GlobalSettingsRepo(session),
        group_settings=GroupSettingsRepo(session),
        theme_preferences=ThemePreferenceRepo(session),
        daily_states=DailyStateRepo(session),
        pair_counters=PairCounterRepo(session),
        member_activity=MemberActivityRepo(session),
    )


class GlobalSettingsRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self) -> GlobalSettings:
        item = await self.session.get(GlobalSettings, 1)
        if item:
            return item
        item = GlobalSettings(
            id=1,
            enabled_theme_keys=list(DEFAULT_GLOBAL_THEMES),
            milestone_notify_enabled=plugin_config.today_waifu_global_milestone_notify,
        )
        self.session.add(item)
        await self.session.flush()
        return item

    async def set_enabled_theme_keys(self, theme_keys: list[str]) -> GlobalSettings:
        item = await self.get()
        item.enabled_theme_keys = theme_keys
        await self.session.flush()
        return item

    async def set_milestone_notify_enabled(self, enabled: bool) -> GlobalSettings:
        item = await self.get()
        item.milestone_notify_enabled = enabled
        await self.session.flush()
        return item


class GroupSettingsRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, scene_id: str) -> GroupSettings:
        item = await self.session.get(GroupSettings, scene_id)
        if item:
            return item
        item = GroupSettings(
            scene_id=scene_id,
            allow_change=plugin_config.today_waifu_default_change_waifu,
            limit_times=plugin_config.today_waifu_default_limit_times,
            select_mode=plugin_config.today_waifu_default_select_mode,
            active_days=plugin_config.today_waifu_default_active_days,
        )
        self.session.add(item)
        await self.session.flush()
        return item

    async def get_subscribed_for_reports(self) -> list[GroupSettings]:
        statement = select(GroupSettings).where(
            GroupSettings.fate_report_enabled.is_(True)
        )
        return list((await self.session.scalars(statement)).all())

    async def update(self, scene_id: str, **fields) -> GroupSettings:
        item = await self.get(scene_id)
        for key, value in fields.items():
            setattr(item, key, value)
        await self.session.flush()
        return item

    async def list_scene_ids(self) -> list[str]:
        statement = select(GroupSettings.scene_id)
        return list((await self.session.scalars(statement)).all())


class ThemePreferenceRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(
        self, scope: str, *, scene_id: str | None = None, user_id: str | None = None
    ) -> ThemePreference | None:
        statement = select(ThemePreference).where(
            ThemePreference.scope == scope,
            ThemePreference.scene_id == scene_id,
            ThemePreference.user_id == user_id,
        )
        return (await self.session.scalars(statement)).one_or_none()

    async def upsert(
        self,
        scope: str,
        enabled_theme_keys: list[str],
        *,
        scene_id: str | None = None,
        user_id: str | None = None,
    ) -> ThemePreference:
        item = await self.get(scope, scene_id=scene_id, user_id=user_id)
        if item:
            item.enabled_theme_keys = enabled_theme_keys
            await self.session.flush()
            return item
        item = ThemePreference(
            scope=scope,
            scene_id=scene_id,
            user_id=user_id,
            enabled_theme_keys=enabled_theme_keys,
        )
        self.session.add(item)
        await self.session.flush()
        return item

    async def delete(
        self, scope: str, *, scene_id: str | None = None, user_id: str | None = None
    ) -> None:
        statement = delete(ThemePreference).where(
            ThemePreference.scope == scope,
            ThemePreference.scene_id == scene_id,
            ThemePreference.user_id == user_id,
        )
        await self.session.execute(statement)


class DailyStateRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, day: date, scene_id: str, user_id: str) -> DailyWaifuState | None:
        statement = select(DailyWaifuState).where(
            DailyWaifuState.date == day,
            DailyWaifuState.scene_id == scene_id,
            DailyWaifuState.user_id == user_id,
        )
        return (await self.session.scalars(statement)).one_or_none()

    async def upsert(self, day: date, scene_id: str, user_id: str, **fields) -> DailyWaifuState:
        item = await self.get(day, scene_id, user_id)
        if item:
            for key, value in fields.items():
                setattr(item, key, value)
            item.updated_at = datetime.now()
            await self.session.flush()
            return item
        item = DailyWaifuState(
            date=day,
            scene_id=scene_id,
            user_id=user_id,
            **fields,
        )
        self.session.add(item)
        await self.session.flush()
        return item

    async def delete(self, day: date, scene_id: str, user_id: str) -> None:
        statement = delete(DailyWaifuState).where(
            DailyWaifuState.date == day,
            DailyWaifuState.scene_id == scene_id,
            DailyWaifuState.user_id == user_id,
        )
        await self.session.execute(statement)

    async def list_scene(self, day: date, scene_id: str) -> list[DailyWaifuState]:
        statement = select(DailyWaifuState).where(
            DailyWaifuState.date == day,
            DailyWaifuState.scene_id == scene_id,
        )
        return list((await self.session.scalars(statement)).all())

    async def list_paired_scene(self, day: date, scene_id: str) -> list[DailyWaifuState]:
        statement = select(DailyWaifuState).where(
            DailyWaifuState.date == day,
            DailyWaifuState.scene_id == scene_id,
            DailyWaifuState.status == "paired",
        ).order_by(
            DailyWaifuState.updated_at.asc(),
            DailyWaifuState.id.asc(),
        )
        return list((await self.session.scalars(statement)).all())

    async def delete_scene(self, day: date, scene_id: str) -> list[DailyWaifuState]:
        rows = await self.list_scene(day, scene_id)
        statement = delete(DailyWaifuState).where(
            DailyWaifuState.date == day,
            DailyWaifuState.scene_id == scene_id,
        )
        await self.session.execute(statement)
        return rows

    async def list_locked_user_ids(self, day: date, scene_id: str) -> set[str]:
        """Return the set of user IDs that are already claimed as
        someone's waifu (i.e. appear as *target_id* in a paired
        record). These members cannot be picked again in pure-love
        mode.
        """
        statement = select(DailyWaifuState.target_id).where(
            DailyWaifuState.date == day,
            DailyWaifuState.scene_id == scene_id,
            DailyWaifuState.status == "paired",
            DailyWaifuState.target_id.isnot(None),
        )
        return set((await self.session.scalars(statement)).all())

    async def list_divorced_user_ids(self, day: date, scene_id: str) -> set[str]:
        """Return users who actively ended today's relation in this scene."""
        statement = select(DailyWaifuState.user_id).where(
            DailyWaifuState.date == day,
            DailyWaifuState.scene_id == scene_id,
            DailyWaifuState.status == "divorced",
        )
        return set((await self.session.scalars(statement)).all())


class MemberActivityRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def touch(self, scene_id: str, user_id: str, moment: datetime) -> MemberActivity:
        statement = select(MemberActivity).where(
            MemberActivity.scene_id == scene_id,
            MemberActivity.user_id == user_id,
        )
        item = (await self.session.scalars(statement)).one_or_none()
        if item:
            item.last_speak_at = moment
            await self.session.flush()
            return item
        item = MemberActivity(scene_id=scene_id, user_id=user_id, last_speak_at=moment)
        self.session.add(item)
        await self.session.flush()
        return item

    async def list_active(self, scene_id: str, days: int, now: datetime) -> set[str]:
        since = now - timedelta(days=days)
        statement = select(MemberActivity.user_id).where(
            MemberActivity.scene_id == scene_id,
            MemberActivity.last_speak_at >= since,
        )
        return set((await self.session.scalars(statement)).all())


class PairCounterRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    def _bucket_pairs(self, moment: datetime) -> list[tuple[str, str]]:
        return [
            (ReportBucket.ALL.value, ReportBucket.ALL.value),
            (ReportBucket.WEEK.value, get_week_bucket_key(moment.date())),
            (ReportBucket.MONTH.value, get_month_bucket_key(moment.date())),
            (ReportBucket.YEAR.value, get_year_bucket_key(moment.date())),
        ]

    async def adjust(
        self,
        scene_id: str,
        user_id: str,
        target_id: str,
        delta: int,
        moment: datetime,
    ) -> int:
        all_count = 0
        for bucket_type, bucket_key in self._bucket_pairs(moment):
            statement = select(PairCounter).where(
                PairCounter.scene_id == scene_id,
                PairCounter.bucket_type == bucket_type,
                PairCounter.bucket_key == bucket_key,
                PairCounter.user_id == user_id,
                PairCounter.target_id == target_id,
            )
            item = (await self.session.scalars(statement)).one_or_none()
            if item:
                item.count += delta
                if item.count <= 0:
                    await self.session.delete(item)
                    count = 0
                else:
                    count = item.count
            elif delta > 0:
                item = PairCounter(
                    scene_id=scene_id,
                    bucket_type=bucket_type,
                    bucket_key=bucket_key,
                    user_id=user_id,
                    target_id=target_id,
                    count=delta,
                )
                self.session.add(item)
                count = delta
            else:
                count = 0
            if bucket_type == ReportBucket.ALL.value:
                all_count = count
        await self.session.flush()
        return all_count

    async def list_bucket(
        self,
        scene_id: str,
        bucket_type: ReportBucket,
        bucket_key: str,
    ) -> list[PairCounter]:
        statement = select(PairCounter).where(
            PairCounter.scene_id == scene_id,
            PairCounter.bucket_type == bucket_type.value,
            PairCounter.bucket_key == bucket_key,
        )
        return list((await self.session.scalars(statement)).all())


async def with_repos(callback):
    repos = await create_repo_bundle()
    async with repos.session:
        async with repos.session.begin():
            return await callback(repos)
