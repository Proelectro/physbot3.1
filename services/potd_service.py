import os
import config
import utils.utils as utils
import asyncio
import discord
from collections import defaultdict
from typing import Union, Optional, Tuple, Any
from discord.ext import commands
from services.google_sheet_service import GoogleSheetService, LocalSheet
from logger import Logger
import random
from utils.ansi_utils import create_ansi_message, ansi_colorize
from utils.potd_utils import (
    COLUMN,
    get_potd_num_to_post,
)


class Menu(discord.ui.View):
    def __init__(self, main_sheet: LocalSheet, to_append: list):
        super().__init__(timeout=None)
        self.to_append = to_append
        self.main_sheet = main_sheet

    @discord.ui.button(label="Yes", style=discord.ButtonStyle.green)
    async def yes(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = self.main_sheet.get_data()
        num = self.to_append[0] = len(data)
        self.main_sheet.append_row(self.to_append)
        self.main_sheet.commit()
        await interaction.response.edit_message(
            content=f"Uploaded as POTD {num}. Accepted by {interaction.user}", view=None
        )
        self.stop()

    @discord.ui.button(label="No", style=discord.ButtonStyle.red)
    async def no(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            content=f"Cancelled uploading...", view=None
        )
        self.stop()


class PotdService:
    def __init__(self, bot: commands.Bot) -> None:
        """Initialize the PotdService with a bot instance."""
        self.logger = Logger(bot)
        self.gss: GoogleSheetService = GoogleSheetService("POTD")
        self.bot: commands.Bot = bot
        self.live_potd: Optional[int] = None
        self.lock: asyncio.Lock = asyncio.Lock()
        self.user_cache: dict[str, str] = {}  # Cache for user ID to username mapping

    async def random(
        self,
        channel: discord.TextChannel,
        topic: Optional[str],
        curator: Optional[discord.Member],
        difficulty: Optional[str],
    ) -> bool:
        """Fetch a random POTD based on the topic, curator, and difficulty."""
        async with self.lock:
            main_sheet = self.gss["Sheet1"]
            valid_potds = []
            for num in range(1, len(main_sheet)):
                if main_sheet[num, COLUMN["status"]] == "done":
                    if (
                        (topic is None or main_sheet[num, COLUMN["topic"]] == topic)
                        and (
                            curator is None
                            or main_sheet[num, COLUMN["creator"]] == str(curator.name)
                        )
                        and (
                            difficulty is None
                            or main_sheet[num, COLUMN["difficulty"]] in difficulty
                        )
                    ):
                        valid_potds.append(num)
            if not valid_potds:
                return False
            potd_num = random.choice(valid_potds)
            await utils.post_question(
                pqotd="POTD",
                channel=channel,
                num=main_sheet[potd_num, COLUMN["potd_num"]],
                date=main_sheet[potd_num, COLUMN["date"]],
                day=main_sheet[potd_num, COLUMN["day"]],
                problem_path=main_sheet[potd_num, COLUMN["problem path"]],
                creator=main_sheet[potd_num, COLUMN["creator"]],
                difficulty=main_sheet[potd_num, COLUMN["difficulty"]],
                topic=main_sheet[potd_num, COLUMN["topic"]],
                points=main_sheet[potd_num, COLUMN["points"]],
            )
            return True

    async def add_score(
        self, num: int,  user: discord.Member, points: int, user_id: Optional[int] = None
    ) -> bool:
        """Add score to a user for solving the POTD."""
        async with self.lock:
            main_sheet = self.gss["Sheet1"]
            user_id = str(user_id or user.id)
            if num < 1 or num >= len(main_sheet) or main_sheet[num, COLUMN["status"]] not in ["live", "active"]:
                await self.logger.warning(f"Invalid POTD number, for add_score: {num}")
                return False
            score_sheet = self.gss[f"potd_{num}"]
            for row in range(len(score_sheet)):
                if score_sheet[row, 0] == user_id:
                    current_score = int(score_sheet[row, 1])
                    score_sheet[row, 1] = str(current_score + points)
                    score_sheet.commit()
                    return True
            # If user not found, add a new entry
            score_sheet.append_row([user_id, str(points)])
            score_sheet.commit()
            return True
        
    async def update_leaderboard(self, num: int) -> bool:
        """Update the leaderboard for a specific POTD."""
        async with self.lock:
            return await self._update_leaderboard(num)
            
    async def _update_leaderboard(self, num: int) -> bool:
        main_sheet = self.gss["Sheet1"]
        if num < 1 or num >= len(main_sheet) or main_sheet[num, COLUMN["status"]] not in ["active", "live"]:
            await self.logger.warning(f"Invalid POTD number, for update_leaderboard: {num}")
            return False
        scores = defaultdict(int)
        for num in range(1, len(main_sheet)):
            if main_sheet[num, COLUMN["status"]] in ["live", "active"]:
                score_sheet = self.gss[f"potd_{num}"]
                for row in range(len(score_sheet)):
                    user_id = score_sheet[row, 0]
                    points = int(score_sheet[row, 1])
                    scores[user_id] += points
        message = self.gss["data"][1, 0]
        season = self.gss["data"][1, 1]
        message = message.format(
            potd=num,
            season=season,
        )
        # self.logger.debug(f"Updating leaderboard for POTD {num} with scores: {scores}")
        for rank, (userid, point) in enumerate(
            sorted(scores.items(), key=lambda x: float(x[1]), reverse=True)[:30],
            start=1,
        ):
            rank_dot = f"{rank}."
            username = await self._get_user_name_or_id(userid)
            message += f"\n{rank_dot:4} {username[:29]:29} {float(point):.3f}"
        message += "\n```"
        
        leaderboard_channel = self.bot.get_channel(config.potd_leaderboard)
        if main_sheet[num, COLUMN["leaderboard"]].strip():
            msg = await leaderboard_channel.fetch_message(int(main_sheet[num, COLUMN["leaderboard"]]))
            await msg.edit(content=message)
        else:
            msg = await leaderboard_channel.send(message)
            main_sheet[num, COLUMN["leaderboard"]] = str(msg.id)
            main_sheet.commit()
        return True

    async def _get_user_name_or_id(self, user_id: str) -> str:
        try:
            return self.user_cache[user_id]
        except KeyError:
            pass
        try:
            user = await self.bot.fetch_user(int(user_id))
            return user.name if user else user_id
        except Exception as e:
            await self.logger.warning(f"Failed to fetch user for ID {user_id}: {e}")
            return user_id

    async def pending(
        self, channel: discord.TextChannel, num: Optional[int]
    ) -> discord.Embed:
        """Get the pending POTD or a specific POTD if num is provided."""
        async with self.lock:
            main_sheet = self.gss["Sheet1"]
            if num is None:
                embed = discord.Embed(
                    title="Pending POTD",
                    color=discord.Color.yellow(),
                )
                max_pending = 10
                for i in range(1, len(main_sheet)):
                    if main_sheet[i, COLUMN["status"]] == "pending":
                        embed.add_field(
                            name=f"POTD {i}",
                            value=(f"Topic: {main_sheet[i, COLUMN['topic']]}, Points: {main_sheet[i, COLUMN['points']]}, Source: {main_sheet[i, COLUMN['source']]}"),
                            inline=False,
                        )
                        if len(embed.fields) >= max_pending:
                            break
                return embed
            else:
                if (
                    num < 1
                    or num >= len(main_sheet)
                ):
                    await self.logger.warning(f"Invalid POTD number: {num}")
                    return discord.Embed(
                        title="Error",
                        description="Invalid POTD number",
                        color=discord.Color.red(),
                    )
                embed = discord.Embed(
                    title=f"Pending POTD #{num}",
                    color=discord.Color.green(),
                )
                embed.add_field(
                    name="problem path",
                    value=main_sheet[num, COLUMN["problem path"]],
                    inline=False,
                )
                await utils.post_question(
                    pqotd="POTD",
                    channel=channel,
                    num=main_sheet[num, COLUMN["potd_num"]],
                    date=main_sheet[num, COLUMN["date"]],
                    day=main_sheet[num, COLUMN["day"]],
                    problem_path=main_sheet[num, COLUMN["problem path"]],
                    creator=main_sheet[num, COLUMN["creator"]],
                    source=main_sheet[num, COLUMN["source"]],
                    difficulty=main_sheet[num, COLUMN["difficulty"]],
                    topic=main_sheet[num, COLUMN["topic"]],
                )
                return embed

    async def edit(
        self,
        num: int,
        problem: discord.Attachment,
        curator: str,
        topic: str,
        points: str,
        source: str,
        difficulty: str,
    ) -> bool:
        async with self.lock:
            main_sheet = self.gss["Sheet1"]
            if num < 1 or num >= len(main_sheet):
                await self.logger.warning(f"Invalid POTD number: {num}")
                return False

            if problem:
                image_path = await utils.upload_potd_image("potd_images", num, problem, self.logger)
                main_sheet[num, COLUMN["problem path"]] = image_path
            else:
                main_sheet[num, COLUMN["problem path"]] = main_sheet[num, COLUMN["problem path"]]
            main_sheet[num, COLUMN["creator"]] = (
                curator or main_sheet[num, COLUMN["creator"]]
            )
            main_sheet[num, COLUMN["topic"]] = topic or main_sheet[num, COLUMN["topic"]]
            main_sheet[num, COLUMN["points"]] = points or main_sheet[num, COLUMN["points"]]
            main_sheet[num, COLUMN["source"]] = (
                source or main_sheet[num, COLUMN["source"]]
            )
            main_sheet[num, COLUMN["difficulty"]] = (
                difficulty or main_sheet[num, COLUMN["difficulty"]]
            )
            main_sheet.commit()
            await self.logger.info(f"Updated POTD {num} successfully")
            return True

    async def daily_problem(self) -> None:
        """Post the problem of the day (POTD) every day at a specified time."""
        async with self.lock:
            if self.gss["data"][1, 2] == "live":
                self.live_potd = None
                await self._daily_problem()
            else:
                self.live_potd = None
                await self.logger.info("Toggle is OFF, skipping POTD post")

    async def clear(self):
        while self.lock.locked():
            await asyncio.sleep(0.1)
        await self.lock.acquire()

    async def check(self, channel: utils.ChannelType):
        async with self.lock:
            main_sheet = self.gss["Sheet1"]
            import os, re
            for file in os.listdir("potd_images"):
                match = re.search(r"potd_(\d+)\.", file)
                if match:
                    num = int(match.group(1))
                    main_sheet[num, COLUMN["problem path"]] = f"potd_images/{file}"
                else:
                    # Optional: print a warning or skip the file if it doesn't match the pattern
                    print(f"Skipping file: {file} (No pattern match)")
            main_sheet.commit()
            await channel.send("Checked for new POTD images and updated links accordingly.")
                    
            

    async def fetch(
        self,
        channel: utils.ChannelType,
        potd_num: int,
    ) -> bool:
        """Post the POTD for a specific POTD number."""
        async with self.lock:
            main_sheet = self.gss["Sheet1"]
            if (
                potd_num < 1
                or potd_num >= len(main_sheet)
                or main_sheet[potd_num, COLUMN["status"]] not in ["done", "active"]
            ):
                await self.logger.warning(f"Invalid POTD number: {potd_num}")
                return False

            await self.logger.info(f"Posting POTD {potd_num}")
            await utils.post_question(
                pqotd="POTD",
                channel=channel,
                num=self.gss["Sheet1"][potd_num, COLUMN["potd_num"]],
                date=self.gss["Sheet1"][potd_num, COLUMN["date"]],
                day=self.gss["Sheet1"][potd_num, COLUMN["day"]],
                problem_path=self.gss["Sheet1"][potd_num, COLUMN["problem path"]],
                creator=self.gss["Sheet1"][potd_num, COLUMN["creator"]],
                difficulty=self.gss["Sheet1"][potd_num, COLUMN["difficulty"]],
                topic=self.gss["Sheet1"][potd_num, COLUMN["topic"]],
                points=self.gss["Sheet1"][potd_num, COLUMN["points"]],
            )
            return True

    async def solution(self, potd_num: int, link: str = "") -> str:
        async with self.lock:
            main_sheet = self.gss["Sheet1"]
            if potd_num < 1 or potd_num >= len(main_sheet):
                await self.logger.warning(f"Invalid POTD number: {potd_num}")
                return "Invalid POTD number"
            if link:
                await self.logger.info(f"Updating solution link for POTD {potd_num}")
                main_sheet[potd_num, COLUMN["solution"]] = link
                main_sheet.commit()
                await self.logger.info("Solution link updated successfully")
                return "Solution link updated successfully"
            else:
                if main_sheet[potd_num, COLUMN["status"]] in ["done", "active"]:
                    await self.logger.info(f"Fetching solution for POTD {potd_num}")
                    potd_creator = main_sheet[potd_num, COLUMN["creator"]]
                    source = main_sheet[potd_num, COLUMN["source"]]
                    solution = main_sheet[potd_num, COLUMN["solution"]]
                    post = (
                        f"**POTD {potd_num} Solution**\n"
                        + f"POTD Creator: **{potd_creator}**\n"
                        + f"Source: {source}\n"
                        + f"{solution if solution.strip() else 'Solution not available yet contact the creator for more info.'}"
                    )
                    return post
                else:
                    await self.logger.warning(
                        f"Solution not available for POTD {potd_num}"
                    )
                    return "Solution not available yet"

    async def submit(
        self, interaction: discord.Interaction, potd_num: Optional[int], solution: discord.Attachment
    ) -> None:
        """Submit an answer for the POTD."""
        async with self.lock:
            return await self._submit(interaction, potd_num, solution)
            

    async def upload(
        self,
        channel: discord.TextChannel,
        creator: str,
        source: str,
        points: str,
        problem: discord.Attachment,
        topic: str,
        difficulty: str,
    ) -> None:
        """Upload a new POTD to the Google Sheet and post it in the specified channel."""
        async with self.lock:
            main_sheet = self.gss["Sheet1"]
            potd_num = len(main_sheet)
            file_name = utils.upload_potd_image("potd_images", potd_num, problem, self.logger)
            to_append = [
                potd_num,
                f"DD MON YYYY",
                "WEEKDAY",
                creator,
                source,
                points,
                file_name,
                topic,
                difficulty,
                "",
                "pending",
            ]
            await utils.post_question(
                pqotd="POTD",
                channel=channel,
                num=str(potd_num),
                date="DD MON YYYY",
                day="WEEKDAY",
                problem_path=file_name,
                creator=creator,
                source=source,
                topic=topic,
                points=points,
                difficulty=difficulty,
            )
            await channel.send(
                view=Menu(main_sheet, to_append),
                content="Are you sure you want to upload this POTD? This action cannot be undone.",
            )

    
    async def _submit(
        self, interaction: discord.Interaction, potd_num: Optional[int], solution: discord.Attachment
    ) -> bool:
        if potd_num is None:
            potd_num = self._get_live_potd_num()
            if potd_num is None:
                await self.logger.warning("No live POTD to submit solution for")
                return False, "There is no live POTD to submit a solution for."
        main_sheet = self.gss["Sheet1"]
        if potd_num < 1 or potd_num >= len(main_sheet) or main_sheet[potd_num, COLUMN["status"]] == "pending":
            await self.logger.warning(f"Invalid POTD number: {potd_num}")
            return False, "Invalid POTD number."
        potd_botspam_channel = self.bot.get_channel(config.potd_botspam)
        await potd_botspam_channel.send(
            f"New solution submitted for POTD {potd_num} by {interaction.user.mention}.", file=await solution.to_file()
        )
        return True, "Solution submitted successfully."
 
    async def _daily_problem(self) -> None:
        main_sheet = self.gss["Sheet1"]
        potd_num_to_post = get_potd_num_to_post(main_sheet)
        if potd_num_to_post is None:
            await self.logger.warning("No POTD available to post")
            potd_planning = self.bot.get_channel(config.potd_planning)
            assert isinstance(
                potd_planning, discord.TextChannel
            ), "POTD Creator channel not found"
            await potd_planning.send(
                f"<@&{config.potd_creator}> Toggle is on but no POTD is available to post. Previous POTD is still live."
            )
            return

        # Complete the previous POTD if it is still live
        if main_sheet[potd_num_to_post - 1, COLUMN["status"]] == "live":
            await self.logger.info(f"Completing previous POTD {potd_num_to_post-1}")
            main_sheet[potd_num_to_post - 1, COLUMN["status"]] = "active"

        await self.logger.info(f"Setting POTD {potd_num_to_post} status to live")
        main_sheet[potd_num_to_post, COLUMN["status"]] = "live"
        main_sheet[potd_num_to_post, COLUMN["date"]] = utils.get_date()
        main_sheet[potd_num_to_post, COLUMN["day"]] = utils.get_day()
        await utils.post_question(
            pqotd="POTD",
            channel=self.bot.get_channel(config.problem_of_the_day),
            num=main_sheet[potd_num_to_post, COLUMN["potd_num"]],
            date=main_sheet[potd_num_to_post, COLUMN["date"]],
            day=main_sheet[potd_num_to_post, COLUMN["day"]],
            problem_path=main_sheet[potd_num_to_post, COLUMN["problem path"]],
            creator=main_sheet[potd_num_to_post, COLUMN["creator"]],
            difficulty=main_sheet[potd_num_to_post, COLUMN["difficulty"]],
            points=main_sheet[potd_num_to_post, COLUMN["points"]],
            announce=True,
        )
        await self.logger.info("Posted new POTD")

        problem_of_the_day_channel = self.bot.get_channel(config.problem_of_the_day)
        assert isinstance(
            problem_of_the_day_channel, discord.TextChannel
        ), "Problem of the Day channel not found"

        assert self.bot.user
        await problem_of_the_day_channel.send(
            f"<@&{config.potd_role}> to submit your solution use  /potd submit command in my({self.bot.user.mention}) DM."
        )
        self.gss.create_sheet(f"potd_{potd_num_to_post}")
        # final commit
        main_sheet.commit()
        await self.logger.info("Daily problem processing completed")

    
    def _get_live_potd_num(self) -> Optional[int]:
        if self.live_potd is not None:
            return self.live_potd
        main_sheet = self.gss["Sheet1"]
        for num in range(1, len(main_sheet)):
            if main_sheet[num, COLUMN["status"]] == "live":
                self.live_potd = num
                return num
        return None
