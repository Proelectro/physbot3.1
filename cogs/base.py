import discord
import config
import utils
from discord.ext import commands
from typing import Optional

class Base(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def log_command(
        self, interaction: Optional[discord.Interaction], caller_name: str, **kwargs
    ):
        if interaction:
            embed = discord.Embed(
                title=str(interaction.user), color=config.black, description=caller_name
            )
        else:
            embed = discord.Embed(
                title="Unknown User", color=config.black, description=caller_name
            )
        for k in kwargs:
            embed.add_field(
                name="Name: " + str(k), value="Value: " + str(kwargs[k]), inline=False
            )
        if interaction:
            embed.set_thumbnail(url=interaction.user.display_avatar.url)
            embed.set_footer(
                text=f"UserId: {interaction.user.id} ChannelId: {interaction.channel_id}"
            )
        await utils.get_text_channel(self.bot, config.log_unimportant).send(embed=embed)
