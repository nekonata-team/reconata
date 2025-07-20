from google.genai import Client

from .prompt_provider.summarize_prompt_provider import SummarizePromptProvider
from .summarizer import Summarizer


class GeminiSummarizer(Summarizer):
    """Google Gemini API を利用して議事録を生成するクラス"""

    def __init__(
        self,
        api_key: str,
        summarize_prompt_provider: SummarizePromptProvider,
    ):
        self.client = Client(api_key=api_key)
        self.summarize_prompt_provider = summarize_prompt_provider

    def generate_meeting_notes(self, transcription: str) -> str:
        prompt = self.summarize_prompt_provider.get_prompt(transcription)
        try:
            response = self.client.models.generate_content(
                model="gemini-2.0-flash", contents=prompt
            )
            content = response.text
            if content is None:
                raise RuntimeError("OpenAI API の応答が無効です")
            return content
        except Exception as e:
            raise RuntimeError(
                "Google Gemini API を用いた議事録作成に失敗しました"
            ) from e
