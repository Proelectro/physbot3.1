from copy import error
import functools
import random
import traceback
from datetime import time as dtime, timedelta, datetime
import os
import enum
from time import time
from typing import Optional, Union
import subprocess

import discord
from discord.ext import commands
from discord.app_commands import CommandOnCooldown

import config
from logger import Logger

ChannelType = Union[
    discord.VoiceChannel,
    discord.StageChannel,
    discord.ForumChannel,
    discord.TextChannel,
    discord.CategoryChannel,
    discord.Thread,
    discord.abc.PrivateChannel,
    None,
]


# qotd, potd common utilities
async def check_toggle_state(channel: ChannelType, toggle_message_id: int) -> bool:
    """Check if the toggle message is in the correct state.
    Returns True if the toggle is enabled (i.e., does not contain "101"), False otherwise.
    """
    if not isinstance(channel, discord.TextChannel):
        raise ValueError("The channel must be a TextChannel to check toggle state.")
    try:
        msg = await channel.fetch_message(toggle_message_id)
        return "101" not in msg.content
    except discord.NotFound:
        return False


async def post_question(
    channel: ChannelType,
    num: str,
    date: str,
    day: str,
    file_path: str,
    creator: str,
    pqotd: str,
    source: Optional[str] = None,
    points: Optional[int] = None,
    difficulty: Optional[str] = None,
    topic: Optional[str] = None,
    answer: Optional[str] = None,
    tolerance: str = "0.01",
    announce: bool = False,
) -> None:
    """Post a formatted question of the day message to the specified channel."""
    post = f"**{pqotd} {num}**\n**{date}, {day}**"
    post2 = f"{pqotd} Creator: **{creator}**\n"
    post3 = f"Source: ||{source}||\n" if source else ""
    post4 = f"Points: {points}\n" if points else ""
    post5 = f"Difficulty: {difficulty}\n" if difficulty else ""
    post6 = f"Category: {topic}\n" if topic else ""
    post7 = f"Answer: {answer} Tolerance: {tolerance}" if answer is not None else ""

    msg1 = await channel.send(post, file=discord.File(file_path))  # type: ignore
    msg2 = await channel.send(post2 + post3 + post4 + post5 + post6 + post7)  # type: ignore
    try:
        if announce:
            await msg1.publish()
            await msg2.publish()
    except Exception as e:
        # If the channel is not a forum channel, publishing will fail. We can ignore this error.
        pass



async def remove_roles(role: discord.Role) -> None:
    """Removes a specific role from all members in the guild.
    Args:
        role (discord.Role): The role to be removed from all members.
    """
    for member in role.members:
        await member.remove_roles(role)


# general utilities

class Permission(enum.Enum):
    PROELECTRO = 0
    STAFF = 1
    QOTD_PLANNING = 2
    QOTD_CREATOR = 3
    POTD_PLANNING = 4
    POTD_CREATOR = 5
    DM = 6
    EVERYONE = 7

async def send_long_message(channel: discord.TextChannel, message: str) -> None:
    """Send a long message to a Discord channel, splitting it into multiple messages if necessary."""
    max_length = 2000  # Discord's message character limit
    if len(message) <= max_length:
        await channel.send(message)
    else:
        parts = [
            message[i : i + max_length] for i in range(0, len(message), max_length)
        ]
        for part in parts:
            await channel.send(part)

def catch_errors(func):
    """Decorator for listeners and loops to catch and log exceptions."""

    @functools.wraps(func)
    async def wrapper(self, *args, **kwargs):
        try:
            return await func(self, *args, **kwargs)
        except Exception as e:
            await self.logger.error(
                f"{func.__name__} failed: {traceback.format_exc()}", exc=e
            )

    return wrapper


def valid_permission(
    level: Permission, user: discord.abc.User, channel: discord.TextChannel
) -> tuple[bool, str]:
    if level == Permission.PROELECTRO:
        ok = user.id == config.proelectro
        msg = "This command is only for Proelectro"
    elif level == Permission.STAFF:
        if isinstance(user, discord.Member):
            roles = [r.id for r in user.roles]
            ok = (config.staff in roles) or (user.id == config.proelectro)
        else:
            ok = False
        msg = "You must have the Staff role to run this command"
    elif level == Permission.QOTD_PLANNING:
        ok = (
            channel.id in (config.qotd_botspam, config.qotd_planning)
            or user.id == config.proelectro
        )
        msg = "This command only works in QOTD planning channels i.e. planning and botspam"
    elif level == Permission.QOTD_CREATOR:
        if isinstance(user, discord.Member):
            roles = [r.id for r in user.roles]
            ok = (
                (config.qotd_creator in roles)
                or (channel.id in (config.qotd_botspam, config.qotd_planning))
                or (user.id == config.proelectro)
            )
        else:
            ok = False
        msg = "You must have the QOTD-Creator role to run this command"
    elif level == Permission.POTD_CREATOR:
        if isinstance(user, discord.Member):
            roles = [r.id for r in user.roles]
            ok = (
                (config.potd_creator in roles)
                or (channel.id in (config.potd_botspam, config.potd_planning))
                or (user.id == config.proelectro)
            )
        else:
            ok = False
        msg = "You must have the POTD-Creator role to run this command"
    elif level == Permission.POTD_PLANNING:
        ok = (
            channel.id in (config.potd_botspam, config.potd_planning)
            or user.id == config.proelectro
        )
        msg = "This command only works in POTD planning channels i.e. planning and botspam"
    elif level == Permission.DM:
        ok = isinstance(user, discord.User)
        msg = "Please try the command in DM"
    elif level == Permission.EVERYONE:
        ok, msg = True, ""
    else:
        ok, msg = False, "Invalid permission level"

    return ok, msg


class PaginatorView(discord.ui.View):
    def __init__(self, pages, user):
        super().__init__(timeout=60)
        self.pages = pages
        self.current_page = 0
        self.user = user
        self.update_buttons()

    def update_buttons(self):
        self.first_page.disabled = self.prev_page.disabled = self.current_page == 0
        self.last_page.disabled = self.next_page.disabled = (
            self.current_page == len(self.pages) - 1
        )
        self.page_counter.label = f"{self.current_page+1}/{len(self.pages)}"

    @discord.ui.button(emoji="⏮", style=discord.ButtonStyle.blurple)
    async def first_page(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.current_page = 0
        self.update_buttons()
        await interaction.response.edit_message(
            embed=self.pages[self.current_page], view=self
        )

    @discord.ui.button(emoji="◀", style=discord.ButtonStyle.blurple)
    async def prev_page(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.current_page -= 1
        self.update_buttons()
        await interaction.response.edit_message(
            embed=self.pages[self.current_page], view=self
        )

    @discord.ui.button(label="1/1", style=discord.ButtonStyle.gray, disabled=True)
    async def page_counter(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        pass

    @discord.ui.button(emoji="▶", style=discord.ButtonStyle.blurple)
    async def next_page(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.current_page += 1
        self.update_buttons()
        await interaction.response.edit_message(
            embed=self.pages[self.current_page], view=self
        )

    @discord.ui.button(emoji="⏭", style=discord.ButtonStyle.blurple)
    async def last_page(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.current_page = len(self.pages) - 1
        self.update_buttons()
        await interaction.response.edit_message(
            embed=self.pages[self.current_page], view=self
        )

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        try:
            await self.message.edit(view=self)
        except discord.NotFound:
            pass

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.user:
            await interaction.response.send_message(
                "❌ This paginator is not for you!", ephemeral=True
            )
            return False
        return True


def requires_permission(level: Permission):
    """
    Decorator factory for slash commands:
     1) checks valid_permission
     2) reports ephemerally & returns if not allowed
     3) wraps execution in cooldown+error handling
    """

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(
            self, interaction: discord.Interaction, *args, **kwargs
        ):
            embed = self.logger.embed_command(
                interaction.user, interaction.channel, func.__name__, **kwargs
            )
            ok, err_msg = valid_permission(level, interaction.user, interaction.channel)
            if not ok:
                await self.logger.warning(embed=embed)
                return await interaction.response.send_message(err_msg, ephemeral=True)

            try:
                await self.logger.info(embed=embed)
                return await func(self, interaction, *args, **kwargs)

            except CommandOnCooldown as cd:
                await self.logger.warning(
                    f"THIS SHOULD NEVER HAPPEN: {func.__name__} on cooldown for {interaction.user}: retry in {cd.retry_after:.1f}s"
                )
                # inform user of cooldown
                try:
                    await interaction.response.send_message(str(cd), ephemeral=True)
                except:
                    pass
                # log cooldown
                await self.logger.warning(
                    f"COOLDOWN TYPE 2: On cooldown for {interaction.user if interaction else 'unknown'}: {cd.retry_after:.2f}s"
                )
                await self.logger.info(
                    f"{func.__name__} on cooldown for {interaction.user}: retry in {cd.retry_after:.1f}s"
                )

            except Exception as exc:
                # log unexpected error
                tb = traceback.format_exc()
                await self.logger.error(f"{func.__name__} failed: {tb}", exc=exc)

                # send fallback notification
                try:
                    if interaction.response.is_done():
                        await interaction.followup.send(
                            "An unexpected error occurred.", ephemeral=True
                        )
                    else:
                        await interaction.response.send_message(
                            "An unexpected error occurred.", ephemeral=True
                        )
                except:
                    pass

        return wrapper

    return decorator

IST_OFFSET = timedelta(hours=5, minutes=30)

def from_ist_to_utc(hour: int, minute: int) -> tuple[int, int]:
    ist_time = datetime.combine(datetime.today(), dtime(hour, minute))
    utc_time = ist_time - IST_OFFSET
    return utc_time.hour, utc_time.minute


def get_date() -> str:
    """Get the current date in the format 'dd Mon yyyy'."""
    return datetime.now().strftime("%d %b %Y").title()


def get_day() -> str:
    """Get the current day of the week."""
    return datetime.now().strftime("%A").title()


def get_time() -> str:
    """Get the current time in the 12-hour format. [HH:MM AM/PM UTC]"""
    return f"<t:{int(time())}:t>"


def get_text_channel(bot: commands.Bot, channel_id: int) -> discord.TextChannel:
    channel = bot.get_channel(channel_id)
    return channel  # type: ignore

async def upload_image(cwd: str, num: int, problem: discord.Attachment, logger: Logger) -> str:
    subprocess.run(["git", "checkout", "main"], cwd=cwd, check=True)
    pull_result = subprocess.run(["git", "pull"], cwd=cwd, check=True, capture_output=True, text=True)
    # check for merge conflicts
    if "CONFLICT" in pull_result.stdout or "CONFLICT" in pull_result.stderr:
        await logger.error("Merge conflict detected during git pull")
        raise Exception("Merge conflict detected. Please resolve manually.")
    if pull_result.returncode != 0:
        await logger.error(f"Git pull failed: {pull_result.stderr}")
        raise Exception("Failed to pull latest changes from GitHub.")
    
    image_path = os.path.join(cwd, f"{problem.filename}")
    # check if file already exists
    cnt = 1
    while os.path.exists(image_path):
        file_name, ext = os.path.splitext(problem.filename)
        image_path = os.path.join(cwd, f"{file_name} ({cnt}){ext}")
        cnt += 1

    await problem.save(image_path)
    
    subprocess.run(["git", "add", "."], cwd=cwd, check=True)
    
    commit_result = subprocess.run(
        ["git", "commit", "-m", f"Added image {image_path} for {num}"], 
        cwd=cwd, 
        capture_output=True, 
        text=True
    )
    await logger.info(f"Git commit output: {commit_result.stdout}")
    if commit_result.returncode != 0:
        await logger.error(f"Git commit failed: {commit_result.stderr}")
        raise Exception("Failed to commit changes to GitHub.")
    
    subprocess.run(["git", "push"], cwd=cwd, check=True)
    await logger.info("Image successfully pushed to GitHub!")
    
    
    return image_path

