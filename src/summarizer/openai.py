from openai import OpenAI

from .prompt_provider.summarize_prompt_provider import SummarizePromptProvider
from .summarizer import Summarizer, Summary


class OpenAISummarizer(Summarizer):
    """OpenAI API を利用して議事録を生成するクラス"""

    def __init__(
        self,
        api_key: str,
        summarize_prompt_provider: SummarizePromptProvider,
        model: str = "gpt-4.1-nano",
    ):
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.summarize_prompt_provider = summarize_prompt_provider

    def generate_meeting_notes(self, transcription: str) -> Summary:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": self.summarize_prompt_provider.get_system_prompt(),
                },
                {
                    "role": "user",
                    "content": self.summarize_prompt_provider.get_prompt(transcription),
                },
            ],
        )
        content = response.choices[0].message.content
        if content is None:
            raise RuntimeError("コンテンツが返されませんでした")

        usage = response.usage

        input_token_count = usage.prompt_tokens if usage is not None else None
        output_token_count = usage.completion_tokens if usage is not None else None

        return Summary(
            content=content,
            input_token_count=input_token_count or 0,
            output_token_count=output_token_count or 0,
        )
