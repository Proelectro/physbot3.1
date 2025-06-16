from datetime import time
import discord
from discord.ext import commands, tasks
from discord import app_commands
import config
import utils
import os
from cogs.base import Base
from typing import Optional
from services.qotd_service import QotdService

Cog = commands.Cog

class Qotd(Base):
    group = app_commands.Group(
        name="qotd",
        description="Manage and interact with the daily Question of the Day system."
    )
    
    def __init__(self, bot: commands.Bot):
        super().__init__(bot)
        self.daily_qotd_loop.start()
        self.qotd_service = QotdService(bot)
        self.log_unimportant = self.bot.get_channel(config.log_unimportant)
        self.log_important = self.bot.get_channel(config.log_important)
        self.log_error = self.bot.get_channel(config.log_error)        

    async def log_event(self, level: str, message: str):
        """Log events to appropriate channels"""
        try:
            if level == "error" and self.log_error:
                await self.log_error.send(f"🚨 **ERROR**: {message}")
            elif level == "important" and self.log_important:
                await self.log_important.send(f"📢 **IMPORTANT**: {message}")
            elif level == "unimportant" and self.log_unimportant:
                await self.log_unimportant.send(f"ℹ️ **INFO**: {message}")
        except Exception as e:
            print(f"Failed to log event: {e.with_traceback()}")

    @Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or isinstance(message.author, discord.Member):
            return
        if "QOTD" in message.content.upper():
            await self.log_event("unimportant", f"QOTD mention detected from {message.author} in {message.channel}")
            try:
                await message.channel.send(
                    "To submit your solution of a QOTD type /qotd submit and click on the command. As shown below.",
                    file=discord.File(os.path.join("images", "submit.png")))
                await message.channel.send(
                    "Then type the number and respective answer to the question you want to submit. As shown below.",
                    file=discord.File(os.path.join("images", "qotd.png")))
                await message.channel.send(
                    "The bot will soon let you know if your answer is correct or incorrect, as shown below.",
                    file=discord.File(os.path.join("images", "verdict.png")))
            except Exception as e:
                await self.log_event("error", f"Failed to send QOTD help: {e.with_traceback()}")

    @tasks.loop(time=time(0, 0))
    async def daily_qotd_loop(self):
        try:
            await self.log_event("unimportant", "Starting daily QOTD task")
            await self.qotd_service.daily_question()
            await self.log_event("unimportant", "Completed daily QOTD task")
        except Exception as e:
            await self.log_event("error", f"Daily QOTD task failed: {e.with_traceback()}")

    @group.command(name="fetch", description="Fetch a QOTD by number.")
    async def fetch(self, interaction: discord.Interaction, num: int):
        await interaction.response.defer(ephemeral=True)
        await self.log_command(caller_name="QOTD Fetch", interaction=interaction, num=num)
        try:
            sc = await self.qotd_service.fetch(interaction.channel, num)
            if sc:
                await interaction.followup.send("Successfully fetched the question of the day.", ephemeral=True)
                await self.log_event("unimportant", f"Fetched QOTD {num} in {interaction.channel.name}")
            else:
                await interaction.followup.send("QOTD not yet done or does not exist.", ephemeral=True)
                await self.log_event("unimportant", f"Failed to fetch QOTD {num} (invalid or pending)")
        except Exception as e:
            await self.log_event("error", f"Fetch command failed: {e.with_traceback()}")
            await interaction.followup.send("An error occurred while fetching the QOTD.", ephemeral=True)

    async def cog_app_command_error(self, interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
        if not isinstance(error, app_commands.CommandOnCooldown):
            error_msg = f"Command error: {error} in command {interaction.command.name} by {interaction.user}"
            await self.log_event("error", error_msg)
            if self.log_error:
                await self.log_error.send(
                    (await self.bot.fetch_user(config.proelectro)).mention,
                    embed=discord.Embed(color=config.red, title=str(interaction.user), description=str(error))
                )

    @group.command(name="solution", description="Get the solution and answer for a specific QOTD.")
    async def solution(self, interaction: discord.Interaction, num: int, link: str = ""):
        await interaction.response.defer()
        await self.log_command(caller_name="QOTD Solution", interaction=interaction, num=num, link=link)
        try:
            result = await self.qotd_service.solution(interaction.user, num, link)
            await interaction.followup.send(result)
            if link:
                await self.log_event("important", f"Solution updated for QOTD {num} by {interaction.user}")
            else:
                await self.log_event("unimportant", f"Solution fetched for QOTD {num} by {interaction.user}")
        except Exception as e:
            await self.log_event("error", f"Solution command failed: {e.with_traceback()}")
            await interaction.followup.send("An error occurred while processing the solution.", ephemeral=True)

    @group.command(name="submit", description="Submit your answer for a QOTD. Only works in DM. Defaults to live qotd.")
    @app_commands.checks.cooldown(1, 30)
    async def submit(self, interaction: discord.Interaction, answer: str, num: Optional[int] = None):
        if interaction.channel.type != discord.ChannelType.private:
            await self.log_event("unimportant", f"Submit attempt in non-DM channel by {interaction.user}")
            await interaction.response.send_message(
                "Cannot submit answers in a server. Please use DMs.", ephemeral=True
            )
            return
        await interaction.response.defer()
        await self.log_command(caller_name="QOTD Submit", interaction=interaction, num=num, answer=answer)
        try:
            await self.qotd_service.submit(interaction, num, answer)
            await self.log_event("unimportant", f"Submission for QOTD {num} by {interaction.user}")
        except Exception as e:
            await self.log_event("error", f"Submit command failed: {e.with_traceback()}")
            await interaction.followup.send("An error occurred while processing your submission.", ephemeral=False)
    
    @submit.error
    async def on_submit_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CommandOnCooldown):
            await self.log_event("unimportant", f"Submit cooldown hit by {interaction.user}")
            await interaction.response.send_message(str(error), ephemeral=True)

    @group.command(name="upload", description="Upload a new QOTD. Only for curators.")
    @app_commands.describe(
        tolerance="In %",
        question_links="Image attachment links. Use newlines for multiple links.",
        points="Deprecated, currently just for compatibility."
    )
    async def upload(self, interaction: discord.Interaction, question_links: str, topic: str, answer: str, difficulty: str, tolerance: str = "1", source: str = "", points: str = ""):
        await interaction.response.defer(ephemeral=True)
        await self.log_command(
            caller_name="QOTD Upload",
            interaction=interaction,
            question_links=question_links,
            topic=topic,
            answer=answer,
            tolerance=tolerance,
            source=source,
            points=points,
            difficulty=difficulty
        )
        try:
            if not all("attachments" in k for k in question_links.splitlines()):
                await self.log_event("unimportant", f"Invalid image links provided by {interaction.user}")
                await interaction.followup.send("Please provide a valid image attachment link. On mobile: use the 'Share' option; on desktop: open the image in a new tab and copy the URL.", ephemeral=True)
                return
            try:
                float(answer)
                float(tolerance)
            except ValueError as e:
                await self.log_event("error", f"QOTD Upload ValueError: {e.with_traceback()}")
                await interaction.followup.send("Invalid answer or tolerance.", ephemeral=True)
                return

            channel = utils.get_text_channel(self.bot, config.qotd_planning)
            if interaction.channel_id in (config.qotd_planning, config.qotd_botspam):
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
                await self.log_event("important", f"QOTD upload initiated by {interaction.user} for topic: {topic}")
            else:
                await self.log_event("unimportant", f"Unauthorized upload attempt by {interaction.user}")
                await interaction.followup.send("You are not authorized to upload a QOTD.", ephemeral=True)
        except Exception as e:
            await self.log_event("error", f"Upload command failed: {e.with_traceback()}")
            await interaction.followup.send("An error occurred during upload.", ephemeral=True)

    @group.command(name="update_leaderboard", description="Update the leaderboard of the current QOTD.")        
    async def update_leaderboard(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self.log_command(caller_name="QOTD Update Leaderboard", interaction=interaction)
        try:
            if self.check_qotd_perms(interaction):
                if await self.qotd_service.update_leaderboard():
                    await interaction.followup.send("Leaderboard updated successfully.", ephemeral=True)
                    await self.log_event("important", f"Leaderboard updated by {interaction.user}")
                else:
                    await interaction.followup.send("No live QOTD.", ephemeral=True)
                    await self.log_event("unimportant", f"Leaderboard update attempted but no live QOTD by {interaction.user}")
            else:
                await self.log_event("unimportant", f"Unauthorized leaderboard update attempt by {interaction.user}")
                await interaction.followup.send("You are not authorized to update the leaderboard. Ask a QOTD Creator.", ephemeral=True)
        except Exception as e:
            await self.log_event("error", f"Leaderboard update failed: {e.with_traceback()}")
            await interaction.followup.send("An error occurred during leaderboard update.", ephemeral=True)

    @group.command(name="status", description="Get your status on the current QOTD. Works only in DMs.")
    @app_commands.checks.cooldown(1, 30)
    async def status(self, interaction: discord.Interaction):
        await self.log_command(caller_name="QOTD Status", interaction=interaction)
        try:
            assert interaction.channel
            if interaction.channel.type == discord.ChannelType.private:
                await interaction.response.defer()
                status = await self.qotd_service.status(interaction.user)
                await interaction.followup.send(status)
                await self.log_event("unimportant", f"Status checked by {interaction.user}")
            else:
                await self.log_event("unimportant", f"Status command in non-DM by {interaction.user}")
                await interaction.response.send_message("This command only works in DMs.", ephemeral=True)
        except Exception as e:
            await self.log_event("error", f"Status command failed: {e.with_traceback()}")
            await interaction.followup.send("An error occurred while fetching your status.", ephemeral=True)

    @group.command(name="merge", description="Restricted to the owner only (proelectro).")
    async def merge(self, interaction: discord.Interaction, num: int, add: bool = True):
        await interaction.response.defer(ephemeral=True)
        await self.log_command(caller_name="QOTD Merge", interaction=interaction, num=num, add=add)
        try:
            if interaction.user.id == config.proelectro:
                await self.qotd_service.merge_leaderboard(num, add)
                await self.log_event("important", f"Leaderboard merged for QOTD {num} by proelectro")
                await interaction.followup.send("Leaderboard merged successfully.", ephemeral=True)
            else:
                await self.log_event("unimportant", f"Unauthorized merge attempt by {interaction.user}")
                await interaction.followup.send("This is proelectro's private command.", ephemeral=True)
        except Exception as e:
            await self.log_event("error", f"Merge command failed: {e.with_traceback()}")
            await interaction.followup.send("An error occurred during merge.", ephemeral=True)

    @group.command(name="cacheclear", description="Restricted to the owner only (proelectro).")
    async def cache_clear(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        await self.log_command(caller_name="Cache Clear", interaction=interaction)
        try:
            if interaction.user.id == config.proelectro:
                self.qotd_service = QotdService(self.bot)
                await self.log_event("important", f"Cleared Cached")
                await interaction.followup.send("Cleared cache successfully.", ephemeral=True)
            else:
                await self.log_event("unimportant", f"Unauthorized clear cache attempt by {interaction.user}")
                await interaction.followup.send("This is proelectro's private command.", ephemeral=True)
        except Exception as e:
            await self.log_event("error", f"Merge command failed: {e.with_traceback()}")
            await interaction.followup.send("An error occurred during merge.", ephemeral=True)

    @group.command(name="remove", description="For QOTD creators. Can remove an upcoming QOTD if it is still pending.")
    async def remove(self, interaction: discord.Interaction, num: int):
        await interaction.response.defer()
        await self.log_command(caller_name="QOTD Remove", interaction=interaction, num=num)
        try:
            if self.check_qotd_perms(interaction):
                sc = await self.qotd_service.delete(qotd_num=num)
                if sc:
                    await interaction.followup.send("Removed QOTD", ephemeral=True)
                    await self.log_event("important", f"QOTD {num} removed by {interaction.user}")
                else:
                    await interaction.followup.send("QOTD number is invalid.", ephemeral=True)
                    await self.log_event("unimportant", f"Failed to remove QOTD {num} by {interaction.user}")
            else:
                await self.log_event("unimportant", f"Unauthorized removal attempt by {interaction.user}")
                await interaction.followup.send("You are not authorized.", ephemeral=True)
        except Exception as e:
            await self.log_event("error", f"Remove command failed: {e.with_traceback()}")
            await interaction.followup.send("An error occurred during removal.", ephemeral=True)

    def check_qotd_perms(self, interaction: discord.Interaction):
        if isinstance(interaction.user, discord.Member):
            return config.qotd_creator in [role.id for role in interaction.user.roles] or config.admin in [role.id for role in interaction.user.roles]
        else:
            return False


async def setup(bot: commands.Bot):
    """Load the QOTD cog."""
    await bot.add_cog(Qotd(bot))