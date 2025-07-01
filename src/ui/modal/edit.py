import discord


class EditModal(discord.ui.Modal):
    def __init__(self, title: str, initial_value: str) -> None:
        super().__init__(title=title)
        self.content = discord.ui.InputText(
            label="内容",
            style=discord.InputTextStyle.long,
            value=initial_value,
        )
        self.add_item(self.content)

    async def callback(self, interaction: discord.Interaction):
        if (message := interaction.message) is not None:
            embed = message.embeds[0]
            embed.description = self.content.value
            await message.edit(embed=embed)
            await interaction.response.send_message(
                "更新が成功しました。", ephemeral=True
            )
