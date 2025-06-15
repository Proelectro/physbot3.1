from datetime import datetime
from random import choice
import discord
from discord.ext import commands
from discord import app_commands
import config
Cog = commands.Cog


class Messages(Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if isinstance(message.author, discord.User):
            await self.handle_dm(message, color = config.green)

    @Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.author.bot:
            return
        if isinstance(before.author, discord.User):
            await self.handle_dm(after,color = config.yellow)

    async def handle_dm(self, message: discord.Message,color):
        embed = discord.Embed(title=str(message.author),
                              color=color, description=message.content)
        embed.set_thumbnail(url=message.author.display_avatar.url)
        for attch in message.attachments:
            embed.add_field(name=attch.filename, value=attch.url, inline=False)
        embed.add_field(name='UserId:',value=str(message.author.id), inline=False)
        embed.add_field(name='MessageId:',value=str(message.id), inline=False)

        await self.bot.get_channel(config.dm_channel).send(embed=embed)

    @app_commands.command(name="message", description="To message/dm someone through bot")
    async def message(self, interaction: discord.Interaction, id: str, text: str, reply: str=None):
        if interaction.user.id not in (config.proelectro, config.dq):
            await interaction.response.send_message(f'This command can only be used by owner of the bot.', ephemeral=True)
        else:
            try:
                channel = self.bot.get_channel(int(id))
                if not channel:
                    channel = await self.bot.fetch_user(int(id))
                if reply:
                    msg = await channel.send(text,reference=await channel.fetch_message(int(reply)))
                else:
                    msg = await channel.send(text)
            except Exception as e:
                await interaction.response.send_message(str(e))
            else:
                embed = discord.Embed(title=str(interaction.user),color=config.blue, description=text)
                embed.set_thumbnail(url=interaction.user.display_avatar.url)
                embed.add_field(name='UserId/ChannelID:',value=str(id),inline=False)
                embed.add_field(name='MessageId:',value=str(msg.id),inline=False)
                await interaction.response.send_message(embed=embed)

    async def cog_app_command_error(self, interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
        await self.bot.get_channel(config.log_important).send((await self.bot.fetch_user(config.proelectro)).mention,embed=discord.Embed(color=config.red,title=str(interaction.user),description=str(error)))

async def setup(bot: commands.Bot):
    await bot.add_cog(Messages(bot))
