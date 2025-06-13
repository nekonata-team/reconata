from pathlib import Path

from dependency_injector import containers, providers
from dotenv import load_dotenv
from nekomeeta.post_process.github_push import GitHubPushPostProcess
from nekomeeta.summarizer.gemini import GeminiSummarizer
from nekomeeta.summarizer.prompt_provider.formatted_markdown import (
    FormattedMarkdownSummarizePromptProvider,
)
from nekomeeta.transcriber.faster_whisper import FasterWhisperTranscriber

from handler.minute import MinuteAudioHandler, MinuteAudioHandlerFromCLI
from handler.save import SaveToFolderAudioHandler
from handler.transcription import TranscriptionAudioHandler

load_dotenv()


class Container(containers.DeclarativeContainer):
    config = providers.Configuration()

    prompt_provider = providers.Singleton(FormattedMarkdownSummarizePromptProvider)
    transcriber = providers.Singleton(
        FasterWhisperTranscriber,
        model_size=config.model_size,
        beam_size=config.beam_size,
        hotwords="nekoanta",
    )
    summarizer = providers.Singleton(
        GeminiSummarizer,
        api_key=config.api_key,
        summarize_prompt_provider=prompt_provider,
    )
    post_process = providers.Singleton(
        GitHubPushPostProcess,
        repo_url=config.repo_url,
    )
    audio_handler = providers.Selector(
        config.mode,
        minute=providers.Singleton(
            MinuteAudioHandler,
            dir=Path("./data"),
            transcriber=transcriber,
            summarizer=summarizer,
            summarize_prompt_provider=prompt_provider,
            post_process=post_process,
        ),
        transcription=providers.Singleton(
            TranscriptionAudioHandler,
            dir=Path("./data"),
            transcriber=transcriber,
        ),
        save=providers.Singleton(
            SaveToFolderAudioHandler,
            dir=Path("./data"),
        ),
    )
    audio_handler_from_cli = providers.Singleton(
        MinuteAudioHandlerFromCLI,
        dir=Path("./data"),
        transcriber=transcriber,
        summarizer=summarizer,
        summarize_prompt_provider=prompt_provider,
        post_process=post_process,
    )


container = Container()
container.config.repo_url.from_env("GITHUB_REPO_URL", required=True)
container.config.api_key.from_env("GOOGLE_API_KEY", required=True)
container.config.model_size.from_env("MODEL_SIZE", default="small")
container.config.beam_size.from_env("BEAM_SIZE", default=5, as_=int)
container.config.discord_bot_token.from_env("DISCORD_BOT_TOKEN", required=True)
