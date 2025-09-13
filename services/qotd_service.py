import config
import utils.utils as utils
import asyncio
import discord
from typing import Union, Optional, Tuple, Any
from discord.ext import commands
from services.google_sheet_service import GoogleSheetService, LocalSheet
from logger import Logger
import random
from utils.qotd_utils import (
    COLUMN,
    get_qotd_num_to_post,
    get_statistics_embed,
    get_submit_embed,
    grade,
    get_score,
    is_correct_answer,
    create_scores_embed,
    create_submission_embed,
    get_stats,
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
            content=f"Uploaded as QoTD {num}. Accepted by {interaction.user}", view=None
        )
        self.stop()

    @discord.ui.button(label="No", style=discord.ButtonStyle.red)
    async def no(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            content=f"Cancelled uploading...", view=None
        )
        self.stop()


class QotdService:
    def __init__(self, bot: commands.Bot) -> None:
        """Initialize the QotdService with a bot instance."""
        self.logger = Logger(bot)
        self.gss: GoogleSheetService = GoogleSheetService("QOTD")
        self.bot: commands.Bot = bot
        self.live_qotd: Optional[int] = None
        self.lock: asyncio.Lock = asyncio.Lock()
        self.users: dict[str, str] = {}
        self.is_end_season: bool = False

    def get_faq(self):
        return self.gss["faq"].get_data()

    async def random(
        self,
        channel: discord.TextChannel,
        topic: Optional[str],
        curator: Optional[discord.Member],
        difficulty: Optional[str],
    ) -> bool:
        """Fetch a random QOTD based on the topic, curator, and difficulty."""
        async with self.lock:
            main_sheet = self.gss["Sheet1"]
            valid_qotds = []
            for num in range(1, len(main_sheet.get_data())):
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
                        valid_qotds.append(num)
            if not valid_qotds:
                return False
            qotd_num = random.choice(valid_qotds)
            await utils.post_question(
                channel=channel,
                num=main_sheet[qotd_num, COLUMN["qotd_num"]],
                date=main_sheet[qotd_num, COLUMN["date"]],
                day=main_sheet[qotd_num, COLUMN["day"]],
                links=main_sheet[qotd_num, COLUMN["question link"]],
                creator=main_sheet[qotd_num, COLUMN["creator"]],
                difficulty=main_sheet[qotd_num, COLUMN["difficulty"]],
            )
            return True

    async def pending(
        self, channel: discord.TextChannel, num: Optional[int]
    ) -> discord.Embed:
        """Get the pending QOTD or a specific QOTD if num is provided."""
        async with self.lock:

            main_sheet = self.gss["Sheet1"]
            if num is None:
                embed = discord.Embed(
                    title="Pending QOTD",
                    color=discord.Color.yellow(),
                )
                for i in range(1, len(main_sheet.get_data())):
                    if main_sheet[i, COLUMN["status"]] == "pending":
                        embed.add_field(
                            name=f"QOTD {i}",
                            value=(f"{main_sheet[i, COLUMN['question link']]}"),
                            inline=False,
                        )
                return embed
            else:
                if (
                    num < 1
                    or num >= len(main_sheet.get_data())
                    or main_sheet[num, COLUMN["status"]] != "pending"
                ):
                    await self.logger.warning(f"Invalid QOTD number: {num}")
                    return discord.Embed(
                        title="Error",
                        description="Invalid QOTD number",
                        color=discord.Color.red(),
                    )
                embed = discord.Embed(
                    title=f"Pending QOTD #{num}",
                    color=discord.Color.green(),
                )
                embed.add_field(
                    name="Question Link",
                    value=main_sheet[num, COLUMN["question link"]],
                    inline=False,
                )
                await utils.post_question(
                    channel=channel,
                    num=main_sheet[num, COLUMN["qotd_num"]],
                    date=main_sheet[num, COLUMN["date"]],
                    day=main_sheet[num, COLUMN["day"]],
                    links=main_sheet[num, COLUMN["question link"]],
                    creator=main_sheet[num, COLUMN["creator"]],
                    source=main_sheet[num, COLUMN["source"]],
                    difficulty=main_sheet[num, COLUMN["difficulty"]],
                    answer=main_sheet[num, COLUMN["answer"]],
                    tolerance=main_sheet[num, COLUMN["tolerance"]],
                )
                return embed

    async def edit(
        self,
        num: int,
        question_links: str,
        curator: str,
        topic: str,
        answer: str,
        tolerance: str,
        source: str,
        difficulty: str,
    ) -> bool:
        async with self.lock:
            main_sheet = self.gss["Sheet1"]
            if num < 1 or num >= len(main_sheet.get_data()):
                await self.logger.warning(f"Invalid QOTD number: {num}")
                return False

            main_sheet[num, COLUMN["question link"]] = (
                question_links or main_sheet[num, COLUMN["question link"]]
            )
            main_sheet[num, COLUMN["creator"]] = (
                curator or main_sheet[num, COLUMN["creator"]]
            )
            main_sheet[num, COLUMN["topic"]] = topic or main_sheet[num, COLUMN["topic"]]
            main_sheet[num, COLUMN["answer"]] = (
                answer or main_sheet[num, COLUMN["answer"]]
            )
            main_sheet[num, COLUMN["tolerance"]] = (
                tolerance or main_sheet[num, COLUMN["tolerance"]]
            )
            main_sheet[num, COLUMN["source"]] = (
                source or main_sheet[num, COLUMN["source"]]
            )
            main_sheet[num, COLUMN["difficulty"]] = (
                difficulty or main_sheet[num, COLUMN["difficulty"]]
            )
            main_sheet.commit()
            await self.logger.info(f"Updated QOTD {num} successfully")
            return True

    async def daily_question(self) -> None:
        """Post the question of the day (QOTD) every day at a specified time."""
        async with self.lock:
            self.live_qotd = None
            if self.gss["data"][1, 3] == "live":
                await self._update_leaderboard_stats()
                await self._daily_question()
                await self._update_leaderboard_stats()
            else:
                await self.logger.info("Toggle is OFF, skipping QOTD post")

    async def clear(self):
        while self.lock.locked():
            await asyncio.sleep(0.1)
        await self.lock.acquire()

    async def update_leaderboard(self) -> bool:
        """Update the leaderboard with the latest QOTD statistics."""
        async with self.lock:
            if self.gss["data"][1, 3] == "live":
                return await self._update_leaderboard_stats()
            else:
                return False

    async def fetch(
        self,
        channel: utils.ChannelType,
        qotd_num: int,
    ) -> bool:
        """Post the QOTD for a specific QOTD number."""
        async with self.lock:
            main_sheet = self.gss["Sheet1"]
            if (
                qotd_num < 1
                or qotd_num >= len(main_sheet.get_data())
                or main_sheet[qotd_num, COLUMN["status"]] not in ["done", "active"]
            ):
                await self.logger.warning(f"Invalid QOTD number: {qotd_num}")
                return False

            await self.logger.info(f"Posting QOTD {qotd_num}")
            await utils.post_question(
                channel=channel,
                num=self.gss["Sheet1"][qotd_num, COLUMN["qotd_num"]],
                date=self.gss["Sheet1"][qotd_num, COLUMN["date"]],
                day=self.gss["Sheet1"][qotd_num, COLUMN["day"]],
                links=self.gss["Sheet1"][qotd_num, COLUMN["question link"]],
                creator=self.gss["Sheet1"][qotd_num, COLUMN["creator"]],
                difficulty=self.gss["Sheet1"][qotd_num, COLUMN["difficulty"]],
            )
            return True

    async def solution(self, qotd_num: int, link: str = "") -> str:
        async with self.lock:
            main_sheet = self.gss["Sheet1"]
            if qotd_num < 1 or qotd_num >= len(main_sheet.get_data()):
                await self.logger.warning(f"Invalid QOTD number: {qotd_num}")
                return "Invalid QOTD number"
            if link:
                await self.logger.info(f"Updating solution link for QOTD {qotd_num}")
                main_sheet[qotd_num, COLUMN["solution"]] = link
                main_sheet.commit()
                await self.logger.info("Solution link updated successfully")
                return "Solution link updated successfully"
            else:
                if main_sheet[qotd_num, COLUMN["status"]] in ["done", "active"]:
                    await self.logger.info(f"Fetching solution for QOTD {qotd_num}")
                    qotd_creator = main_sheet[qotd_num, COLUMN["creator"]]
                    source = main_sheet[qotd_num, COLUMN["source"]]
                    solution = main_sheet[qotd_num, COLUMN["solution"]]
                    answer = main_sheet[qotd_num, COLUMN["answer"]]
                    tolerance = main_sheet[qotd_num, COLUMN["tolerance"]]
                    post = (
                        f"**QOTD {qotd_num} Solution**\n"
                        + f"QOTD Creator: **{qotd_creator}**\n"
                        + f"Answer: {answer}   Tolerance: {tolerance}\n"
                        + f"Source: {source}\n"
                        + f"{solution}"
                    )
                    return post
                else:
                    await self.logger.warning(
                        f"Solution not available for QOTD {qotd_num}"
                    )
                    return "Solution not available yet"

    async def submit(
        self, interaction: discord.Interaction, qotd_num: Optional[int], answer: str
    ) -> None:
        """Submit an answer for the QOTD."""
        async with self.lock:
            action_needed = await self._submit(interaction, qotd_num, answer)
            if action_needed:
                await self._update_leaderboard_stats()

    async def upload(
        self,
        channel: discord.TextChannel,
        creator: str,
        source: str,
        points: str,
        question_links: str,
        topic: str,
        difficulty: str,
        answer: str,
        tolerance: str,
    ) -> None:
        """Upload a new QOTD to the Google Sheet and post it in the specified channel."""
        async with self.lock:
            main_sheet = self.gss["Sheet1"]
            qotd_num = len(main_sheet.get_data())
            to_append = [
                qotd_num,
                f"DD MON YYYY",
                "WEEKDAY",
                creator,
                source,
                points,
                question_links,
                topic,
                difficulty,
                "",
                answer,
                tolerance,
                "pending",
            ]
            await utils.post_question(
                channel=channel,
                num=str(qotd_num),
                date="DD MON YYYY",
                day="WEEKDAY",
                links=question_links,
                creator=creator,
                source=source,
                topic=topic,
                difficulty=difficulty,
                answer=answer,
                tolerance=tolerance,
            )
            await channel.send(
                view=Menu(main_sheet, to_append),
                content="Are you sure you want to upload this QOTD? This action cannot be undone.",
            )

    async def get_scores(self, user: discord.abc.User):
        async with self.lock:
            scores = await self._get_scores(str(user.id))
            embed = create_scores_embed(user.name, scores)
            return embed

    async def verify_submissions(
        self, user: Union[discord.User, discord.Member], qotd_num: int
    ) -> Optional[discord.Embed]:
        """Send the status of the QOTD to the user."""
        async with self.lock:
            main_sheet = self.gss["Sheet1"]
            if main_sheet[qotd_num, COLUMN["status"]] in ["live", "active"]:
                answer = main_sheet[qotd_num, COLUMN["answer"]]
                tolerance = main_sheet[qotd_num, COLUMN["tolerance"]]
                sub = []
                for userid, *submissions in self.gss[f"qotd {qotd_num}"].get_data():
                    if userid == str(user.id):
                        sub = submissions
                        break
                embed = create_submission_embed(user, qotd_num, sub, answer, tolerance)
                await self.logger.warning(embed=embed)
                return embed
            return None

    async def _submit(
        self, interaction: discord.Interaction, qotd_num: Optional[int], answer_str: str
    ) -> bool:
        main_sheet = self.gss["Sheet1"]
        user = interaction.user
        action_needed = False
        qotd_num = qotd_num or self._get_live_qotd_num()
        if qotd_num is None:
            await self.logger.warning("No live QOTD for submission")
            await interaction.followup.send(
                "No live QOTD available to submit an answer for."
            )
            return False
        if (
            qotd_num < 1
            or qotd_num >= len(main_sheet.get_data())
            or main_sheet[qotd_num, COLUMN["status"]] == "pending"
        ):
            await self.logger.warning(f"Invalid QOTD number {qotd_num} for submission")
            await interaction.followup.send("Invalid QOTD number")
            return False
        try:
            answer = float(answer_str)
        except ValueError:
            await interaction.followup.send(
                "Invalid answer format. Please provide a numeric answer."
            )
            return False
        correct_ans = float(main_sheet[qotd_num, COLUMN["answer"]])
        tolerance = float(main_sheet[qotd_num, COLUMN["tolerance"]])
        is_correct = is_correct_answer(correct_ans, answer, tolerance)
        embed = get_submit_embed(
            user=user,
            qotd_num=qotd_num,
            answer=answer,
            correct=is_correct,
        )
        phods = self.bot.get_guild(config.phods)
        assert phods, "PHODS guild not found"
        member = phods.get_member(user.id)
        if (
            main_sheet[qotd_num, COLUMN["status"]] == "live"
            and member
            and not member.get_role(config.admin)
            and not member.get_role(config.qotd_creator)
        ):
            qotd_sheet = self.gss[f"qotd {qotd_num}"]
            data = qotd_sheet.get_data()
            for sub in data:
                if sub[0] == str(user.id):
                    sub.append(str(answer))
                    break
            else:
                data.append([str(user.id), str(answer)])

            qotd_sheet.update_data(data)
            qotd_sheet.commit()
            await utils.get_text_channel(self.bot, config.qotd_botspam).send(
                embed=embed
            )
            if is_correct:
                action_needed = True
                qotd_logs = utils.get_text_channel(
                    self.bot, config.qotd_logs
                )
                await qotd_logs.send(
                    f"{user.mention} has solved QOTD #{qotd_num} !!!\nCongratulations! 🎉"
                )
                member = phods.get_member(user.id)
                if member:
                    role = phods.get_role(config.qotd_solver)
                    if role is not None:
                        await member.add_roles(role)
                        await self.logger.info(f"Added solver role to user {user.id}")
        await interaction.followup.send(embed=embed)
        return action_needed

    async def _daily_question(self) -> None:
        main_sheet = self.gss["Sheet1"]
        qotd_num_to_post = get_qotd_num_to_post(main_sheet)
        if qotd_num_to_post is None:
            await self.logger.warning("No QOTD available to post")
            qotd_planning = self.bot.get_channel(config.qotd_planning)
            assert isinstance(
                qotd_planning, discord.TextChannel
            ), "QOTD Creator channel not found"
            await qotd_planning.send(
                f"<@&{config.qotd_creator}> Toggle is on but no QOTD is available to post. Previous Qotd is still live."
            )
            return

        # Complete the previous QOTD if it is still live
        if main_sheet[qotd_num_to_post - 1, COLUMN["status"]] == "live":
            await self.logger.info(f"Completing previous QOTD {qotd_num_to_post-1}")
            main_sheet[qotd_num_to_post - 1, COLUMN["status"]] = "active"

        # Increment the QOTD number in the for leaderboard
        data_sheet = self.gss["data"]
        data_sheet[1, 1] = str(int(data_sheet[1, 1]) + 1)
        data_sheet.commit()
        await self.logger.info(f"Creating new sheet for QOTD {qotd_num_to_post}")
        try:
            self.gss.create_sheet(f"qotd {qotd_num_to_post}")
        except Exception as e:
            await self.logger.error(
                "Unable to create the sheet, maybe already existed", e
            )
        # Update the main sheet with the new QOTD details
        await self.logger.info(f"Setting QOTD {qotd_num_to_post} status to live")
        main_sheet[qotd_num_to_post, COLUMN["status"]] = "live"
        main_sheet[qotd_num_to_post, COLUMN["date"]] = utils.get_date()
        main_sheet[qotd_num_to_post, COLUMN["day"]] = utils.get_day()
        await utils.post_question(
            channel=self.bot.get_channel(config.question_of_the_day),
            num=main_sheet[qotd_num_to_post, COLUMN["qotd_num"]],
            date=main_sheet[qotd_num_to_post, COLUMN["date"]],
            day=main_sheet[qotd_num_to_post, COLUMN["day"]],
            links=main_sheet[qotd_num_to_post, COLUMN["question link"]],
            creator=main_sheet[qotd_num_to_post, COLUMN["creator"]],
            difficulty=main_sheet[qotd_num_to_post, COLUMN["difficulty"]],
            announce=True,
        )
        await self.logger.info("Posted new QOTD")
        phods = self.bot.get_guild(config.phods)
        assert phods, "PHODS guild not found"
        qotd_solver_role = phods.get_role(config.qotd_solver)
        assert qotd_solver_role, "QOTD Solver role not found"
        await utils.remove_roles(qotd_solver_role)
        await self.logger.info("Reset solver roles")
        # stats
        stats_embed = get_statistics_embed(
            num=qotd_num_to_post,
            creator=main_sheet[qotd_num_to_post, COLUMN["creator"]],
        )
        question_of_the_day_channel = self.bot.get_channel(config.question_of_the_day)
        assert isinstance(
            question_of_the_day_channel, discord.TextChannel
        ), "Question of the Day channel not found"

        stats_msg = await question_of_the_day_channel.send(embed=stats_embed)
        assert self.bot.user
        await question_of_the_day_channel.send(
            f"<@&{config.qotd_role}> to submit your answer use /qotd submit command in my({self.bot.user.mention}) DM."
        )
        main_sheet[qotd_num_to_post, COLUMN["stats"]] = str(stats_msg.id)

        # leaderboard
        leader_board_channel = self.bot.get_channel(config.leaderboard)
        assert isinstance(
            leader_board_channel, discord.TextChannel
        ), "Leaderboard channel not found"
        leaderboard_msg = await leader_board_channel.send(
            "Placeholder for leaderboard message"
        )
        main_sheet[qotd_num_to_post, COLUMN["leaderboard"]] = str(leaderboard_msg.id)

        # final commit
        main_sheet.commit()
        await self.logger.info("Daily question processing completed")

    async def _get_scores(self, user_id: str):
        main_sheet = self.gss["Sheet1"]
        scores: list[tuple[str, float]] = []
        for user, score in self.gss["Leaderboard"].get_data():
            if user == user_id:
                scores.append(("Offset", float(score)))
        for num in range(1, len(main_sheet.get_data())):
            if main_sheet[num, COLUMN["status"]] in ["active", "live"]:
                ans = main_sheet[num, COLUMN["answer"]]
                tolerance = main_sheet[num, COLUMN["tolerance"]]
                qotd_sheet = self.gss[f"qotd {num}"]
                stats = get_stats(qotd_sheet, ans, tolerance)
                for user, *sub in qotd_sheet.get_data():
                    if user == user_id:
                        scores.append(
                            (f"Qotd {num}", get_score(sub, ans, tolerance, stats))
                        )
        scores.append(("Total", sum(k[1] for k in scores)))
        return scores

    async def end_season(self) -> None:
        """End the current season and reset the QOTD data."""
        async with self.lock:
            if self.is_end_season:
                self.live_qotd = None
                self.is_end_season = False
                self._update_leaderboard_stats()
                await self.logger.info("Ending the season")
                main_sheet = self.gss["Sheet1"]
                active_and_live = []
                for num in range(1, len(main_sheet.get_data())):
                    if main_sheet[num, COLUMN["status"]] in ["active", "live"]:
                        active_and_live.append(num)
                        main_sheet[num, COLUMN["status"]] = "done"
                main_sheet.commit()
                await self.logger.info("main sheet updated")
                for num in active_and_live:
                    del self.gss[f"qotd {num}"]
                await self.logger.info("Deleted all active QOTD sheets")
                data_sheet = self.gss["data"]
                data_sheet[1, 2] = str(int(data_sheet[1, 2]) + 1)
                data_sheet[1, 3] = "live"
                data_sheet[1, 1] = "0"
                data_sheet.commit()
                await self.logger.info("Data sheet updated for new season")
                await utils.remove_roles(
                    self.bot.get_guild(config.phods).get_role(config.qotd_solver)
                )
                await self.logger.info(
                    f"Ended season with {len(active_and_live)} QOTDs"
                )
            else:
                self.is_end_season = True
                return "Use the command again to end the season."

    async def _update_leaderboard_stats(self) -> bool:
        await self.logger.info("Updating leaderboard stats")
        qotd_num = self._get_live_qotd_num()
        if qotd_num is None:
            await self.logger.warning("No live QOTD for leaderboard update")
            return False
        await self.logger.info(f"Updating stats for live QOTD {qotd_num}")
        main_sheet = self.gss["Sheet1"]
        message = self.gss["data"][1, 0]
        done_qotds = self.gss["data"][1, 1]
        season = self.gss["data"][1, 2]
        time = utils.get_time()
        message = message.format(
            qotd=qotd_num,
            day=done_qotds,
            season=season,
            time=time,
        )

        total_scores = {
            user: float(score) for user, score in self.gss["Leaderboard"].get_data()
        }
        for num in range(1, len(main_sheet.get_data())):
            if main_sheet[num, COLUMN["status"]] in ["active", "live"]:
                ans = main_sheet[num, COLUMN["answer"]]
                tolerance = main_sheet[num, COLUMN["tolerance"]]
                qotd_sheet = self.gss[f"qotd {num}"]
                scores, stats = grade(qotd_sheet, ans, tolerance)
                for user, points in scores.items():
                    total_scores[user] = total_scores.get(user, 0.0) + points

        for rank, (userid, point) in enumerate(
            sorted(total_scores.items(), key=lambda x: float(x[1]), reverse=True)[:29],
            start=1,
        ):
            rank_dot = f"{rank}."
            username = await self._get_user_name_or_id(userid)
            message += f"\n{rank_dot:4} {username[:29]:29} {float(point):.3f}"
        message += "\n```"
        leaderboard_channel = self.bot.get_channel(config.leaderboard)
        assert isinstance(
            leaderboard_channel, discord.TextChannel
        ), "Leaderboard channel not found"
        leaderboard_msg = await leaderboard_channel.fetch_message(
            int(main_sheet[qotd_num, COLUMN["leaderboard"]])
        )
        await leaderboard_msg.edit(content=message)
        question_of_the_day = self.bot.get_channel(config.question_of_the_day)
        assert isinstance(
            question_of_the_day, discord.TextChannel
        ), "Question of the Day channel not found"
        stats_msg = await question_of_the_day.fetch_message(
            int(main_sheet[qotd_num, COLUMN["stats"]])
        )
        stats_embed = get_statistics_embed(
            num=qotd_num,
            creator=main_sheet[qotd_num, COLUMN["creator"]],
            base=stats.base,
            weighted_solves=stats.weight_solves,
            solves_official=stats.total_solves,
            total_attempts=stats.total_attempts,
        )
        await stats_msg.edit(embed=stats_embed)
        await self.logger.info("Leaderboard stats updated")
        return True

    async def _get_user_name_or_id(self, user_id: str) -> str:
        if user_id in self.users:
            return self.users[user_id]
        try:
            user = await self.bot.fetch_user(int(user_id))
            self.users[user_id] = str(user)
            return str(user)
        except discord.NotFound:
            self.users[user_id] = user_id
            await self.logger.warning(f"User not found: {user_id}")
            return user_id
        except Exception as e:
            await self.logger.error(f"Error fetching user {user_id}: {e}, e")
            return user_id

    def _get_live_qotd_num(self) -> Optional[int]:
        if self.live_qotd is not None:
            return self.live_qotd
        main_sheet = self.gss["Sheet1"]
        for num in range(1, len(main_sheet.get_data())):
            if main_sheet[num, COLUMN["status"]] == "live":
                self.live_qotd = num
                return num
        return None
