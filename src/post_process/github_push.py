import os
from datetime import datetime
from logging import getLogger

from git import Actor, Repo

logger = getLogger(__name__)


class GitHubPusher:
    """
    GitPython を用いて pushする
    """

    def __init__(
        self,
        repo_url: str,
        local_repo_path: str = "local",
        commit_message: str | None = None,
        branch: str = "main",
    ):
        self.repo_url = repo_url
        self.local_repo_path = local_repo_path
        self.message = commit_message
        self.branch = branch

    def __call__(
        self,
        transcription: str,
        meeting_notes: str,
        title: str | None = None,
    ):
        repo = self._ensure_repo()

        origin = repo.remotes.origin
        origin.set_url(self.repo_url)

        if repo.is_dirty(untracked_files=True):
            logger.error(
                "Local changes detected. Aborting push to avoid interfering with local modifications."
            )
            return

        logger.info("Pulling latest changes from remote...")
        origin.pull(self.branch)

        title_ = title or datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

        repo_transcription_path = self._save_content(
            transcription, f"minutes/{title_}_transcription.txt"
        )
        repo_meeting_notes_path = self._save_content(
            meeting_notes, f"minutes/{title_}.md"
        )

        repo.index.add(
            [
                repo_transcription_path,
                repo_meeting_notes_path,
            ]
        )

        message = (
            self.message
            or f"vault backup by reconata: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        committer = Actor("noreply", "noreply@reconata.com")
        repo.index.commit(message, author=committer, committer=committer)

        origin.push(self.branch)
        logger.info("Push completed.")

    def _ensure_repo(self):
        # ローカルにリポジトリがなければ clone する
        if not os.path.exists(self.local_repo_path):
            logger.info(
                f"Cloning repository from {self.repo_url} to {self.local_repo_path}..."
            )
            Repo.clone_from(self.repo_url, self.local_repo_path, branch=self.branch)
        else:
            logger.info(f"Local repository found at {self.local_repo_path}")

        return Repo(self.local_repo_path)

    def _save_content(self, content: str, local_repo_file_path: str) -> str:
        """
        contentをローカルリポジトリに保存して、ファイルパスを返す
        """
        full_file_path = os.path.join(self.local_repo_path, local_repo_file_path)

        # 既存ファイルが存在する場合はリネーム
        if os.path.exists(full_file_path):
            base, ext = os.path.splitext(full_file_path)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            full_file_path = f"{base}_{timestamp}{ext}"

        os.makedirs(os.path.dirname(full_file_path), exist_ok=True)

        with open(full_file_path, "w", encoding="utf-8") as f:
            f.write(content)

        return local_repo_file_path
