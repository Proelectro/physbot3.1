import logging
import discord
from discord.ext import commands
import config
from dotenv import load_dotenv

import os


class Potd(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Start", custom_id="potd_button", style=discord.ButtonStyle.green
    )
    async def potd(self, interaction: discord.Interaction, button: discord.Button):
        if button.label == "Start":
            button.label = "Stop"
            button.style = discord.ButtonStyle.red
            await interaction.response.edit_message(
                content=f"**CurrentState** -> Start(id-100) (i.e. It will regularly post potds at 0:00UTC)\nPress this button to stop posting potds at 0:00UTC.\n**Note**\nSometimes you might need to click this button twice to make it work.\n**WARNING**\nThis will stop/start potds\nDon't click this without any intend or for fun.\n\nToggled by {interaction.user.mention}",
                view=self,
            )
        else:
            button.label = "Start"
            button.style = discord.ButtonStyle.green
            await interaction.response.edit_message(
                content=f"**CurrentState** -> Stop(id-101) (i.e. It will not post any potd at 0:00UTC)\nPress this button to start posting potds at 0:00UTC.\n**Note**\nSometimes you might need to click this button twice to make it work.\n**WARNING**\nThis will stop/start potds\nDon't click this without any intend or for fun.\n\nToggled by {interaction.user.mention}",
                view=self,
            )


class Qotd(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Start", custom_id="qotd_button", style=discord.ButtonStyle.green
    )
    async def qotd(self, interaction: discord.Interaction, button: discord.Button):
        if button.label == "Start":
            button.label = "Stop"
            button.style = discord.ButtonStyle.red
            await interaction.response.edit_message(
                content=f"**CurrentState** -> Start(id-100) (i.e. It will regularly post qotds at 0:00UTC)\nPress this button to stop posting qotds at 0:00UTC.\n**Note**\nSometimes you might need to click this button twice to make it work.\n**WARNING**\nThis will stop/start qotds\nDon't click this without any intend or for fun.\n\nToggled by {interaction.user.mention}",
                view=self,
            )
        else:
            button.label = "Start"
            button.style = discord.ButtonStyle.green
            await interaction.response.edit_message(
                content=f"**CurrentState** -> Stop(id-101) (i.e. It will not post any qotd at 0:00UTC)\nPress this button to start posting qotds at 0:00UTC.\n**Note**\nSometimes you might need to click this button twice to make it work.\n**WARNING**\nThis will stop/start qotds\nDon't click this without any intend or for fun.\n\nToggled by {interaction.user.mention}",
                view=self,
            )


class PHODSBot(commands.Bot):
    def __init__(self, prefix):
        intents = discord.Intents.all()
        intents.members = True
        super().__init__(prefix, intents=intents)
        self.config = config
        logging.basicConfig(
            level=logging.INFO, format="[%(name)s %(levelname)s] %(message)s"
        )
        self.logger = logging.getLogger("bot")

    async def on_ready(self):
        for cog in self.config.cogs:
            try:
                await self.load_extension(cog)
            except Exception:
                self.logger.exception("Failed to load cog {}.".format(cog))
            else:
                self.logger.info("Loaded cog {}.".format(cog))
        await self.tree.sync()
        embed = discord.Embed(
            color=config.green,
            title="Connected to Discord",
            description=f"We have logged in as {self.user.mention}.\nGuilds  : {', '.join(str(k) for k in self.guilds)}",
        )
        await self.get_channel(self.config.log_important).send(embed=embed)
        self.add_view(Potd())
        self.add_view(Qotd())

    async def on_error(self, event_method: str, *args, **kwargs) -> None:
        await self.get_channel(config.log_important).send(
            (await self.fetch_user(config.proelectro)).mention
            + " "
            + str(event_method)
            + " "
            + str(args)
            + str(kwargs)
        )
        raise


if __name__ == "__main__":
    load_dotenv()
    token = os.getenv("TOKEN")
    PHODSBot(config.prefix).run(token)
