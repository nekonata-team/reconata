from .summarize_prompt_provider import ContextualSummarizePromptProvider


class ObsidianSummarizePromptProvider(ContextualSummarizePromptProvider):
    """Obsidian 用の議事録フォーマットのプロンプトを提供する具象クラス"""

    def get_prompt(self, transcription: str) -> str:
        prompt = (
            f"""以下のフォーマットで、内容を要約し議事録を作成してください。議事録以外の内容は出力しないでください。

#minute

**日時**:
**参加者**:

## TL;DR

## 進捗

## 議題
### 1. xxx
### 2. yyy
### 3. zzz
### ...

## 決まったこと

## 決まらなかったこと
"""
            f"\n\n文字起こし: {transcription}"
            f"\n\n{self.additional_context}"
            if self.additional_context
            else ""
        )

        return prompt
