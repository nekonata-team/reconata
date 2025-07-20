from typing import cast

# 依存関係を外している。再使用する場合は、依存を再追加する必要がある。
from llama_cpp import CreateChatCompletionResponse, Llama

from .prompt_provider.summarize_prompt_provider import SummarizePromptProvider
from .summarizer import Summarizer

# 採用理由
# - GPT 4に匹敵する
# - 日本語対応
# - 8B
# - Llama 3 ベース
_DEFAULT_REPO_ID = "elyza/Llama-3-ELYZA-JP-8B-GGUF"
_DEFAULT_FILENAME = "Llama-3-ELYZA-JP-8B-q4_k_m.gguf"


class LlamaSummarizer(Summarizer):
    """Llama API を利用して議事録を生成するクラス"""

    def __init__(
        self,
        summarize_prompt_provider: SummarizePromptProvider,
        repo_id: str = _DEFAULT_REPO_ID,
        filename: str = _DEFAULT_FILENAME,
    ):
        self.llm = Llama.from_pretrained(
            repo_id=repo_id,
            filename=filename,
            n_gpu_layers=-1,
            n_ctx=0,
        )
        self.summarize_prompt_provider = summarize_prompt_provider

    def generate_meeting_notes(self, transcription: str) -> str:
        prompt = self.summarize_prompt_provider.get_prompt(transcription)
        try:
            response = cast(
                CreateChatCompletionResponse,
                self.llm.create_chat_completion(
                    messages=[
                        {
                            "role": "system",
                            "content": "あなたは優秀な議事録作成者です。",
                        },
                        {"role": "user", "content": prompt},
                    ],
                ),
            )
            content = response["choices"][0]["message"]["content"]
            if content is None:
                raise RuntimeError("Llama API の応答が無効です")
            return content
        except Exception as e:
            raise RuntimeError("Llama API を用いた議事録作成に失敗しました") from e
