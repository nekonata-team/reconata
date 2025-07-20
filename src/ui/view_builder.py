from abc import ABC, abstractmethod

import discord

from .view.commit import PusherBuilder


class ViewBuilder(ABC):
    @abstractmethod
    def create_view(self) -> discord.ui.View: ...


class CommitViewBuilder(ViewBuilder):
    def __init__(self, pusher_builder: PusherBuilder):
        self.pusher_builder = pusher_builder

    def create_view(self) -> discord.ui.View:
        from .view.commit import CommitView

        return CommitView(pusher_builder=self.pusher_builder)


class EditViewBuilder(ViewBuilder):
    def create_view(self) -> discord.ui.View:
        from .view.edit import EditView

        return EditView()
