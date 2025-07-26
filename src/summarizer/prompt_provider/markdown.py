from .summarize_prompt_provider import ContextualSummarizePromptProvider


class MarkdownSummarizePromptProvider(ContextualSummarizePromptProvider):
    """Markdown フォーマットのプロンプトを提供する具象クラス"""

    def get_system_prompt(self) -> str:
        return "あなたは優秀な議事録作成者です。マークダウンで議事録を作成してください。議事録以外の内容は出力しないこと。"

    def get_prompt(self, transcription: str) -> str:
        prompt = f"""以下の会話の内容を要約し、Markdownで議事録を作成してください。
{super().get_prompt(transcription)}
        """

        return prompt
