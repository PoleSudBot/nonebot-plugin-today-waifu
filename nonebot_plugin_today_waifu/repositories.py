from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta

from nonebot_plugin_orm import get_session
from sqlalchemy import delete, select, update
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from .config import plugin_config
from .constants import (
    DEFAULT_GLOBAL_THEMES,
    PairStatus,
    ReportBucket,
    ThemeScope,
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

    def _normalize_keys(
        self,
        scope: str,
        scene_id: str | None,
        user_id: str | None,
    ) -> tuple[str, str]:
        # 用空字符串替代 NULL，保证唯一约束在全局/群级偏好上也真正生效。
        if scope == ThemeScope.GLOBAL.value:
            return "", ""
        if scope == ThemeScope.GROUP.value:
            return scene_id or "", ""
        return scene_id or "", user_id or ""

    async def get(
        self, scope: str, *, scene_id: str | None = None, user_id: str | None = None
    ) -> ThemePreference | None:
        scene_key, user_key = self._normalize_keys(scope, scene_id, user_id)
        statement = select(ThemePreference).where(
            ThemePreference.scope == scope,
            ThemePreference.scene_id == scene_key,
            ThemePreference.user_id == user_key,
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
        scene_key, user_key = self._normalize_keys(scope, scene_id, user_id)
        item = await self.get(scope, scene_id=scene_key, user_id=user_key)
        if item:
            item.enabled_theme_keys = enabled_theme_keys
            await self.session.flush()
            return item
        item = ThemePreference(
            scope=scope,
            scene_id=scene_key,
            user_id=user_key,
            enabled_theme_keys=enabled_theme_keys,
        )
        self.session.add(item)
        await self.session.flush()
        return item

    async def delete(
        self, scope: str, *, scene_id: str | None = None, user_id: str | None = None
    ) -> None:
        scene_key, user_key = self._normalize_keys(scope, scene_id, user_id)
        statement = delete(ThemePreference).where(
            ThemePreference.scope == scope,
            ThemePreference.scene_id == scene_key,
            ThemePreference.user_id == user_key,
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

    async def insert(self, day: date, scene_id: str, user_id: str, **fields) -> DailyWaifuState:
        # 纯爱绑定不能覆盖并发写入的状态，必须让唯一约束暴露冲突后由服务层重试。
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
            DailyWaifuState.status == PairStatus.PAIRED.value,
            DailyWaifuState.target_id.isnot(None),
        )
        return set((await self.session.scalars(statement)).all())

    async def list_paired_user_ids(self, day: date, scene_id: str) -> set[str]:
        """Return users who already have their own active relation today."""
        statement = select(DailyWaifuState.user_id).where(
            DailyWaifuState.date == day,
            DailyWaifuState.scene_id == scene_id,
            DailyWaifuState.status == PairStatus.PAIRED.value,
        )
        return set((await self.session.scalars(statement)).all())

    async def list_divorced_user_ids(self, day: date, scene_id: str) -> set[str]:
        """Return users who actively ended today's relation in this scene."""
        statement = select(DailyWaifuState.user_id).where(
            DailyWaifuState.date == day,
            DailyWaifuState.scene_id == scene_id,
            DailyWaifuState.status == PairStatus.DIVORCED.value,
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

    def _counter_identity(
        self,
        scene_id: str,
        bucket_type: str,
        bucket_key: str,
        user_id: str,
        target_id: str,
    ) -> dict[str, str]:
        return {
            "scene_id": scene_id,
            "bucket_type": bucket_type,
            "bucket_key": bucket_key,
            "user_id": user_id,
            "target_id": target_id,
        }

    async def _get_count(self, identity: dict[str, str]) -> int:
        statement = select(PairCounter.count).where(
            PairCounter.scene_id == identity["scene_id"],
            PairCounter.bucket_type == identity["bucket_type"],
            PairCounter.bucket_key == identity["bucket_key"],
            PairCounter.user_id == identity["user_id"],
            PairCounter.target_id == identity["target_id"],
        )
        return (await self.session.scalar(statement)) or 0

    async def _increment_bucket(self, identity: dict[str, str], delta: int) -> int:
        dialect_name = self.session.get_bind().dialect.name
        insert_factory = {
            "postgresql": postgresql_insert,
            "sqlite": sqlite_insert,
        }.get(dialect_name)
        if insert_factory:
            insert_statement = insert_factory(PairCounter).values(**identity, count=delta)
            statement = insert_statement.on_conflict_do_update(
                index_elements=[
                    PairCounter.scene_id,
                    PairCounter.bucket_type,
                    PairCounter.bucket_key,
                    PairCounter.user_id,
                    PairCounter.target_id,
                ],
                set_={"count": PairCounter.count + delta},
            )
            await self.session.execute(statement)
            return await self._get_count(identity)

        # 少数非主流方言保留兼容路径；主仓库默认 SQLite/Postgres 会走原子 upsert。
        statement = (
            update(PairCounter)
            .where(
                PairCounter.scene_id == identity["scene_id"],
                PairCounter.bucket_type == identity["bucket_type"],
                PairCounter.bucket_key == identity["bucket_key"],
                PairCounter.user_id == identity["user_id"],
                PairCounter.target_id == identity["target_id"],
            )
            .values(count=PairCounter.count + delta)
        )
        result = await self.session.execute(statement)
        if result.rowcount:
            return await self._get_count(identity)
        self.session.add(PairCounter(**identity, count=delta))
        await self.session.flush()
        return delta

    async def _decrement_bucket(self, identity: dict[str, str], delta: int) -> int:
        statement = (
            update(PairCounter)
            .where(
                PairCounter.scene_id == identity["scene_id"],
                PairCounter.bucket_type == identity["bucket_type"],
                PairCounter.bucket_key == identity["bucket_key"],
                PairCounter.user_id == identity["user_id"],
                PairCounter.target_id == identity["target_id"],
            )
            .values(count=PairCounter.count + delta)
        )
        result = await self.session.execute(statement)
        if not result.rowcount:
            return 0
        count = await self._get_count(identity)
        if count > 0:
            return count
        await self.session.execute(
            delete(PairCounter).where(
                PairCounter.scene_id == identity["scene_id"],
                PairCounter.bucket_type == identity["bucket_type"],
                PairCounter.bucket_key == identity["bucket_key"],
                PairCounter.user_id == identity["user_id"],
                PairCounter.target_id == identity["target_id"],
            )
        )
        return 0

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
            identity = self._counter_identity(
                scene_id,
                bucket_type,
                bucket_key,
                user_id,
                target_id,
            )
            if delta > 0:
                count = await self._increment_bucket(identity, delta)
            elif delta < 0:
                count = await self._decrement_bucket(identity, delta)
            else:
                count = await self._get_count(identity)
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
