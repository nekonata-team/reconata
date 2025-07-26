from .summarize_prompt_provider import ContextualSummarizePromptProvider


class ObsidianSummarizePromptProvider(ContextualSummarizePromptProvider):
    """Obsidian 用の議事録フォーマットのプロンプトを提供する具象クラス"""

    def get_system_prompt(self) -> str:
        return "あなたは優秀な議事録作成者です。ユーザーから指定されたフォーマットと文字起こしなどの情報から、マークダウンで議事録を作成してください。議事録以外の内容は出力しないこと。"

    def get_prompt(self, transcription: str) -> str:
        prompt = f"""【フォーマット】
#minute <!-- タグとして機能するため、このまま記載する -->

**日時**:
**参加者**: <!-- 参加者は省略せず記載する -->

## TL;DR
<!-- 簡潔に箇条書きで記載する -->

## 進捗
<!-- 簡潔に箇条書きで記載する -->

## 議題
### 1. xxx
<!-- 話し合った内容を見返しやすいようにまとめる。表を用いても良い -->
### 2. yyy
### ...

## 決まったこと
## 決まらなかったこと

【会議】
{super().get_prompt(transcription)}
"""

        return prompt
