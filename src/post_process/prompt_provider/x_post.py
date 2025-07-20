from .post_process_prompt_provider import PostProcessPromptProvider


class XPostProcessPromptProvider(PostProcessPromptProvider):
    def get_prompt(self, meeting_notes: str) -> str:
        prompt = f"""以下の議事録をもとに、X（旧Twitter）用の進捗報告ポストを日本語で作成してください。
要点を簡潔に箇条書きでまとめ、最後に関連するハッシュタグを付けてください。

---
議事録:
{meeting_notes}
---
"""
        return prompt
