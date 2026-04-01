from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from enum import Enum


class PairStatus(str, Enum):
    PAIRED = "paired"
    EXHAUSTED = "exhausted"


class ThemeScope(str, Enum):
    GLOBAL = "global"
    GROUP = "group"
    USER = "user"


class ReportBucket(str, Enum):
    ALL = "all"
    WEEK = "week"
    MONTH = "month"
    YEAR = "year"


class SelectMode(str, Enum):
    RANDOM = "random"
    ACTIVE = "active"


THEME_INDEX_TO_KEY = {
    1: "bangdream",
    2: "pjsk",
}
THEME_KEY_TO_INDEX = {value: key for key, value in THEME_INDEX_TO_KEY.items()}
THEME_DISPLAY_NAMES = {
    "bangdream": "BangDream",
    "pjsk": "PJSK",
}

DEFAULT_GLOBAL_THEMES = ["bangdream", "pjsk"]
DIVORCE_EXHAUSTED_TEXT = "你现在没老婆了！渣男"
NO_WAIFU_TEXT = "你今天没老婆了！渣男"
PURE_LOVE_ONLY_TEXT = "这个功能只有纯爱模式才能看。"
REPORT_EMPTY_TEXT = "这一期缘分周刊还是空白，大家今天都挺克制。"

MODE_DISPLAY_NAMES = {
    SelectMode.RANDOM.value: "随机模式",
    SelectMode.ACTIVE.value: "活跃模式",
}

REPORT_TITLES = {
    ReportBucket.WEEK: "缘分周刊",
    ReportBucket.MONTH: "缘分月刊",
    ReportBucket.YEAR: "缘分年刊",
}


@dataclass(slots=True)
class PeriodWindow:
    bucket_type: ReportBucket
    bucket_key: str
    title: str
    start: datetime
    end: datetime


def get_week_bucket_key(value: date) -> str:
    year, week, _ = value.isocalendar()
    return f"{year}-W{week:02d}"


def get_month_bucket_key(value: date) -> str:
    return value.strftime("%Y-%m")


def get_year_bucket_key(value: date) -> str:
    return value.strftime("%Y")


def get_period_window(bucket_type: ReportBucket, moment: datetime) -> PeriodWindow:
    current_date = moment.date()
    if bucket_type == ReportBucket.WEEK:
        start_date = current_date - timedelta(days=current_date.weekday())
        end_date = start_date + timedelta(days=6)
        return PeriodWindow(
            bucket_type=bucket_type,
            bucket_key=get_week_bucket_key(current_date),
            title=REPORT_TITLES[bucket_type],
            start=datetime.combine(start_date, datetime.min.time()),
            end=datetime.combine(end_date, datetime.max.time()),
        )
    if bucket_type == ReportBucket.MONTH:
        start_date = current_date.replace(day=1)
        if current_date.month == 12:
            next_month = current_date.replace(year=current_date.year + 1, month=1, day=1)
        else:
            next_month = current_date.replace(month=current_date.month + 1, day=1)
        end_date = next_month - timedelta(days=1)
        return PeriodWindow(
            bucket_type=bucket_type,
            bucket_key=get_month_bucket_key(current_date),
            title=REPORT_TITLES[bucket_type],
            start=datetime.combine(start_date, datetime.min.time()),
            end=datetime.combine(end_date, datetime.max.time()),
        )
    if bucket_type == ReportBucket.YEAR:
        start_date = current_date.replace(month=1, day=1)
        end_date = current_date.replace(month=12, day=31)
        return PeriodWindow(
            bucket_type=bucket_type,
            bucket_key=get_year_bucket_key(current_date),
            title=REPORT_TITLES[bucket_type],
            start=datetime.combine(start_date, datetime.min.time()),
            end=datetime.combine(end_date, datetime.max.time()),
        )
    raise ValueError(f"unsupported bucket type: {bucket_type}")
