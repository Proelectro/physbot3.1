from datetime import time, datetime
import os
from typing import Optional, Union

import discord
from discord.ext import commands, tasks
from discord import app_commands
from discord.app_commands import CommandOnCooldown

import config
import utils.utils as utils
from services.staff_service import StaffService
from logger import Logger
from utils.utils import requires_permission, catch_errors, Permission, PaginatorView
from help_cmds import cmds_creator, cmds_everyone, cmds_staff

Cog = commands.Cog

class Staff(Cog):
    group = app_commands.Group(
        name="staff",
        description="Manage and interact with the staff system.",
    )

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bot.tree.on_error = self.on_app_command_error
        self.logger = Logger(bot)
        self.staff_service = StaffService(bot)

    # General

    @Cog.listener()
    @catch_errors
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return        
        await self.staff_service.on_message(message)
    
    @Cog.listener()
    @catch_errors
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.author.bot:
            return        
        await self.staff_service.on_message_edit(before, after)
        
    @Cog.listener()
    async def on_delete_message(self, message: discord.Message):
        if message.author.bot:
            return        
        await self.staff_service.on_delete_message(message)    

    @Cog.listener()
    async def on_app_command_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ):
        if not isinstance(error, CommandOnCooldown):
            staff = await self.bot.fetch_user(config.proelectro)
            await self.logger.log_error.send(
                staff.mention,
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

    @group.command(name="monitor", description="To monitor/ unmonitor a channel")
    @requires_permission(Permission.STAFF)
    async def monitor(self, interaction: discord.Interaction, channel_: Optional[discord.TextChannel] = None, user_: Optional[discord.User] = None):
        await interaction.response.defer()
        msg = await self.staff_service.monitor(channel_, user_)
        await interaction.followup.send(msg)
        
    @group.command(
        name="clear_cache", description="Restricted to the owner only (proelectro)."
    )
    @requires_permission(Permission.PROELECTRO)
    async def clear_cache(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        new_staff_service = StaffService(self.bot)
        old_staff_service = self.staff_service
        async with new_staff_service.lock:
            self.staff_service = new_staff_service
            await old_staff_service.clear()
        await interaction.followup.send("Cleared cache successfully.", ephemeral=True)
        await self.logger.warning("Cache cleared by proelectro")


    @group.command(
        name="help", description="Displays list and description of staff cmds"
    )
    @requires_permission(Permission.STAFF)
    async def help(self, interaction: discord.Interaction):
        await interaction.response.defer()
        # Pick correct command list
        command_list = cmds_staff
        title = "🏆 Staff Commands"
        # Build pages
        pages = []
        per_page = 5
        for i in range(0, len(command_list), per_page):
            embed = discord.Embed(
                title=title,
                color=discord.Color.blurple(),
                description="Below are the staff commands. Commands executed in DMs are marked accordingly.",
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
    """Load the Staff cog."""
    await bot.add_cog(Staff(bot))
