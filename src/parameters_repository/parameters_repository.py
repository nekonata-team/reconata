import logging
from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import List, Mapping, Optional, Union

from pydantic import BaseModel, Field

from src.bot.enums import PromptKey

logger = logging.getLogger(__name__)

WEEKDAY_STR_TO_INT = {
    "mon": 0,
    "tue": 1,
    "wed": 2,
    "thu": 3,
    "fri": 4,
    "sat": 5,
    "sun": 6,
}

ScheduleType = Union["WeeklySchedule", "BiweeklySchedule", "MonthlySchedule"]


def parse_schedule_from_string(line: str) -> ScheduleType | None:
    line = line.strip()
    if line.startswith("weekly,"):
        try:
            _, weekday_str, time_str = [x.strip() for x in line.split(",")]
            weekday = WEEKDAY_STR_TO_INT.get(weekday_str.lower(), None)
            if weekday is None:
                return None
            return WeeklySchedule(weekday=weekday, time=time_str)
        except Exception:
            return None
    if line.startswith("biweekly,"):
        try:
            _, weekday_str, time_str, start_date_str = [
                x.strip() for x in line.split(",")
            ]
            weekday = WEEKDAY_STR_TO_INT.get(weekday_str.lower(), None)
            if weekday is None:
                return None
            return BiweeklySchedule(
                weekday=weekday,
                time=time_str,
                start_date=date.fromisoformat(start_date_str),
            )
        except Exception:
            return None
    if line.startswith("monthly,"):
        try:
            _, day_str, time_str = [x.strip() for x in line.split(",")]
            day = int(day_str)
            return MonthlySchedule(day=day, time=time_str)
        except Exception:
            return None
    return None


class BaseSchedule(BaseModel):
    def should_run(self, now: datetime) -> bool:
        raise NotImplementedError

    def to_string(self) -> str:
        raise NotImplementedError


class WeeklySchedule(BaseSchedule):
    weekday: int = Field(description="曜日（0=月曜, 6=日曜）")
    time: str = Field(description="時刻（例: 20:00, 15:00）")
    model_config = {"frozen": True}

    def should_run(self, now: datetime) -> bool:
        return now.weekday() == self.weekday and now.strftime("%H:%M") == self.time

    def to_string(self) -> str:
        weekday_str = [k for k, v in WEEKDAY_STR_TO_INT.items() if v == self.weekday][0]
        return f"weekly,{weekday_str},{self.time}"


class BiweeklySchedule(BaseSchedule):
    weekday: int = Field(description="曜日（0=月曜, 6=日曜）")
    time: str = Field(description="時刻（例: 20:00, 15:00）")
    start_date: date = Field(description="基準日（YYYY-MM-DD）")
    model_config = {"frozen": True}

    def should_run(self, now: datetime) -> bool:
        if now.weekday() != self.weekday or now.strftime("%H:%M") != self.time:
            return False
        days_since = (now.date() - self.start_date).days
        return days_since % 14 == 0 and days_since >= 0

    def to_string(self) -> str:
        weekday_str = [k for k, v in WEEKDAY_STR_TO_INT.items() if v == self.weekday][0]
        return f"biweekly,{weekday_str},{self.time},{self.start_date.isoformat()}"


class MonthlySchedule(BaseSchedule):
    day: int = Field(description="日（1〜31）")
    time: str = Field(description="時刻（例: 20:00, 15:00）")
    model_config = {"frozen": True}

    def should_run(self, now: datetime) -> bool:
        return now.day == self.day and now.strftime("%H:%M") == self.time

    def to_string(self) -> str:
        return f"monthly,{self.day},{self.time}"


class MeetingSchedule(BaseModel):
    channel_id: int = Field(description="チャンネルID")
    schedule: ScheduleType = Field(description="スケジュール情報")


class GitHub(BaseModel):
    repo_url: str = Field(description="GitHubリポジトリのURL")
    local_repo_path: str = Field(description="GitHubリポジトリのローカルパス")

    model_config = {"frozen": True}


class Parameters(BaseModel):
    prompt_key: Optional[PromptKey] = Field(
        default=None, description="使用するプロンプトのキー"
    )
    user_names: Mapping[str, str] = Field(
        default_factory=dict, description="ユーザー名の辞書"
    )
    additional_context: Optional[str] = Field(
        default=None, description="追加のコンテキスト情報"
    )
    github: Optional[GitHub] = Field(default=None, description="GitHub関連の情報")
    schedules: List[MeetingSchedule] = Field(
        default_factory=list, description="スケジュール情報"
    )

    model_config = {"frozen": True}


class ParametersRepository(ABC):
    @abstractmethod
    def get_parameters(self, guild_id: int) -> Parameters: ...

    @abstractmethod
    def reset_parameters(self, guild_id: int) -> None: ...

    @abstractmethod
    def set_parameters(self, guild_id: int, parameters: Parameters) -> None: ...
