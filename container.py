from dependency_injector import containers, providers
from dotenv import load_dotenv

from src.bot.enums import PromptKey
from src.parameters_repository.tinydb import TinyDBParametersRepository
from src.summarizer.openai import OpenAISummarizer
from src.summarizer.prompt_provider.obsidian import (
    ObsidianSummarizePromptProvider,
)
from src.summarizer.prompt_provider.structured_markdown import (
    StructuredMarkdownSummarizePromptProvider,
)
from src.transcriber.openai import OpenAIWhisperTranscriber

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
    # transcriber = providers.Singleton(
    #     FasterWhisperTranscriber,
    #     model_size=config.model_size,
    #     beam_size=config.beam_size,
    #     batch_size=config.batch_size,
    # )
    transcriber = providers.Singleton(
        OpenAIWhisperTranscriber,
        api_key=config.openai_api_key,
        model="gpt-4o-mini-transcribe",
    )
    summarizer = providers.Singleton(
        OpenAISummarizer,
        api_key=config.openai_api_key,
        summarize_prompt_provider=prompt_provider,
        model=config.openai_model,
    )
    parameters_repository = providers.Singleton(TinyDBParametersRepository)


container = Container()
container.config.google_api_key.from_env("GOOGLE_API_KEY", required=True)
container.config.openai_api_key.from_env("OPENAI_API_KEY", required=True)
container.config.openai_model.from_env("OPENAI_MODEL", default="gpt-5-nano")
container.config.model_size.from_env("MODEL_SIZE", default="small")
container.config.beam_size.from_env("BEAM_SIZE", default=5, as_=int)
container.config.batch_size.from_env("BATCH_SIZE", default=8, as_=int)
container.config.discord_bot_token.from_env("DISCORD_BOT_TOKEN", required=True)
container.config.log_level.from_env("LOG_LEVEL", default="INFO", as_=str)
container.config.summarize_prompt_key.from_env(
    "SUMMARIZE_PROMPT_KEY", default=PromptKey.DEFAULT
)
