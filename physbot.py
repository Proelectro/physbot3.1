import logging
import discord
from discord.ext import commands
import config
from dotenv import load_dotenv
import os


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
