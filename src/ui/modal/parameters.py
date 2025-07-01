import discord

from container import container
from src.bot.enums import PromptKey
from src.parameters_repository.parameters_repository import Parameters


class ParametersModal(discord.ui.Modal):
    def __init__(self, title: str, initial_params: Parameters, guild_id: int) -> None:
        super().__init__(title=title)
        self.guild_id = guild_id
        self.initial_params = initial_params

        self.prompt_key_input = discord.ui.InputText(
            label="プロンプトキー",
            placeholder="default, obsidian",
            value=initial_params.prompt_key.value
            if initial_params.prompt_key
            else "default",
            max_length=50,
            required=False,
        )
        self.add_item(self.prompt_key_input)

        self.additional_context_input = discord.ui.InputText(
            label="追加コンテキスト",
            style=discord.InputTextStyle.long,
            placeholder="会議の背景情報や特別な指示を入力してください",
            value=initial_params.additional_context or "",
            max_length=1000,
            required=False,
        )
        self.add_item(self.additional_context_input)

        self.github_repo_url_input = discord.ui.InputText(
            label="GitHub リポジトリURL",
            placeholder="https://github.com/username/repository",
            value=initial_params.github_repo_url or "",
            max_length=200,
            required=False,
        )
        self.add_item(self.github_repo_url_input)

        user_names_str = "\n".join(
            [f"{k}:{v}" for k, v in initial_params.user_names.items()]
        )
        self.user_names_input = discord.ui.InputText(
            label="ユーザー名マッピング",
            style=discord.InputTextStyle.long,
            placeholder="user_id1:表示名1\nuser_id2:表示名2",
            value=user_names_str,
            max_length=1500,
            required=False,
        )
        self.add_item(self.user_names_input)

    async def callback(self, interaction: discord.Interaction):
        try:
            prompt_key_str = (self.prompt_key_input.value or "").strip()
            prompt_key = None
            if prompt_key_str:
                try:
                    prompt_key = PromptKey(prompt_key_str)
                except ValueError:
                    await interaction.response.send_message(
                        f"無効なプロンプトキーです: {prompt_key_str}\n有効な値: {', '.join([pk.value for pk in PromptKey])}",
                        ephemeral=True,
                    )
                    return

            additional_context = (
                self.additional_context_input.value or ""
            ).strip() or None
            github_repo_url = (self.github_repo_url_input.value or "").strip() or None

            user_names = {}
            user_names_text = (self.user_names_input.value or "").strip()
            if user_names_text:
                for line in user_names_text.split("\n"):
                    line = line.strip()
                    if ":" in line:
                        key, value = line.split(":", 1)
                        user_names[key.strip()] = value.strip()

            new_params = Parameters(
                prompt_key=prompt_key,
                additional_context=additional_context,
                github_repo_url=github_repo_url,
                user_names=user_names,
            )

            repository = container.parameters_repository()
            repository.set_parameters(self.guild_id, new_params)

            # 元の表示を更新（リセットと同じ挙動）
            from src.ui.embeds import create_parameters_embed

            embed = create_parameters_embed(self.guild_id)

            # 元のメッセージを更新
            await interaction.response.edit_message(embed=embed)

        except Exception as e:
            embed = discord.Embed(
                title="エラー",
                description=f"パラメータの更新中にエラーが発生しました: {str(e)}",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
