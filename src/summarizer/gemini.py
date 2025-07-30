from google.genai import Client
from google.genai.types import GenerateContentConfig

from .prompt_provider.summarize_prompt_provider import SummarizePromptProvider
from .summarizer import Summarizer, Summary


class GeminiSummarizer(Summarizer):
    """Google Gemini API を利用して議事録を生成するクラス"""

    def __init__(
        self,
        api_key: str,
        summarize_prompt_provider: SummarizePromptProvider,
        model: str = "gemini-2.0-flash",
    ):
        self.client = Client(api_key=api_key)
        self.summarize_prompt_provider = summarize_prompt_provider
        self.model = model

    def generate_meeting_notes(self, transcription: str) -> Summary:
        response = self.client.models.generate_content(
            model=self.model,
            contents=self.summarize_prompt_provider.get_prompt(transcription),
            config=GenerateContentConfig(
                system_instruction=self.summarize_prompt_provider.get_system_prompt()
            ),
        )
        content = response.text
        if content is None:
            raise RuntimeError("コンテンツが返されませんでした")

        usage = response.usage_metadata

        input_token_count = usage.prompt_token_count if usage is not None else None
        output_token_count = usage.candidates_token_count if usage is not None else None

        return Summary(
            content=content,
            input_token_count=input_token_count or 0,
            output_token_count=output_token_count or 0,
        )
