from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from nonebot.adapters import Bot
from nonebot_plugin_uninfo import Interface, Member, SceneType, Uninfo, get_interface

from .config import plugin_config


@dataclass(slots=True)
class CachedMember:
    user_id: str
    name: str
    avatar_url: str | None
    role_id: str | None
    role_level: int


@dataclass(slots=True)
class CachedGroup:
    members: dict[str, CachedMember]
    last_refresh: datetime


class GroupMemberCache:
    def __init__(self):
        self._groups: dict[str, CachedGroup] = {}

    def _ttl(self) -> timedelta:
        return timedelta(seconds=plugin_config.today_waifu_member_cache_ttl_seconds)

    def _to_cached_member(self, member: Member) -> CachedMember:
        name = (
            member.nick
            or member.user.nick
            or member.user.name
            or member.user.id
        )
        return CachedMember(
            user_id=member.user.id,
            name=name,
            avatar_url=member.user.avatar,
            role_id=member.role.id if member.role else None,
            role_level=member.role.level if member.role else 0,
        )

    def update_members(self, scene_id: str, members: list[Member]) -> None:
        self._groups[scene_id] = CachedGroup(
            members={member.user.id: self._to_cached_member(member) for member in members},
            last_refresh=datetime.now(),
        )

    def upsert_member(self, scene_id: str, member: Member) -> None:
        group = self._groups.setdefault(
            scene_id,
            CachedGroup(members={}, last_refresh=datetime.now()),
        )
        group.members[member.user.id] = self._to_cached_member(member)

    def upsert_from_session(self, session: Uninfo) -> None:
        if not session.scene or session.scene.is_private or not session.user:
            return
        group = self._groups.setdefault(
            session.scene.id,
            CachedGroup(members={}, last_refresh=datetime.now()),
        )
        role = session.member.role if session.member else None
        group.members[session.user.id] = CachedMember(
            user_id=session.user.id,
            name=session.member.nick if session.member and session.member.nick else (
                session.user.nick or session.user.name or session.user.id
            ),
            avatar_url=session.user.avatar,
            role_id=role.id if role else None,
            role_level=role.level if role else 0,
        )

    def remove_member(self, scene_id: str, user_id: str) -> None:
        if group := self._groups.get(scene_id):
            group.members.pop(user_id, None)

    def get_member(self, scene_id: str, user_id: str) -> CachedMember | None:
        return self._groups.get(scene_id, CachedGroup({}, datetime.min)).members.get(user_id)

    def get_member_ids(self, scene_id: str) -> set[str]:
        return set(self._groups.get(scene_id, CachedGroup({}, datetime.min)).members.keys())

    def needs_refresh(self, scene_id: str) -> bool:
        group = self._groups.get(scene_id)
        if not group:
            return True
        return datetime.now() - group.last_refresh >= self._ttl()

    async def ensure(self, session: Uninfo, interface: Interface) -> dict[str, CachedMember]:
        if self.needs_refresh(session.scene.id):
            members = await interface.get_members(session.scene.type, session.scene.id)
            self.update_members(session.scene.id, list(members))
        return self._groups[session.scene.id].members

    async def ensure_scene(self, bot: Bot, scene_id: str) -> dict[str, CachedMember]:
        if not self.needs_refresh(scene_id):
            return self._groups[scene_id].members
        return await self.refresh_scene(bot, scene_id)

    async def refresh_scene(self, bot: Bot, scene_id: str) -> dict[str, CachedMember]:
        if not (interface := get_interface(bot)):
            return {}
        members = await interface.get_members(SceneType.GROUP, scene_id)
        self.update_members(scene_id, list(members))
        return self._groups[scene_id].members


member_cache = GroupMemberCache()
