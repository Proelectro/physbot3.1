from datetime import time, datetime
import os
from typing import Optional, Union

import discord
from discord.ext import commands, tasks
from discord import app_commands
from discord.app_commands import CommandOnCooldown

import config
import utils.utils as utils
from services.potd_service import PotdService
from logger import Logger
from utils.utils import requires_permission, catch_errors, Permission, PaginatorView
from help_cmds import potd_cmds_everyone, potd_cmds_creator

Cog = commands.Cog

class Potd(Cog):
    group = app_commands.Group(
        name="potd",
        description="Manage and interact with the daily Problem of the Day system.",
    )

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bot.tree.on_error = self.on_app_command_error
        self.logger = Logger(bot)
        self.potd_service = PotdService(bot)
        self.daily_potd_loop.start()

    @tasks.loop(time=time(14, 30))  # 14:30 UTC = 20:00 IST
    @catch_errors
    async def daily_potd_loop(self):
        await self.logger.info("Starting daily POTD task")
        await self.potd_service.daily_problem()
        await self.logger.info("Completed daily POTD task")

    @Cog.listener()
    async def on_app_command_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ):
        if not isinstance(error, CommandOnCooldown):
            admin = await self.bot.fetch_user(config.proelectro)
            await self.logger.log_error.send(
                admin.mention,
                embed=discord.Embed(
                    color=config.red,
                    title=str(interaction.user),
                    description=str(error),
                ),
            )
        else:
            await self.logger.warning(
                f"COOLDOWN TYPE 1: On cooldown for {interaction.user if interaction else 'unknown'}: {error.retry_after:.2f}s"
            )
            await interaction.response.send_message(str(error), ephemeral=True)

    # Commands

    @group.command(name="fetch", description="Fetch a POTD by number.")
    @requires_permission(Permission.EVERYONE)
    async def fetch(self, interaction: discord.Interaction, num: int):
        await interaction.response.defer()
        return await interaction.followup.send("This command is not implemented yet. Please ask Proelectro to implement it.")
        sc = await self.potd_service.fetch(interaction.channel, num)
        if sc:
            await interaction.followup.send(
                "Successfully fetched the problem of the day.", ephemeral=True
            )
        else:
            await interaction.followup.send(
                "POTD not yet done or does not exist.", ephemeral=True
            )
            await self.logger.warning(
                f"Failed to fetch POTD {num} (invalid or pending)"
            )

    @group.command(
        name="solution", description="Get the solution and answer for a specific POTD."
    )
    @requires_permission(Permission.EVERYONE)
    async def solution(self, interaction: discord.Interaction, num: int):
        await interaction.response.defer()
        return await interaction.followup.send("This command is not implemented yet. Please ask Proelectro to implement it.")
        result = await self.potd_service.solution(num)
        await interaction.followup.send(result)

    @group.command(name="add_score", description="To add score for particular problem")
    @requires_permission(Permission.POTD_CREATOR)
    async def add_score(self, interaction: discord.Interaction, num: int, solver: discord.User, points: int, user_id: Optional[int] = None):
        await interaction.response.defer()
        sc = await self.potd_service.add_score(num, solver, points, user_id)
        if sc:
            await interaction.followup.send("Successfully added score for the problem of the day.")
        else:
            await interaction.followup.send("Failed to add score. Please try again later or contact Proelectro if the issue persists.")
            await self.logger.warning(f"Failed to add score for POTD by {interaction.user}")
    
    @group.command(name="update_leaderboard", description="To update the leaderboard of a particular potd.")
    @requires_permission(Permission.POTD_CREATOR)
    async def update_leaderboard(self, interaction: discord.Interaction, num: int):
        await interaction.response.defer()
        sc = await self.potd_service.update_leaderboard(num)
        if sc:
            await interaction.followup.send("Successfully updated the leaderboard for the problem of the day.")
        else:
            await interaction.followup.send("Failed to update the leaderboard. Please try again later or contact Proelectro if the issue persists.")
            await self.logger.warning(f"Failed to update leaderboard for POTD by {interaction.user}")
    


    @group.command(
        name="update_solution", description="Update the solution for a specific POTD."
    )
    @requires_permission(Permission.POTD_CREATOR)
    async def update_solution(
        self, interaction: discord.Interaction, num: int, link: str
    ):
        await interaction.response.defer()
        return await interaction.followup.send("This command is not implemented yet. Please ask Proelectro to implement it.")
        result = await self.potd_service.solution(num, link)
        await interaction.followup.send(result)

    @group.command(
        name="submit",
        description="Submit your answer for a POTD. Only works in DM. Defaults to live potd.",
    )
    @app_commands.checks.cooldown(1, 30)
    @requires_permission(Permission.DM)
    async def submit(
        self, interaction: discord.Interaction, solution: discord.Attachment, num: Optional[int] = None
    ):
        await interaction.response.defer()
        sc, msg = await self.potd_service.submit(interaction, num, solution)
        if sc:
            await interaction.followup.send(msg or "Successfully submitted your answer for the POTD. The staff will review it and get back to you soon!")
        else:
            await interaction.followup.send(
                msg or "Failed to submit your answer. Please try again later or contact the staff if the issue persists."
            )
            await self.logger.warning(
                f"Failed to submit POTD answer for {interaction.user}"
            )
            

    @group.command(name="upload", description="Upload a new POTD. Only for curators.")
    @app_commands.describe(
        problem_links="Image attachment links. Use newlines for multiple links.",
    )
    @requires_permission(Permission.POTD_PLANNING)
    async def upload(
        self,
        interaction: discord.Interaction,
        problem_links: str,
        topic: str,
        answer: str,
        difficulty: str,
        source: str,
        tolerance: str = "1",
        points: str = "",
    ):
        await interaction.response.defer(ephemeral=True)
        return await interaction.followup.send("This command is not implemented yet. Please ask Proelectro to implement it.")
        if not all("attachments" in k for k in problem_links.splitlines()):
            await self.logger.info(
                f"Invalid image links provided by {interaction.user}"
            )
            return await interaction.followup.send(
                "Please provide a valid image attachment link. On mobile: use the 'Share' option; on desktop: open the image in a new tab and copy the URL.",
                ephemeral=True,
            )
        
        channel = utils.get_text_channel(self.bot, config.potd_planning)
        await interaction.followup.send("Processing your query...", ephemeral=True)
        await self.potd_service.upload(
            channel=channel,
            creator=interaction.user.name,
            problem_links=problem_links,
            topic=topic,
            source=source,
            points=points,
            difficulty=difficulty,
        )
        await self.logger.warning(
            f"POTD upload initiated by {interaction.user} for POTD"
        )

    
    @group.command(
        name="clear_cache", description="Restricted to the owner only (proelectro)."
    )
    @requires_permission(Permission.PROELECTRO)
    async def clear_cache(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        new_potd_service = PotdService(self.bot)
        old_potd_service = self.potd_service
        async with new_potd_service.lock:
            self.potd_service = new_potd_service
            await old_potd_service.clear()
        await interaction.followup.send("Cleared cache successfully.", ephemeral=True)
        await self.logger.warning("Cache cleared by proelectro")

    @group.command(name="pending", description="Displays list of pending potd")
    @requires_permission(Permission.POTD_PLANNING)
    async def pending(
        self, interaction: discord.Interaction, num: Optional[int] = None
    ):
        await interaction.response.defer()
        embed = await self.potd_service.pending(interaction.channel, num)
        await interaction.followup.send(embed=embed)

    @group.command(name="random", description="Fetch a random POTD.")
    @requires_permission(Permission.EVERYONE)
    async def random(
        self,
        interaction: discord.Interaction,
        topic: Optional[str] = None,
        curator: Optional[discord.User] = None,
        difficulty: Optional[str] = None,
    ):
        await interaction.response.defer()
        return await interaction.followup.send("This command is not implemented yet. Please ask Proelectro to implement it.")
        sc = await self.potd_service.random(
            interaction.channel, topic, curator, difficulty
        )
        if sc:
            await interaction.followup.send(
                "Successfully fetched a random problem of the day.", ephemeral=True
            )
        else:
            await interaction.followup.send(
                "No random POTD for the given filters is available. Maybe try different filters.",
                ephemeral=True,
            )
            await self.logger.info(
                "Failed to fetch a random POTD (no available problems)"
            )

    @group.command(name="edit", description="Edit a POTD. Only for curators.")
    @requires_permission(Permission.POTD_PLANNING)
    async def edit(
        self,
        interaction: discord.Interaction,
        num: int,
        curator: Optional[discord.User] = None,
        problem: Optional[discord.Attachment] = None,
        topic: Optional[str] = None,
        difficulty: Optional[str] = None,
        source: Optional[str] = None,
        points: Optional[str] = None,
    ):
        await interaction.response.defer()
        rc = await self.potd_service.edit(
            num=num,
            problem=problem,
            curator=curator,
            topic=topic,
            points=points,
            source=source,
            difficulty=difficulty,
        )
        if rc:
            await interaction.followup.send(
                f"POTD #{num} edited successfully.", ephemeral=True
            )
            await self.logger.warning(f"POTD #{num} edited by {interaction.user}")
        else:
            await interaction.followup.send(f"POTD #{num} not found", ephemeral=True)
            await self.logger.warning(f"POTD #{num} edit failed by {interaction.user}")


    @group.command(
        name="help", description="Displays list and description of potd cmds"
    )
    @requires_permission(Permission.EVERYONE)
    async def help(self, interaction: discord.Interaction):
        await interaction.response.defer()
        return await interaction.followup.send("This command is not implemented yet. Please ask Proelectro to implement it.")
        user = interaction.user

        roles = [r.id for r in user.roles] if isinstance(user, discord.Member) else []
        is_creator = config.potd_creator in roles

        # Pick correct command list
        command_list = potd_cmds_creator if is_creator else potd_cmds_everyone
        title = "🏆 Creator Commands" if is_creator else "📋 General POTD Commands"

        # Build pages
        pages = []
        per_page = 5
        for i in range(0, len(command_list), per_page):
            embed = discord.Embed(
                title=title,
                color=discord.Color.blurple(),
                description="Below are the POTD commands. Commands executed in DMs are marked accordingly.",
            )
            chunk = command_list[i : i + per_page]
            for cmd, desc in chunk:
                embed.add_field(name=cmd, value=desc or "No description.", inline=False)
            embed.set_footer(
                text=f"Page {len(pages)+1}/{((len(command_list)+ per_page - 1)/per_page)} • Use commands responsibly!"
            )
            pages.append(embed)

        if len(pages) == 1:
            return await interaction.followup.send(embed=pages[0], ephemeral=True)

        view = PaginatorView(pages, interaction.user)
        await interaction.followup.send(embed=pages[0], view=view, ephemeral=True)
        view.message = await interaction.original_response()


    @group.command(name="check", description="only for proelectro")
    @requires_permission(Permission.PROELECTRO)
    async def check(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self.potd_service.check(interaction.channel)
        await interaction.followup.send("Checked successfully.", ephemeral=True)    



async def setup(bot: commands.Bot):
    """Load the POTD cog."""
    await bot.add_cog(Potd(bot))
