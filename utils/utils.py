import discord
import config
from functools import wraps
from typing import Optional, Union
from datetime import datetime
from discord.ext import commands
from enum import Enum
from time import time

ChannelType = Union[discord.VoiceChannel, discord.StageChannel, discord.ForumChannel, discord.TextChannel, discord.CategoryChannel, discord.Thread, discord.abc.PrivateChannel, None]

# qotd, potd common utilities
async def check_toggle_state(channel: ChannelType, toggle_message_id: int) -> bool:
    """Check if the toggle message is in the correct state.
        Returns True if the toggle is enabled (i.e., does not contain "101"), False otherwise."""
    if not isinstance(channel, discord.TextChannel):
        raise ValueError("The channel must be a TextChannel to check toggle state.")
    try:
        msg = await channel.fetch_message(toggle_message_id)
        return "101" not in msg.content
    except discord.NotFound:
        return False
    
async def post_question(channel: ChannelType, num: str, date: str, day: str,
                        links: str, creator: str, source: Optional[str] = None, points: Optional[int] = None,
                        difficulty: Optional[str] = None, topic: Optional[str] = None,
                        answer: Optional[str] = None, tolerance: str = "0.01",
                        announce: bool = False) -> None:
    """Post a formatted question of the day message to the specified channel."""
    post = f'**QOTD {num}**\n**{date}, {day}**\n{links}'
    post2 = f'QOTD Creator: **{creator}**\n'
    post3 = f'Source: ||{source}||\n' if source is not None else ""
    post4 = f'Points: {points}\n' if points is not None else ""
    post5 = f'Difficulty: {difficulty}\n' if  difficulty is not None else ""
    post6 = f'Category: {topic}\n'if topic is not None else ""
    post7 = f'Answer: {answer} Tolerance: {tolerance}' if answer is not None else ""
    
    msg1 = await channel.send(post) # type: ignore
    msg2 = await channel.send(post2 + post3 + post4 + post5 + post6 + post7) # type: ignore
    if announce:
        await msg1.publish()
        await msg2.publish()

async def remove_roles(role: discord.Role) -> None:
    """Removes a specific role from all members in the guild.
    Args:
        role (discord.Role): The role to be removed from all members.
    """
    for member in role.members:
        await member.remove_roles(role)

# general utilities

async def send_long_message(channel: discord.TextChannel, message: str) -> None:
    """Send a long message to a Discord channel, splitting it into multiple messages if necessary."""
    max_length = 2000  # Discord's message character limit
    if len(message) <= max_length:
        await channel.send(message)
    else:
        parts = [message[i:i + max_length] for i in range(0, len(message), max_length)]
        for part in parts:
            await channel.send(part)

class Permission(Enum):
    PROELECTRO = 0
    QOTD_PLANNING = 1
    QOTD_CREATOR = 2
    DM = 3
    EVERYONE = 4
    
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
    return channel # type: ignore
    
