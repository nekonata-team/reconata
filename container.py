from pathlib import Path

from dependency_injector import containers, providers
from dotenv import load_dotenv
from nekomeeta.post_process.github_push import GitHubPusher
from nekomeeta.summarizer.formatter.mdformat import MdFormatSummaryFormatter
from nekomeeta.summarizer.gemini import GeminiSummarizer
from nekomeeta.summarizer.prompt_provider.obsidian import (
    ObsidianSummarizePromptProvider,
)
from nekomeeta.summarizer.prompt_provider.structured_markdown import (
    StructuredMarkdownSummarizePromptProvider,
)
from nekomeeta.transcriber.faster_whisper import FasterWhisperTranscriber

from src.bot.enums import Mode, PromptKey, ViewType
from src.parameters_repository.tinydb import TinyDBParametersRepository
from src.recording_handler.minute import MinuteAudioHandler
from src.recording_handler.save import SaveToFolderRecordingHandler
from src.recording_handler.transcription import TranscriptionAudioHandler
from src.ui.view_builder import CommitViewBuilder, EditViewBuilder

load_dotenv()


class Container(containers.DeclarativeContainer):
    config = providers.Configuration()

    prompt_provider = providers.Selector(
        config.summarize_prompt_key,
        **{
            PromptKey.DEFAULT: providers.Singleton(
                StructuredMarkdownSummarizePromptProvider
            ),
            PromptKey.OBSIDIAN: providers.Singleton(ObsidianSummarizePromptProvider),
        },
    )
    transcriber = providers.Singleton(
        FasterWhisperTranscriber,
        model_size=config.model_size,
        beam_size=config.beam_size,
        batch_size=config.batch_size,
        hotwords="nekonata",
    )
    summarizer = providers.Singleton(
        GeminiSummarizer,
        api_key=config.api_key,
        summarize_prompt_provider=prompt_provider,
    )
    formatter = providers.Singleton(MdFormatSummaryFormatter)
    pusher = providers.Singleton(
        GitHubPusher,
        repo_url=config.repo_url,
        # local_repo_path=Path("./local.dev"),
    )
    view_builder = providers.Selector(
        config.view_type,
        **{
            ViewType.COMMIT: providers.Singleton(
                CommitViewBuilder,
                pusher=pusher,
            ),
            ViewType.EDIT: providers.Singleton(
                EditViewBuilder,
            ),
        },
    )
    audio_handler = providers.Selector(
        config.mode,
        **{
            Mode.MINUTE: providers.Singleton(
                MinuteAudioHandler,
                dir=Path("./data"),
                transcriber=transcriber,
                summarizer=summarizer,
                summarize_prompt_provider=prompt_provider,
                summary_formatter=formatter,
                view_builder=view_builder,
            ),
            Mode.TRANSCRIPTION: providers.Singleton(
                TranscriptionAudioHandler,
                dir=Path("./data"),
                transcriber=transcriber,
            ),
            Mode.SAVE: providers.Singleton(
                SaveToFolderRecordingHandler,
                dir=Path("./data"),
            ),
        },
    )
    parameters_repository = providers.Singleton(TinyDBParametersRepository)


container = Container()
container.config.repo_url.from_env("GITHUB_REPO_URL", required=True)
container.config.api_key.from_env("GOOGLE_API_KEY", required=True)
container.config.model_size.from_env("MODEL_SIZE", default="small")
container.config.beam_size.from_env("BEAM_SIZE", default=5, as_=int)
container.config.batch_size.from_env("BATCH_SIZE", default=8, as_=int)
container.config.discord_bot_token.from_env("DISCORD_BOT_TOKEN", required=True)
container.config.log_level.from_env("LOG_LEVEL", default="INFO", as_=str)
container.config.summarize_prompt_key.from_env(
    "SUMMARIZE_PROMPT_KEY", default=PromptKey.DEFAULT
)
