from typing import Optional, Any, Union
from utils import utils
from services.google_sheet_service import LocalSheet
import config
import discord
from discord.ext import commands

def list_monitored(monitored_cache: dict) -> str:
    if not monitored_cache:
        return "No channels are being monitored."
    msg = "Currently monitored channels:\n"
    for channel in monitored_cache.keys():
        msg += f"- {channel}\n"
    return msg

def save_cache(monitored_cache: dict, monitoring_sheet: LocalSheet) -> None:
    data = []
    for channel, logging_channel in monitored_cache.items():
        data.append([str(channel.id), str(logging_channel.id)])
    monitoring_sheet.update_data(data)
    monitoring_sheet.commit()

def send_message_embed(message: discord.Message, color: discord.Colour, before: Optional[discord.Message] = None) -> discord.Embed:
    embed = discord.Embed(description=message.content, color=color)
    if before:
        embed.set_footer(text=f"Edited from: {before.content}")
    embed.set_author(name=str(message.author), icon_url=message.author.display_avatar.url)
    return embed