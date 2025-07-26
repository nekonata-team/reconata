from google.genai import Client
from google.genai.types import GenerateContentConfig

from .prompt_provider.summarize_prompt_provider import SummarizePromptProvider
from .summarizer import Summarizer


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

    def generate_meeting_notes(self, transcription: str) -> str:
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=self.summarize_prompt_provider.get_prompt(transcription),
                config=GenerateContentConfig(
                    system_instruction=self.summarize_prompt_provider.get_system_prompt()
                ),
            )
            content = response.text
            if content is None:
                raise RuntimeError("OpenAI API の応答が無効です")
            return content
        except Exception as e:
            raise RuntimeError(
                "Google Gemini API を用いた議事録作成に失敗しました"
            ) from e
