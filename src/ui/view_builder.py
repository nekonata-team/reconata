from abc import ABC, abstractmethod

import discord
from nekomeeta.post_process.github_push import GitHubPusher


class ViewBuilder(ABC):
    @abstractmethod
    def create_view(self) -> discord.ui.View: ...


class CommitViewBuilder(ViewBuilder):
    def __init__(self, pusher: GitHubPusher):
        self.pusher = pusher

    def create_view(self) -> discord.ui.View:
        from .view.commit import CommitView

        return CommitView(pusher=self.pusher)


class EditViewBuilder(ViewBuilder):
    def create_view(self) -> discord.ui.View:
        from .view.edit import EditView

        return EditView()
