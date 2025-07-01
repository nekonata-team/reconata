import discord

from ..modal.edit import EditModal


class EditView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="編集", style=discord.ButtonStyle.primary, emoji="✏️")
    async def edit_button_callback(self, button, interaction: discord.Interaction):
        if (message := interaction.message) is None:
            await interaction.response.send_message(
                "メッセージが見つかりません。", ephemeral=True
            )
            return

        modal = EditModal(
            title="議事録を編集",
            initial_value=message.embeds[0].description or "",
        )
        await interaction.response.send_modal(modal)
