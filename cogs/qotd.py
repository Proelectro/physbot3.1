from datetime import time, datetime
import os
from typing import Optional, Union

import discord
from discord.ext import commands, tasks
from discord import app_commands
from discord.app_commands import CommandOnCooldown

import config
import utils.utils as utils
from services.qotd_service import QotdService
from logger import Logger
from utils.utils import requires_permission, catch_errors, Permission, PaginatorView
from help_cmds import qotd_cmds_creator, qotd_cmds_everyone

Cog = commands.Cog

class Qotd(Cog):
    group = app_commands.Group(
        name="qotd",
        description="Manage and interact with the daily Question of the Day system.",
    )

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bot.tree.on_error = self.on_app_command_error
        self.logger = Logger(bot)
        self.qotd_service = QotdService(bot)
        hour, minute = self.qotd_service.get_time()
        print(f"QOTD posting time is set to {hour}:{minute} UTC")
        self.daily_qotd_loop.change_interval(time=time(hour, minute))
        self.daily_qotd_loop.start()
        print(f"QOTD daily loop started at {hour}:{minute} UTC")
        self.empty_run = datetime.now()
        # self.update_leaderboard_hrs.start()

    # General

    @Cog.listener()
    @catch_errors
    async def on_message(self, message: discord.Message):
        if message.author.bot or isinstance(message.author, discord.Member):
            return
        if "QOTD" in message.content.upper():
            await self.logger.info(
                f"QOTD mention detected from {message.author} in {message.channel}"
            )
            await message.channel.send(
                "To submit your solution of a QOTD type /qotd submit and click on the command. As shown below.",
                file=discord.File(os.path.join("images", "submit.png")),
            )
            await message.channel.send(
                "Then type the answer to the question to submit. As shown below.",
                file=discord.File(os.path.join("images", "qotd.png")),
            )
            await message.channel.send(
                "The bot will soon let you know if your answer is correct or incorrect, as shown below.",
                file=discord.File(os.path.join("images", "verdict.png")),
            )

    # @tasks.loop(hours=1)
    # @catch_errors
    # async def update_leaderboard_hrs(self):
    #     await self.logger.info("Leader board update started")
    #     await self.qotd_service.update_leaderboard()
    #     await self.logger.info("Leader board update completed")

    # @update_leaderboard_hrs.before_loop
    # @catch_errors
    # async def before_hourly_task(self):
    #     await self.bot.wait_until_ready()
    
    @tasks.loop(time=time(0, 0)) 
    @catch_errors
    async def daily_qotd_loop(self):
        await self.logger.info("Starting daily QOTD task")
        await self.qotd_service.daily_question()
        await self.logger.info("Completed daily QOTD task")

    @group.command(name="start", description="To start the qotd season")
    @requires_permission(Permission.QOTD_CREATOR)
    async def start(self, interaction: discord.Interaction):
        await interaction.response.defer()
        if await self.qotd_service.start_season():
            await interaction.followup.send(f"Started the QOTD season successfully. Will post {utils.convert_time_discord_format(*self.qotd_service.get_time())}.")
        else:
            await interaction.followup.send("Qotd season is already live, end it first to start a new one.")

    @group.command(name="change_time", description="To change the posting time of the qotd, optional timezone argument defaults to UTC")
    @requires_permission(Permission.QOTD_CREATOR)
    @app_commands.choices(timezone=[
        # --- North America ---
        app_commands.Choice(name="🇺🇸 US Eastern (EST/EDT)", value="US/Eastern"),
        app_commands.Choice(name="🇺🇸 US Central (CST/CDT)", value="US/Central"),
        app_commands.Choice(name="🇺🇸 US Mountain (MST/MDT)", value="US/Mountain"),
        app_commands.Choice(name="🇺🇸 US Pacific (PST/PDT)", value="US/Pacific"),
        app_commands.Choice(name="🇺🇸 US Alaska (AKST/AKDT)", value="US/Alaska"),
        app_commands.Choice(name="🇺🇸 US Hawaii (HST)", value="US/Hawaii"),
        app_commands.Choice(name="🇨🇦 Canada Toronto (EST/EDT)", value="America/Toronto"),
        app_commands.Choice(name="🇨🇦 Canada Vancouver (PST/PDT)", value="America/Vancouver"),
        app_commands.Choice(name="🇲🇽 Mexico City (CST/CDT)", value="America/Mexico_City"),

        # --- South America ---
        app_commands.Choice(name="🇧🇷 Brazil São Paulo (BRT)", value="America/Sao_Paulo"),

        # --- Europe ---
        app_commands.Choice(name="🇬🇧 UK London (GMT/BST)", value="Europe/London"),
        app_commands.Choice(name="🇪🇺 Central Europe (CET/CEST)", value="Europe/Paris"),
        app_commands.Choice(name="🇪🇺 Eastern Europe (EET/EEST)", value="Europe/Kyiv"),
        app_commands.Choice(name="🇷🇺 Russia Moscow (MSK)", value="Europe/Moscow"),

        # --- Africa & Middle East ---
        app_commands.Choice(name="🇿🇦 South Africa (SAST)", value="Africa/Johannesburg"),
        app_commands.Choice(name="🇦🇪 UAE Dubai (GST)", value="Asia/Dubai"),

        # --- Asia ---
        app_commands.Choice(name="🇮🇳 India Standard Time (IST)", value="Asia/Kolkata"),
        app_commands.Choice(name="🇸🇬 Singapore (SGT)", value="Asia/Singapore"),
        app_commands.Choice(name="🇨🇳 China Beijing (CST)", value="Asia/Shanghai"),
        app_commands.Choice(name="🇯🇵 Japan Tokyo (JST)", value="Asia/Tokyo"),

        # --- Oceania ---
        app_commands.Choice(name="🇦🇺 Australia Sydney (AEST/AEDT)", value="Australia/Sydney"),
        app_commands.Choice(name="🇦🇺 Australia Perth (AWST)", value="Australia/Perth"),
        app_commands.Choice(name="🇳🇿 New Zealand (NZST/NZDT)", value="Pacific/Auckland"),

        # --- Universal ---
        app_commands.Choice(name="🌐 Coordinated Universal Time (UTC)", value="UTC"),
        app_commands.Choice(name="🌐 Greenwich Mean Time (GMT)", value="GMT"),
    ])
    async def change_time(self, interaction: discord.Interaction, hour: int, minute: int, timezone: Optional[str] = "UTC"):
        await interaction.response.defer()
        if hour < 0 or hour > 23 or minute < 0 or minute > 59:
            return await interaction.followup.send("Invalid hour or minute. Hour should be between 0-23 and minute should be between 0-59.")
        utc_hour, utc_minute = await self.qotd_service.change_time(hour, minute, timezone)
        self.daily_qotd_loop.change_interval(time=time(utc_hour, utc_minute))
        self.daily_qotd_loop.restart()
        await interaction.followup.send(f"Successfully changed the posting time of the QOTD. Will post the next QOTD {utils.convert_time_discord_format(utc_hour, utc_minute)}.")


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
            # await self.logger.warning(
            #     f"COOLDOWN TYPE 1: On cooldown for {interaction.user if interaction else 'unknown'}: {error.retry_after:.2f}s"
            # )
            await interaction.response.send_message(str(error), ephemeral=True)

    # Commands

    @group.command(name="fetch", description="Fetch a QOTD by number.")
    @requires_permission(Permission.EVERYONE)
    async def fetch(self, interaction: discord.Interaction, num: int):
        await interaction.response.defer(ephemeral=True)
        sc = await self.qotd_service.fetch(interaction.channel, num)
        if sc:
            await interaction.followup.send(
                "Successfully fetched the question of the day.", ephemeral=True
            )
        else:
            await interaction.followup.send(
                "QOTD not yet done or does not exist.", ephemeral=True
            )
            await self.logger.warning(
                f"Failed to fetch QOTD {num} (invalid or pending)"
            )

    @group.command(
        name="solution", description="Get the solution and answer for a specific QOTD."
    )
    @requires_permission(Permission.EVERYONE)
    async def solution(self, interaction: discord.Interaction, num: int):
        await interaction.response.defer()
        msg, file = await self.qotd_service.solution(num)
        if file:
            await interaction.followup.send(msg, file=file)
        else:
            await interaction.followup.send(msg)

    @group.command(
        name="update_solution", description="Update the solution for a specific QOTD."
    )
    @requires_permission(Permission.QOTD_CREATOR)
    async def update_solution(
        self, interaction: discord.Interaction, num: int, solution: discord.Attachment
    ):
        await interaction.response.defer()
        result, file = await self.qotd_service.solution(num, solution)
        await interaction.followup.send(result)

    @group.command(
        name="submit",
        description="Submit your answer for a QOTD. Only works in DM. Defaults to live qotd.",
    )
    @app_commands.checks.cooldown(1, 30)
    @requires_permission(Permission.DM)
    async def submit(
        self, interaction: discord.Interaction, answer: str, num: Optional[int] = None
    ):
        await interaction.response.defer()
        await self.qotd_service.submit(interaction, num, answer)

    @group.command(name="upload", description="Upload a new QOTD. Only for curators.")
    @app_commands.describe(
        tolerance="In %",
        points="Deprecated, currently just for compatibility.",
    )
    @requires_permission(Permission.QOTD_PLANNING)
    async def upload(
        self,
        interaction: discord.Interaction,
        question: discord.Attachment,
        topic: str,
        answer: str,
        difficulty: str,
        source: str,
        tolerance: str = "1",
        points: str = "",
    ):
        await interaction.response.defer(ephemeral=True)

        try:
            float(answer)
            float(tolerance)
        except ValueError:
            await self.logger.warning(
                f"QOTD Upload ValueError: invalid answer or tolerance"
            )
            return await interaction.followup.send(
                "Invalid answer or tolerance.", ephemeral=True
            )

        channel = utils.get_text_channel(self.bot, config.qotd_planning)
        msg = await interaction.followup.send("Processing your query...", ephemeral=True)
        await self.qotd_service.upload(
            channel=channel,
            creator=interaction.user.name,
            question=question,
            topic=topic,
            answer=answer,
            tolerance=tolerance,
            source=source,
            points=points,
            difficulty=difficulty,
        )
        await self.logger.warning(
            f"QOTD upload initiated by {interaction.user} for QOTD"
        )
        await interaction.followup.edit_message(message_id=msg.id, content="Your QOTD uploaded for review. Thank you!")

    @group.command(
        name="update_leaderboard",
        description="Update the leaderboard of the current QOTD.",
    )
    @requires_permission(Permission.QOTD_CREATOR)
    async def update_leaderboard(self, interaction: discord.Interaction):
        await interaction.response.defer()
        success = await self.qotd_service.update_leaderboard()
        if success:
            await interaction.followup.send(
                "Leaderboard updated successfully.", ephemeral=True
            )
            await self.logger.warning(f"Leaderboard updated by {interaction.user}")
        else:
            await interaction.followup.send("No live QOTD.", ephemeral=True)
            await self.logger.warning(
                f"Leaderboard update attempted but no live QOTD by {interaction.user}"
            )

    @group.command(
        name="clear_cache", description="Restricted to the owner only (proelectro)."
    )
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

    @group.command(name="pending", description="Displays list of pending qotd")
    @requires_permission(Permission.QOTD_PLANNING)
    async def pending(
        self, interaction: discord.Interaction, num: Optional[int] = None
    ):
        await interaction.response.defer()
        embed = await self.qotd_service.pending(interaction.channel, num)
        await interaction.followup.send(embed=embed)

    @group.command(name="random", description="Fetch a random QOTD.")
    @requires_permission(Permission.EVERYONE)
    async def random(
        self,
        interaction: discord.Interaction,
        topic: Optional[str] = None,
        curator: Optional[discord.User] = None,
        difficulty: Optional[str] = None,
    ):
        await interaction.response.defer(ephemeral=True)
        return await interaction.followup.send("This command is not yet implemented. Please ask Proelectro to implement it.")
        sc = await self.qotd_service.random(
            interaction.channel, topic, curator, difficulty
        )
        if sc:
            await interaction.followup.send(
                "Successfully fetched a random question of the day.", ephemeral=True
            )
        else:
            await interaction.followup.send(
                "No random QOTD for the given filters is available. Maybe try different filters.",
                ephemeral=True,
            )
            await self.logger.info(
                "Failed to fetch a random QOTD (no available questions)"
            )

    @group.command(name="edit", description="Edit a QOTD. Only for curators.")
    @requires_permission(Permission.QOTD_PLANNING)
    async def edit(
        self,
        interaction: discord.Interaction,
        num: int,
        curator: Optional[discord.User] = None,
        problem: Optional[discord.Attachment] = None,
        topic: Optional[str] = None,
        answer: Optional[str] = None,
        difficulty: Optional[str] = None,
        source: Optional[str] = None,
        tolerance: Optional[str] = None,
    ):
        await interaction.response.defer()
        try:
            answer and float(answer)
            tolerance and float(tolerance)
        except ValueError:
            await self.logger.warning(
                f"QOTD Edit ValueError: invalid answer or tolerance"
            )
            return await interaction.followup.send(
                "Invalid answer or tolerance. (Should be numeric)", ephemeral=True
            )

        rc = await self.qotd_service.edit(
            num=num,
            problem=problem,
            curator=curator,
            topic=topic,
            answer=answer,
            tolerance=tolerance,
            source=source,
            difficulty=difficulty,
        )
        if rc:
            await interaction.followup.send(
                f"QOTD #{num} edited successfully.", ephemeral=True
            )
            await self.logger.warning(f"QOTD #{num} edited by {interaction.user}")
        else:
            await interaction.followup.send(f"QOTD #{num} not found", ephemeral=True)
            await self.logger.warning(f"QOTD #{num} edit failed by {interaction.user}")

    @group.command(
        name="verify_submission", description="To verify submission of any active qotd"
    )
    @requires_permission(Permission.DM)
    async def verify_submission(self, interaction: discord.Interaction, num: int):
        await interaction.response.defer()
        embed = await self.qotd_service.verify_submissions(interaction.user, num)
        if embed:
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send(
                "Invalid qotd number please choose an active/ live qotd."
            )

    @group.command(
        name="get_submission",
        description="Check the submissions of any active qotd of a user",
    )
    @requires_permission(Permission.QOTD_PLANNING)
    async def get_submission(
        self, interaction: discord.Interaction, participant: discord.User, num: int
    ):
        await interaction.response.defer()
        embed = await self.qotd_service.verify_submissions(participant, num)
        if embed:
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send(
                "Invalid qotd number please choose an active/ live qotd."
            )

    @group.command(
        name="update_submission",
        description="Overwrites the submission of a user for a qotd only for curators",
    )
    @app_commands.describe(submission=", separated values for multiple submissions")
    @requires_permission(Permission.QOTD_PLANNING)
    async def update_submission(
        self,
        interaction: discord.Interaction,
        participant: discord.User,
        num: int,
        submission: str,
    ):
        await interaction.response.defer()
        rc, previous_submissions = await self.qotd_service.update_submission(
            participant, num, submission
        )
        if rc:
            await interaction.followup.send(
                f"Submission updated successfully for {participant.mention} for QOTD #{num}.\nPrevious submissions: {previous_submissions}\nNew submissions: {submission}"
            )
            await self.logger.warning(
                f"Submission of {participant} for QOTD #{num} updated by {interaction.user}"
            )
        else:
            await interaction.followup.send(
                f"Failed to update submission. Invalid QOTD number or submissions are not numeric."
            )
            await self.logger.warning(
                f"Submission update failed for {participant} for QOTD #{num} by {interaction.user}"
            )

    @group.command(
        name="update_offset",
        description="Update the offset score for a user. Only for curators",
    )
    @requires_permission(Permission.QOTD_PLANNING)
    async def update_offset(
        self, interaction: discord.Interaction, participant: discord.User, offset: str
    ):
        await interaction.response.defer()
        try:
            offset_val = float(offset)
        except ValueError:
            return await interaction.followup.send(
                "Invalid offset value. Please provide a numeric value."
            )
        rc, previous_offset = await self.qotd_service.update_offset(
            participant, offset_val
        )
        if rc:
            await interaction.followup.send(
                f"Offset updated successfully for {participant.mention}.\nPrevious offset: {previous_offset}\nNew offset: {offset_val}"
            )
            await self.logger.warning(
                f"Offset of {participant} updated by {interaction.user}"
            )
        else:
            await interaction.followup.send(
                f"Failed to update offset. Unknown error occurred Contact Proelectro."
            )
            await self.logger.warning(
                f"Offset update failed for {participant} by {interaction.user}"
            )

    @group.command(
        name="clear_submissions",
        description="Clear all submissions of a qotd. NOTE THIS ACTION IS IRREVERSIBLE. Only for curators",
    )
    @requires_permission(Permission.QOTD_PLANNING)
    async def clear_submissions(
        self,
        interaction: discord.Interaction,
        qotd_num: int,
        participant: Optional[discord.User] = None,
    ):
        await interaction.response.defer()
        if participant is None:
            self.empty_run = datetime.now()
            await self.logger.warning(
                f"Clear submissions initiated by {interaction.user} for QOTD #{qotd_num}. Awaiting confirmation."
            )
            await interaction.followup.send(
                f"THIS ACTION IS IRREVERSIBLE. If you are sure you want to clear submissions of all users for this qotd, please re-run the command with the user as {self.bot.user.mention}."
            )
        else:
            if participant.id == self.bot.user.id:
                if (datetime.now() - self.empty_run).total_seconds() > 300:
                    return await interaction.followup.send(
                        "The previous clear submissions command has expired. Please re-run the command to initiate again."
                    )
                self.empty_run = datetime.now()
                await self.logger.warning(
                    f"Clear submissions confirmed by {interaction.user} for QOTD #{qotd_num}. Proceeding to clear all submissions."
                )
                participant = None

            if await self.qotd_service.clear_submissions(qotd_num, participant):
                await interaction.followup.send("Submissions cleared successfully.")
            else:
                await interaction.followup.send(
                    "Failed to clear submissions. Invalid QOTD number or user has no submissions."
                )

    @group.command(name="score", description="Detailed transcript of score")
    @requires_permission(Permission.EVERYONE)
    async def score(
        self, interaction: discord.Interaction, solver: discord.User = None
    ):
        await interaction.response.defer()
        solver = solver or interaction.user
        embed = await self.qotd_service.get_scores(solver)
        embeds = [embed]
        if len(embeds) == 1:
            await interaction.followup.send(embed=embeds[0])
        else:
            view = PaginatorView(embeds, interaction.user)
            await interaction.followup.send(embed=embeds[0], view=view)
            view.message = await interaction.original_response()


    @group.command(name="end_season", description="Only for proelectro")
    @requires_permission(Permission.PROELECTRO)
    async def end_season(self, interaction: discord.Interaction):
        await interaction.response.defer()
        msg = await self.qotd_service.end_season()
        await interaction.followup.send(msg)
        await self.logger.warning("Season ended by proelectro")

    @group.command(
        name="help", description="Displays list and description of qotd cmds"
    )
    @requires_permission(Permission.EVERYONE)
    async def help(self, interaction: discord.Interaction):
        await interaction.response.defer()
        user = interaction.user

        roles = [r.id for r in user.roles] if isinstance(user, discord.Member) else []
        is_creator = config.qotd_creator in roles

        # Pick correct command list
        command_list = qotd_cmds_creator if is_creator else qotd_cmds_everyone
        title = "🏆 Creator Commands" if is_creator else "📋 General QOTD Commands"

        # Build pages
        pages = []
        per_page = 5
        for i in range(0, len(command_list), per_page):
            embed = discord.Embed(
                title=title,
                color=discord.Color.blurple(),
                description="Below are the QOTD commands. Commands executed in DMs are marked accordingly.",
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




async def setup(bot: commands.Bot):
    """Load the QOTD cog."""
    await bot.add_cog(Qotd(bot))
