import config
import utils.utils as utils
import asyncio
import discord
from typing import Union, Optional, Tuple, Any, Dict    
from discord.ext import commands
from services.google_sheet_service import GoogleSheetService, LocalSheet
from logger import Logger
import random
import utils.staff_utils as staff_utils



class StaffService:
    def __init__(self, bot: commands.Bot) -> None:
        """Initialize the StaffService with a bot instance."""
        self.logger = Logger(bot)
        self.gss: GoogleSheetService = GoogleSheetService("STAFF")
        self.bot: commands.Bot = bot
        self.lock: asyncio.Lock = asyncio.Lock()
        self.monitored_cache: Optional[Dict[discord.TextChannel, discord.TextChannel]] = None
        self.reverse_monitored_cache: Optional[Dict[discord.TextChannel, discord.TextChannel]] = None
        self.message_cache: Dict[int, discord.Message] = {}
    
    async def on_message(self, message: discord.Message) -> None:
        async with self.lock:
            if message.author.bot:
                return
            await self._load_cache()
            if message.channel in self.monitored_cache:
                logging_channel = self.monitored_cache[message.channel]
                embed = staff_utils.send_message_embed(message, discord.colour.Color.green())
                await logging_channel.send(embed=embed)
                
            elif message.channel in self.reverse_monitored_cache:
                original_channel = self.reverse_monitored_cache[message.channel]
                msg = await original_channel.send(message.content)
                self.message_cache[message.id] = msg
        
    async def on_delete_message(self, message: discord.Message) -> None:
        async with self.lock:
            if message.author.bot:
                return
            await self._load_cache()
            if message.channel in self.monitored_cache:
                logging_channel = self.monitored_cache[message.channel]
                embed = staff_utils.send_message_embed(message, discord.colour.Color.red())
                await logging_channel.send(embed=embed)
                
            elif message.channel in self.reverse_monitored_cache:
                if message.id in self.message_cache:
                    try:
                        msg = self.message_cache[message.id]
                        await msg.delete()
                        del self.message_cache[message.id]
                    except Exception as e:
                        self.logger.error(f"Error deleting message in original channel: {e}")
    
    async def on_message_edit(self, before: discord.Message, after: discord.Message) -> None:
        async with self.lock:
            if before.author.bot:
                return
            await self._load_cache()
            if before.channel in self.monitored_cache:
                logging_channel = self.monitored_cache[before.channel]
                embed = staff_utils.send_message_embed(after, discord.colour.Color.yellow(), before=before)
                await logging_channel.send(embed=embed)
                
            elif before.channel in self.reverse_monitored_cache:
                if before.id in self.message_cache:
                    try:
                        msg = self.message_cache[before.id]
                        await msg.edit(content=after.content)
                        self.message_cache[after.id] = msg
                    except Exception as e:
                        self.logger.error(f"Error editing message in original channel: {e}")
                else:
                    original_channel = self.reverse_monitored_cache[before.channel]
                    msg = await original_channel.send(after.content)
                    self.message_cache[after.id] = msg
                
                    
    async def clear(self):
        while self.lock.locked():
            await asyncio.sleep(0.1)
        await self.lock.acquire()

    async def monitor(self, channel: Optional[discord.TextChannel], user: Optional[discord.User]) -> str:
        """Monitor or unmonitor a channel for a user."""
        async with self.lock:
            await self._load_cache()
            if not channel and not user:
                return staff_utils.list_monitored(self.monitored_cache)
            try:
                dm_channel = user and await user.create_dm()
            except Exception as e:
                return f"Failed to create DM channel with user {user}: {e}"
            msg = ""
            for mon_channel in [channel, dm_channel]:
                if not mon_channel:
                    continue
                if mon_channel in self.monitored_cache:
                    try:
                        await self.monitored_cache[mon_channel].delete()
                    except Exception as e:
                        self.logger.warning(f"Error deleting logging channel for {mon_channel}: {e}")
                    
                    del self.reverse_monitored_cache[self.monitored_cache[mon_channel]]
                    del self.monitored_cache[mon_channel]
                    msg += f"Stopped monitoring channel {mon_channel}.\n"
                else:
                    phods = self.bot.get_guild(config.phods)
                    category = phods.get_channel(config.category)
                    logging_channel = await phods.create_text_channel(
                        name=f"view-{mon_channel}", category=category,
                    )
                    self.monitored_cache[mon_channel] = logging_channel
                    self.reverse_monitored_cache[logging_channel] = mon_channel
                    await self.logger.info(f"Started monitoring channel {mon_channel} with key {logging_channel.id}.")
                    msg += f"Now monitoring channel {mon_channel}.\n"
                    
            staff_utils.save_cache(self.monitored_cache, self.gss["monitoring"])
            return msg

    async def _load_cache(self) -> None:
        if self.monitored_cache is not None:
            return
        self.monitored_cache = {}
        self.reverse_monitored_cache = {}
        data = self.gss["monitoring"].get_data()
        for row in data:
            if len(row) < 2:
                continue
            channel_id, key = row[0], row[1]
            channel = self.bot.get_channel(int(channel_id))
            logging_channel = self.bot.get_channel(int(key))
            if not logging_channel:
                try:
                    logging_channel = await self.bot.fetch_channel(int(key))
                except Exception as e:
                    self.logger.error(f"Error fetching logging channel {key}: {e}")
                    continue
            if not channel:
                try:
                    channel = await self.bot.fetch_channel(int(channel_id))
                except Exception as e:
                    self.logger.error(f"Error fetching channel {channel_id}: {e}")
                    continue
            self.monitored_cache[channel] = logging_channel
            self.reverse_monitored_cache[logging_channel] = channel