from openai import OpenAI

from .prompt_provider.summarize_prompt_provider import SummarizePromptProvider
from .summarizer import Summarizer


class OpenAISummarizer(Summarizer):
    """OpenAI API を利用して議事録を生成するクラス"""

    def __init__(
        self,
        api_key: str,
        summarize_prompt_provider: SummarizePromptProvider,
        model: str = "gpt-4o",
    ):
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.summarize_prompt_provider = summarize_prompt_provider

    def generate_meeting_notes(self, transcription: str) -> str:
        prompt = self.summarize_prompt_provider.get_prompt(transcription)
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "あなたは優秀な議事録作成者です。"},
                    {"role": "user", "content": prompt},
                ],
            )
            content = response.choices[0].message.content
            if content is None:
                raise RuntimeError("OpenAI API の応答が無効です")
            return content
        except Exception as e:
            raise RuntimeError("OpenAI API を用いた議事録作成に失敗しました") from e
