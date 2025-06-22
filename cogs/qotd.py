from datetime import time
import os
import traceback
import functools
from typing import Optional, Union

import discord
from discord.ext import commands, tasks
from discord import app_commands
from discord.app_commands import CommandOnCooldown

import config
import utils.utils as utils
from services.qotd_service import QotdService
from logger import Logger
from utils.utils import Permission

Cog = commands.Cog

def catch_errors(func):
    """Decorator for listeners and loops to catch and log exceptions."""
    @functools.wraps(func)
    async def wrapper(self, *args, **kwargs):
        try:
            return await func(self, *args, **kwargs)
        except Exception as e:
            await self.logger.error(f"{func.__name__} failed: {traceback.format_exc()}", exc=e)
    return wrapper


def valid_permission(level: Permission, user: discord.abc.User, channel: discord.TextChannel) -> tuple[bool,str]:
    match level:
        case Permission.PROELECTRO:
            ok = (user.id == config.proelectro)
            msg = "This command is only for Proelectro"
        case Permission.QOTD_PLANNING:
            ok = (channel.id in (config.qotd_botspam, config.qotd_planning))
            msg = "This command only works in QOTD planning channels i.e. planning and botspam"
        case Permission.QOTD_CREATOR:
            if isinstance(user, discord.Member):
                roles = [r.id for r in user.roles]
                ok = (config.qotd_creator in roles or config.admin in roles)
            else:
                ok = False
            msg = "You must have the QOTD-Creator role to run this command"
        case Permission.DM:
            ok = isinstance(user, discord.User)
            msg = "Please try the command in DM"
        case Permission.EVERYONE:
            ok, msg = True, ""
        case _:
            ok, msg = False, "Invalid permission level"
    return ok, msg

def requires_permission(level: Permission):
    """
    Decorator factory for slash commands:
     1) checks valid_permission
     2) reports ephemerally & returns if not allowed
     3) wraps execution in cooldown+error handling
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(self, interaction: discord.Interaction, *args, **kwargs):
            embed = self.logger.embed_command(interaction.user, interaction.channel, func.__name__, **kwargs)
            ok, err_msg = valid_permission(level, interaction.user, interaction.channel)
            if not ok:
                await self.logger.warning(embed=embed)
                return await interaction.response.send_message(err_msg, ephemeral=True)
    
            try:
                await self.logger.info(embed=embed)
                return await func(self, interaction, *args, **kwargs)

            # except CommandOnCooldown as cd:
            #     # inform user of cooldown
            #     try:
            #         await interaction.response.send_message(str(cd), ephemeral=True)
            #     except:
            #         pass
            #     # log cooldown
            #     await self.logger.info(
            #         f"{func.__name__} on cooldown for {interaction.user}: retry in {cd.retry_after:.1f}s"
            #     )

            except Exception as exc:
                # log unexpected error
                tb = traceback.format_exc()
                await self.logger.error(f"{func.__name__} failed: {tb}", exc=exc)

                # send fallback notification
                try:
                    if interaction.response.is_done():
                        await interaction.followup.send("An unexpected error occurred.", ephemeral=True)
                    else:
                        await interaction.response.send_message("An unexpected error occurred.", ephemeral=True)
                except:
                    pass

        return wrapper
    return decorator



class Qotd(Cog):
    group = app_commands.Group(
        name="qotd",
        description="Manage and interact with the daily Question of the Day system."
    )
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logger = Logger(bot)
        self.qotd_service = QotdService(bot)
        self.daily_qotd_loop.start()
        
    # General

    @Cog.listener()
    @catch_errors
    async def on_message(self, message: discord.Message):
        if message.author.bot or isinstance(message.author, discord.Member):
            return
        if "QOTD" in message.content.upper():
            await self.logger.info(f"QOTD mention detected from {message.author} in {message.channel}")
            await message.channel.send(
                "To submit your solution of a QOTD type /qotd submit and click on the command. As shown below.",
                file=discord.File(os.path.join("images", "submit.png")))
            await message.channel.send(
                "Then type the number and respective answer to the question you want to submit. As shown below.",
                file=discord.File(os.path.join("images", "qotd.png")))
            await message.channel.send(
                "The bot will soon let you know if your answer is correct or incorrect, as shown below.",
                file=discord.File(os.path.join("images", "verdict.png")))

    @tasks.loop(time=time(0, 0))
    @catch_errors
    async def daily_qotd_loop(self):
        await self.logger.info("Starting daily QOTD task")
        await self.qotd_service.daily_question()
        await self.logger.info("Completed daily QOTD task")

    

    @Cog.listener()
    async def app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if not isinstance(error, CommandOnCooldown):
            await self.logger.error(f"Command error: {error} in command {interaction.command.name} by {interaction.user}")
            admin = await self.bot.fetch_user(config.proelectro)
            await self.logger.log_error.send(
                admin.mention,
                embed=discord.Embed(color=config.red, title=str(interaction.user), description=str(error))
            )
        else:
            await self.logger.info(f"On cooldown for {interaction.user if interaction else 'unknown'}: {error.retry_after:.2f}s")
            await interaction.response.send_message(str(error), ephemeral=True)


    # Commands

    @group.command(name="fetch", description="Fetch a QOTD by number.")
    @requires_permission(Permission.EVERYONE)
    async def fetch(self, interaction: discord.Interaction, num: int):
        await interaction.response.defer(ephemeral=True)
        sc = await self.qotd_service.fetch(interaction.channel, num)
        if sc:
            await interaction.followup.send("Successfully fetched the question of the day.", ephemeral=True)
        else:
            await interaction.followup.send("QOTD not yet done or does not exist.", ephemeral=True)
            await self.logger.warning(f"Failed to fetch QOTD {num} (invalid or pending)")


    @group.command(name="solution", description="Get the solution and answer for a specific QOTD.")
    @requires_permission(Permission.EVERYONE)
    async def solution(self, interaction: discord.Interaction, num: int):
        await interaction.response.defer()
        result = await self.qotd_service.solution(num)
        await interaction.followup.send(result)

    @group.command(name="update_solution", description="Update the solution for a specific QOTD.")
    @requires_permission(Permission.QOTD_PLANNING)
    async def update_solution(self, interaction: discord.Interaction, num: int, link: str):
        await interaction.response.defer()
        result = await self.qotd_service.solution(num, link)
        await interaction.followup.send(result)

    @group.command(name="submit", description="Submit your answer for a QOTD. Only works in DM. Defaults to live qotd.")
    @app_commands.checks.cooldown(1, 30)
    @requires_permission(Permission.DM)
    async def submit(self, interaction: discord.Interaction, answer: str, num: Optional[int] = None):
        await interaction.response.defer()
        await self.qotd_service.submit(interaction, num, answer)

    @group.command(name="upload", description="Upload a new QOTD. Only for curators.")
    @app_commands.describe(
        tolerance="In %",
        question_links="Image attachment links. Use newlines for multiple links.",
        points="Deprecated, currently just for compatibility."
    )
    @requires_permission(Permission.QOTD_PLANNING)
    async def upload(self, interaction: discord.Interaction, question_links: str, topic: str, answer: str, difficulty: str, tolerance: str = "1", source: str = "", points: str = ""):
        await interaction.response.defer(ephemeral=True)

        if not all("attachments" in k for k in question_links.splitlines()):
            await self.logger.info(f"Invalid image links provided by {interaction.user}")
            return await interaction.followup.send(
                "Please provide a valid image attachment link. On mobile: use the 'Share' option; on desktop: open the image in a new tab and copy the URL.",
                ephemeral=True
            )
        try:
            float(answer); float(tolerance)
        except ValueError:
            await self.logger.warning(f"QOTD Upload ValueError: invalid answer or tolerance")
            return await interaction.followup.send("Invalid answer or tolerance.", ephemeral=True)

        channel = utils.get_text_channel(self.bot, config.qotd_planning)
        await interaction.followup.send("Processing your query...", ephemeral=True)
        await self.qotd_service.upload(
            channel=channel,
            creator=interaction.user.name,
            question_links=question_links,
            topic=topic,
            answer=answer,
            tolerance=tolerance,
            source=source,
            points=points,
            difficulty=difficulty
        )
        await self.logger.warning(f"QOTD upload initiated by {interaction.user} for QOTD")

    @group.command(name="update_leaderboard", description="Update the leaderboard of the current QOTD.")        
    @requires_permission(Permission.QOTD_CREATOR)
    async def update_leaderboard(self, interaction: discord.Interaction):
        await interaction.response.defer()
        success = await self.qotd_service.update_leaderboard()
        if success:
            await interaction.followup.send("Leaderboard updated successfully.", ephemeral=True)
            await self.logger.warning(f"Leaderboard updated by {interaction.user}")
        else:
            await interaction.followup.send("No live QOTD.", ephemeral=True)
            await self.logger.warning(f"Leaderboard update attempted but no live QOTD by {interaction.user}")

    @group.command(name="status", description="Get your status on the current QOTD. Works only in DMs.")
    @app_commands.checks.cooldown(1, 30)
    @requires_permission(Permission.DM)
    async def status(self, interaction: discord.Interaction):
        await interaction.response.defer()
        status = await self.qotd_service.status(interaction.user)
        await interaction.followup.send(status)
        await self.logger.info(f"Status checked by {interaction.user}")

    @group.command(name="merge", description="Restricted to the owner only (proelectro).")
    @requires_permission(Permission.PROELECTRO)
    async def merge(self, interaction: discord.Interaction, num: int, add: bool = True):
        await interaction.response.defer(ephemeral=True)
        await self.qotd_service.merge_leaderboard(num, add)
        await interaction.followup.send("Leaderboard merged successfully.", ephemeral=True)
        await self.logger.warning(f"Leaderboard merged for QOTD {num} by proelectro")

    @group.command(name="clear_cache", description="Restricted to the owner only (proelectro).")
    @requires_permission(Permission.PROELECTRO)
    async def clear_cache(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        new_qotd_service = QotdService(self.bot)
        old_qotd_service = self.qotd_service
        async with new_qotd_service.lock:
            self.qotd_service = new_qotd_service
            await old_qotd_service.clear()
        await interaction.followup.send("Cleared cache successfully.", ephemeral=True)
        await self.logger.warning("Cache cleared by proelectro")

    @group.command(name="remove", description="For QOTD creators. Can remove an upcoming QOTD if it is still pending.")
    @requires_permission(Permission.QOTD_PLANNING)
    async def remove(self, interaction: discord.Interaction, num: int):
        await interaction.response.defer()
        sc = await self.qotd_service.delete(qotd_num=num)
        if sc:
            await interaction.followup.send("Removed QOTD", ephemeral=True)
            await self.logger.warning(f"QOTD {num} removed by {interaction.user}")
        else:
            await interaction.followup.send("QOTD number is invalid.", ephemeral=True)
            await self.logger.info(f"Failed to remove QOTD {num} by {interaction.user}")


async def setup(bot: commands.Bot):
    """Load the QOTD cog."""
    await bot.add_cog(Qotd(bot))
