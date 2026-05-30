from datetime import datetime
import discord
from discord.ext import commands
from discord import app_commands
import config
from threading import Thread
from utils.utils import requires_permission, Permission
from logger import Logger

Cog = commands.Cog


class Miscellaneous(Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logger = Logger(bot)

    @app_commands.command()
    @requires_permission(Permission.STAFF)
    async def remove_role(self, interaction: discord.Interaction, role: discord.Role):
        await interaction.response.defer()
        for member in role.members:
            await member.remove_roles(role)
        await interaction.followup.send(f"Removed all members from {role}.")
        return True

    @app_commands.command(
        name="message", description="To message/dm someone through bot"
    )
    @requires_permission(Permission.STAFF)
    async def message(
        self, interaction: discord.Interaction, id: str, text: str, reply: str = None
    ):
        try:
            await interaction.response.defer(ephemeral=True)
            channel = self.bot.get_channel(int(id))
            if not channel:
                channel = await self.bot.fetch_user(int(id))
            if reply:
                msg = await channel.send(
                    text, reference=await channel.fetch_message(int(reply))
                )
            else:
                msg = await channel.send(text)
        except Exception as e:
            await interaction.followup.send(f"An error occurred: {e}")
        else:
            await interaction.followup.send(f"Message sent successfully.")
            return True
            
    @app_commands.command(
        name="edit_message", description="To edit a message sent by the bot"
    )
    @requires_permission(Permission.STAFF)
    async def edit_message(self, interaction: discord.Interaction, channel_id: str, message_id: str, new_content: str):
        await interaction.response.defer(ephemeral=True)
        channel = self.bot.get_channel(int(channel_id))
        if not channel:
            channel = await self.bot.fetch_user(int(channel_id))
        try:
            msg = await channel.fetch_message(int(message_id))
            await msg.edit(content=new_content)
        except Exception as e:
            self.logger.error(f"Failed to edit message {message_id} in channel {channel_id}: {e}")
            return False
        else:
            await interaction.followup.send(f"Message edited successfully.")
            return True
    

    @app_commands.command(name="helper", description="To ping helpers.")
    @app_commands.checks.cooldown(1, 30 * 60)
    @requires_permission(Permission.EVERYONE)
    async def helper(self, interaction: discord.Interaction):
        phods = self.bot.get_guild(config.phods)
        await interaction.response.defer()
        await interaction.followup.send(phods.get_role(config.helper).mention)
        return True

    @app_commands.command(name="resources", description="See resources")
    @requires_permission(Permission.EVERYONE)
    async def resource(self, interaction: discord.Interaction):
        resources = discord.Embed(
            title="Physics Resources",
            colour=config.green,
            description="[A Comprehensive List of Physics Olympiad Resources](https://artofproblemsolving.com/community/c164h2094716_a_comprehensive_list_of_physics_olympiad_resources)\n[Various Textbooks and Solutions](https://discordapp.com/channels/601528888908185655/601884131005169743/707334765673447454)",
        )
        await interaction.response.defer()
        await interaction.followup.send(embed=resources)

    @app_commands.command(name="help", description="To know about the commands.")
    @requires_permission(Permission.EVERYONE)
    async def help(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="Physbot3.0",
            colour=config.green,
            description="A multipurpose bot made for phods.",
        )
        embed.add_field(
            name="Miscellaneous",
            value="/help -> to bring this embed\n/helper -> to ping @helper\n/resources -> to know some resources for physoly.",
            inline=False,
        )
        embed.add_field(
            name="PoTD",
            value="/potd fetch <num> -> Bring the potd of that number\n/potd solution <num> -> Bring the solution of that potd of that number\n/potd submit <num> <attachment> -> to submit your soln of the live potd. (If you want to get on the leaderboard)\n/potd upload -> request your potd to upload.",
            inline=False,
        )
        embed.add_field(
            name="QoTD",
            value="/qotd fetch <num> -> Bring the qotd of that number\n/qotd solution <num> -> Bring the solution of that qotd of that number\n/qotd submit <num> <answer> -> to submit your soln of the live qotd. (If you want to get on the leaderboard)",
            inline=False,
        )
        await interaction.response.defer()
        await interaction.followup.send(embed=embed, ephemeral=True)
        return True

    @helper.error
    async def on_submit_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ):
        if isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.defer()
            await interaction.followup.send(str(error), ephemeral=True)

    async def cog_app_command_error(
        self,
        interaction: discord.Interaction,
        error: discord.app_commands.AppCommandError,
    ):
        await self.bot.get_channel(config.log_error).send(
            (await self.bot.fetch_user(config.proelectro)).mention,
            embed=discord.Embed(
                color=config.red, title=str(interaction.user), description=str(error)
            ),
        )


async def setup(bot):
    await bot.add_cog(Miscellaneous(bot))
