from dependency_injector import containers, providers
from dotenv import load_dotenv

from src.bot.enums import PromptKey
from src.parameters_repository.tinydb import TinyDBParametersRepository
from src.summarizer.gemini import GeminiSummarizer
from src.summarizer.prompt_provider.obsidian import (
    ObsidianSummarizePromptProvider,
)
from src.summarizer.prompt_provider.structured_markdown import (
    StructuredMarkdownSummarizePromptProvider,
)
from src.transcriber.faster_whisper import FasterWhisperTranscriber

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
        hotwords=config.hotwords,
    )
    summarizer = providers.Singleton(
        GeminiSummarizer,
        api_key=config.api_key,
        summarize_prompt_provider=prompt_provider,
    )
    parameters_repository = providers.Singleton(TinyDBParametersRepository)


container = Container()
container.config.api_key.from_env("GOOGLE_API_KEY", required=True)
container.config.model_size.from_env("MODEL_SIZE", default="small")
container.config.beam_size.from_env("BEAM_SIZE", default=5, as_=int)
container.config.batch_size.from_env("BATCH_SIZE", default=8, as_=int)
container.config.discord_bot_token.from_env("DISCORD_BOT_TOKEN", required=True)
container.config.log_level.from_env("LOG_LEVEL", default="INFO", as_=str)
container.config.summarize_prompt_key.from_env(
    "SUMMARIZE_PROMPT_KEY", default=PromptKey.DEFAULT
)
