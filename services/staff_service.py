import config
import utils.utils as utils
import asyncio
import discord
from typing import Union, Optional, Tuple, Any, Dict    
from discord.ext import commands
from services.google_sheet_service import GoogleSheetService, LocalSheet
from logger import Logger
import random
from datetime import datetime, timedelta
import utils.staff_utils as staff_utils



class StaffService:
    def __init__(self, bot: commands.Bot) -> None:
        """Initialize the StaffService with a bot instance."""
        self.logger = Logger(bot)
        self.bot: commands.Bot = bot
        self.lock: asyncio.Lock = asyncio.Lock()
        self.message_cache: Dict[int, int] = {}
        self.physbot_dm_forum_id = config.physbot_dm_forum
    
    async def on_message(self, message: discord.Message) -> None:
        async with self.lock:
            if message.author.bot:
                return
            if isinstance(message.channel, discord.Thread) and message.channel.parent_id == self.physbot_dm_forum_id:
                if message.content and message.content.startswith("//"):
                    return
                user_id = staff_utils.get_user_id_from_thread(message.channel)
                user = self.bot.get_user(user_id)
                if user.dm_channel is None:
                    await user.create_dm()
                user_channel = user.dm_channel
                await staff_utils.relay_content(user_channel, message, self.message_cache)
                
            elif isinstance(message.channel, discord.DMChannel) and message.author.id != self.bot.user.id: 
                forum = self.bot.get_channel(self.physbot_dm_forum_id)
                thread = await staff_utils.get_user_thread(forum, message.author)
                assert thread is not None, f"Could not find or create thread for user {message.author.id} in forum {self.physbot_dm_forum_id} for relaying."
                await staff_utils.relay_content(thread, message, self.message_cache)
                
        
    async def on_message_delete(self, message: discord.Message) -> None:
        async with self.lock:
            if message.author.bot:
                return
            if isinstance(message.channel, discord.Thread) and message.channel.parent_id == self.physbot_dm_forum_id:
                user_id = staff_utils.get_user_id_from_thread(message.channel)
                user = self.bot.get_user(user_id)
                if user.dm_channel is None:
                    await user.create_dm()
                user_channel = user.dm_channel
                success = await staff_utils.delete_relay(user_channel, message.id, self.message_cache)
                if not success:
                    await message.channel.send(f"Failed to delete relayed message for deleted message ID {message.id}.")                
    
    async def on_message_edit(self, before: discord.Message, after: discord.Message) -> None:
        async with self.lock:
            if before.author.bot:
                return
            if isinstance(before.channel, discord.Thread) and before.channel.parent_id == self.physbot_dm_forum_id:
                if after.content and after.content.startswith("//"):
                    return
                user_id = staff_utils.get_user_id_from_thread(after.channel)
                user = self.bot.get_user(user_id)
                if user.dm_channel is None:
                    await user.create_dm()
                user_channel = user.dm_channel
                await staff_utils.relay_content(user_channel, after, self.message_cache, before_message_id=before.id)
                
            elif isinstance(before.channel, discord.DMChannel) and before.author.id != self.bot.user.id:
                forum = self.bot.get_channel(self.physbot_dm_forum_id)
                if forum:
                    thread = await staff_utils.get_user_thread(forum, before.author)
                    if thread:
                        await staff_utils.relay_content(thread, after, self.message_cache) # Will not pass before_message_id for anti-privacy reasons
                    else:
                        self.logger.info(f"Could not find or create thread for user {before.author.id} in forum {self.physbot_dm_forum_id} for relaying edited message.")
                
    async def on_member_join(self, member: discord.Member) -> None:
        async with self.lock:
            account_age = member.joined_at - member.created_at

        if account_age < timedelta(days=2):
            staff_channel = self.bot.get_channel(config.staff_chat)
            embed = discord.Embed(
                title="Recently Joined Member",
                description=f"{member} joined the server. Account age: {account_age.days} days, {account_age.seconds // 3600} hours.",
                color=discord.Color.red(),
                timestamp=datetime.utcnow()
                
            )
            embed.set_thumbnail(url=member.avatar.url if member.avatar else None)
            embed.set_footer(text=f"{member.id}")
            await staff_channel.send(embed=embed)
            
    async def clear(self):
        while self.lock.locked():
            await asyncio.sleep(0.1)
        await self.lock.acquire()

