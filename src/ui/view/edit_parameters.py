import discord

from container import container
from src.ui.modal.parameters import ParametersModal


class EditParametersView(discord.ui.View):
    def __init__(self, guild_id: int):
        super().__init__(timeout=None)
        self.guild_id = guild_id

    @discord.ui.button(label="編集", style=discord.ButtonStyle.success, emoji="⚙️")
    async def edit_parameters(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ):
        repository = container.parameters_repository()
        current_params = repository.get_parameters(self.guild_id)

        modal = ParametersModal(
            title="パラメータ編集",
            initial_params=current_params,
            guild_id=self.guild_id,
        )
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="リセット", style=discord.ButtonStyle.danger, emoji="🔄")
    async def reset_parameters(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ):
        repository = container.parameters_repository()
        repository.reset_parameters(self.guild_id)

        from src.ui.embeds import create_parameters_embed
        
        embed = create_parameters_embed(self.guild_id)
        
        await interaction.response.edit_message(embed=embed, view=self)
