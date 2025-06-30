from typing import Protocol

import discord
from nekomeeta.post_process.github_push import GitHubPusher


class ViewBuilder(Protocol):
    def create_view(self) -> discord.ui.View: ...


class CommitViewBuilder:
    def __init__(self, pusher: GitHubPusher):
        self.pusher = pusher

    def create_view(self) -> discord.ui.View:
        from view import CommitView

        return CommitView(pusher=self.pusher)


class EditViewBuilder:
    def create_view(self) -> discord.ui.View:
        from view import EditView

        return EditView()
