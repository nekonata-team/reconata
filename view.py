import discord
from post_process.post_process import PostProcess


class CommitView(discord.ui.View):
    def __init__(self, post_process: PostProcess):
        super().__init__(timeout=None)
        self.post_process = post_process

    @discord.ui.button(label="コミット", style=discord.ButtonStyle.primary, emoji="🚀")
    async def commit_button_callback(self, button, interaction: discord.Interaction):
        if (message := interaction.message) is None:
            await interaction.response.send_message(
                "メッセージが見つかりません。", ephemeral=True
            )
            return
        await interaction.response.send_message(
            "コミットを実行しますか？",
            view=ConfirmView(self.post_process, message),
            ephemeral=True,
        )

    @discord.ui.button(label="編集", style=discord.ButtonStyle.danger, emoji="✏️")
    async def edit_button_callback(self, button, interaction: discord.Interaction):
        if (message := interaction.message) is None:
            await interaction.response.send_message(
                "メッセージが見つかりません。", ephemeral=True
            )
            return

        modal = SummaryEditModal(
            title="編集",
            initial_summary=message.embeds[0].description or "",
        )
        await interaction.response.send_modal(modal)


class ConfirmView(discord.ui.View):
    def __init__(
        self,
        post_process: PostProcess,
        target_message: discord.Message,
    ):
        super().__init__()
        self.post_process = post_process
        self.target_message = target_message

    @discord.ui.button(label="はい", style=discord.ButtonStyle.success)
    async def yes_button_callback(self, button, interaction: discord.Interaction):
        await interaction.response.defer()

        message = self.target_message
        if not message.attachments or not message.embeds:
            await interaction.followup.send(
                "添付ファイルまたは埋め込みが見つかりません。", ephemeral=True
            )
            return
        transcription_bytes = await message.attachments[0].read()
        transcription = transcription_bytes.decode("utf-8")
        summary = message.embeds[0].description
        if not transcription or not summary:
            await interaction.followup.send(
                "文字起こしまたは要約が空です。", ephemeral=True
            )
            return
        self.post_process.run(transcription, summary)
        # ボタンを削除
        await message.edit(view=None)
        await interaction.followup.send("コミットが成功しました。", ephemeral=True)
        self.stop()

    @discord.ui.button(label="いいえ", style=discord.ButtonStyle.secondary)
    async def no_button_callback(self, button, interaction: discord.Interaction):
        await interaction.response.send_message("キャンセルしました。", ephemeral=True)
        self.stop()


class SummaryEditModal(discord.ui.Modal):
    def __init__(self, initial_summary: str) -> None:
        super().__init__()
        self.summary = discord.ui.InputText(
            label="内容",
            style=discord.InputTextStyle.long,
            value=initial_summary,
        )
        self.add_item(self.summary)

    async def callback(self, interaction: discord.Interaction):
        if (message := interaction.message) is not None:
            embed = message.embeds[0]
            embed.description = self.summary.value
            await message.edit(embed=embed)
            await interaction.response.send_message(
                "更新が成功しました。", ephemeral=True
            )
