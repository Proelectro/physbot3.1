import discord
import config
import utils.utils as utils
from discord.ext import commands
from typing import Optional
import traceback
from enum import Enum
from dotenv import load_dotenv
import os

class Level(Enum):
    INFO = 0
    WARNING = 1
    ERROR = 2

class Logger:
    def __init__(self, bot: commands.Bot):
        load_dotenv()
        self.bot = bot
        self.debug_logs = os.getenv("DEBUG")
        self.log_unimportant: discord.TextChannel = self.bot.get_channel(config.log_unimportant)
        self.log_important: discord.TextChannel = self.bot.get_channel(config.log_important)
        self.log_error: discord.TextChannel = self.bot.get_channel(config.log_error)
    
    def debug(self, msg: str):
        if self.debug_logs:
            print(msg)

    async def _log_event(self, level: Level, message: str):
        """Log events to appropriate channels"""
        try:
            if level == Level.ERROR and self.log_error:
                await self.log_error.send(f"🚨 **ERROR**: {message}")
            elif level == Level.WARNING and self.log_important:
                await self.log_important.send(f"📢 **IMPORTANT**: {message}")
            elif level == Level.INFO and self.log_unimportant:
                await self.log_unimportant.send(f"ℹ️ **INFO**: {message}")
        except Exception as e:
            print(f"Failed to log event: {traceback.format_exc()}")
            # Optionally send to a fallback channel or console

    async def info(self, message: str):
        """Log an informational message"""
        await self._log_event(Level.INFO, message)

    async def warning(self, message: str):
        """Log a warning message"""
        await self._log_event(Level.WARNING, message)

    async def error(self, message: str, exc: Optional[Exception] = None):
        """Log an error message, optionally including exception traceback"""
        full_message = message
        if exc:
            tb = ''.join(traceback.format_exception(type(exc), exc, exc.__traceback__))
            full_message = f"{message}\n```py\n{tb}\n```"
        await self._log_event(Level.ERROR, full_message)

    def embed_command(
        self,
        user: discord.User,
        channel: discord.TextChannel,
        caller_name: str,
        **kwargs,
    ):
        embed = discord.Embed(
            title=str(user), color=config.black, description=caller_name
        )
        for k, v in kwargs.items():
            embed.add_field(
                name=f"{k}", value=f"{v}", inline=False
            )
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_footer(
            text=f"UserId: {user.id} ChannelId: {channel.id}"
        )
        return embed
