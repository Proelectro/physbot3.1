from datetime import datetime
import discord
from discord.ext import commands
from discord import app_commands
import config
from threading import Thread


Cog = commands.Cog


class Miscellaneous(Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.channel.id == config.voting:
            await message.add_reaction("\U0001f44d")
            await message.add_reaction("🤷‍♂️")
            await message.add_reaction("\U0001f44e")

    @Cog.listener()
    async def on_message_edit(self, before, message: discord.Message):
        if message.channel.id == config.voting:
            await message.add_reaction("\U0001f44d")
            await message.add_reaction("🤷‍♂️")
            await message.add_reaction("\U0001f44e")

    @app_commands.command()
    async def remove_role(self, interaction: discord.Interaction, role: discord.Role):
        await interaction.response.defer()
        if interaction.user.get_role(config.staff):
            for member in role.members:
                await member.remove_roles(role)
            await interaction.followup.send(f"Removed all members from {role}.")
            return True
        else:
            await interaction.followup.send("You don't have permission to use this command.")
            return False

    @app_commands.command(
        name="attachment_link", description="Converts attachment to link."
    )
    async def attachment_link(
        self, interaction: discord.Interaction, attachment: discord.Attachment
    ):
        await interaction.response.defer()
        msg = await interaction.channel.send(file=await attachment.to_file())
        await interaction.followup.send(content=msg.attachments[0].url)
        return False

    @app_commands.command(name="helper", description="To ping helpers.")
    @app_commands.checks.cooldown(1, 30 * 60)
    async def helper(self, interaction: discord.Interaction):
        phods = self.bot.get_guild(config.phods)
        await interaction.response.send_message(phods.get_role(config.helper).mention)
        return True

    @app_commands.command(name="resources", description="See resources")
    async def resource(self, interaction: discord.Interaction):
        resources = discord.Embed(
            title="Physics Resources",
            colour=config.green,
            description="[A Comprehensive List of Physics Olympiad Resources](https://artofproblemsolving.com/community/c164h2094716_a_comprehensive_list_of_physics_olympiad_resources)\n[Various Textbooks and Solutions](https://discordapp.com/channels/601528888908185655/601884131005169743/707334765673447454)",
        )
        await interaction.response.send_message(embed=resources)

    @app_commands.command(name="help", description="To know about the commands.")
    async def help(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="Physbot3.0",
            colour=config.green,
            description="A multipurpose bot made for phods.",
        )
        embed.add_field(
            name="Miscellaneous",
            value="/help -> to bring this embed\n/helper -> to ping @helper\n/resources -> to know some resources for physoly.\n/attachement_link -> Converts attachment into a link.",
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
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return True

    @helper.error
    async def on_submit_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ):
        if isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(str(error), ephemeral=True)

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
