from .summarize_prompt_provider import ContextualSummarizePromptProvider


class MarkdownSummarizePromptProvider(ContextualSummarizePromptProvider):
    """Markdown フォーマットのプロンプトを提供する具象クラス"""

    def get_prompt(self, transcription: str) -> str:
        prompt = (
            f"以下の会話の内容を要約し、Markdownで議事録を作成してください。"
            f"\n\n{transcription}"
            f"\n\n{self.additional_context}"
            if self.additional_context
            else ""
        )

        return prompt
