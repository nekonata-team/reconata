from abc import ABC, abstractmethod
from datetime import datetime
from zoneinfo import ZoneInfo

from src.parameters_repository.parameters_repository import Parameters

_TZ = ZoneInfo("Asia/Tokyo")


class ContextProvider(ABC):
    @abstractmethod
    def __call__(self, ids: list[int]) -> str:
        pass


class ParametersBaseContextProvider(ContextProvider):
    def __init__(self, parameters: Parameters) -> None:
        self.parameters = parameters

    def __call__(self, ids: list[int]) -> str:
        user_names_map = self.parameters.user_names
        additional_context = self.parameters.additional_context

        participant_names = ",".join(
            [user_names_map.get(str(id), f"<@{id}>") for id in ids]
        )
        today_str = datetime.now(_TZ).strftime("%Y年%m月%d日")
        return f"録音日: {today_str}\n参加者: {participant_names}\n補足: {additional_context or 'なし'}"
