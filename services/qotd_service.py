import logging
# Add logger configuration at the top
logger = logging.getLogger("qotd_service")
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

import config
import utils
import asyncio
import numpy as np
import discord
from typing import Union, Optional, Tuple, Any
from datetime import datetime, timezone
from discord.ext import commands
from services.google_sheet_service import GoogleSheetService, LocalSheet

COLUMN = {
    "qotd_num": 0,
    "date": 1,
    "day": 2,
    "creator": 3,
    "source": 4,
    "points": 5,
    "question link": 6,
    "topic": 7,
    "difficulty": 8,
    "solution": 9,
    "answer": 10,
    "tolerance": 11,
    "status": 12,
    "stats": 13,
    "leaderboard": 14,
}
A1, a1, B1, b1 = 8.90125, -0.0279323, 24.6239, -0.402639


class Menu(discord.ui.View):
    def __init__(self, main_sheet: LocalSheet, to_append: list):
        super().__init__(timeout=None)
        logger.info(f"Creating Menu with sheet: {main_sheet.sheet_name}, data: {to_append}")
        self.to_append = to_append
        self.main_sheet = main_sheet

    @discord.ui.button(label="Yes", style=discord.ButtonStyle.green)
    async def yes(self, interaction: discord.Interaction, button: discord.ui.Button):
        logger.info(f"Menu YES selected by {interaction.user}")
        data = self.main_sheet.get_data()
        num = self.to_append[0] = len(data)
        self.main_sheet.append_row(self.to_append)
        self.main_sheet.commit()
        logger.info(f"Appended new QOTD {num} to sheet")
        await interaction.response.edit_message(
            content=f"Uploaded as QoTD {num}. Accepted by {interaction.user}", view=None
        )
        self.stop()

    @discord.ui.button(label="No", style=discord.ButtonStyle.red)
    async def no(self, interaction: discord.Interaction, button: discord.ui.Button):
        logger.info(f"Menu NO selected by {interaction.user}")
        await interaction.response.edit_message(
            content=f"Cancelled uploading...", view=None
        )
        self.stop()


class QotdService:
    def __init__(self, bot: commands.Bot) -> None:
        """Initialize the QotdService with a bot instance."""
        logger.info("Initializing QotdService")
        self.gss: GoogleSheetService = GoogleSheetService("QOTD")
        self.bot: commands.Bot = bot
        self.live_qotd: Optional[int] = None
        self.lock: asyncio.Lock = asyncio.Lock()
        self.users: dict[str, str] = {}
        logger.info("QotdService initialized")

    async def daily_question(self) -> None:
        """Post the question of the day (QOTD) every day at a specified time."""
        logger.info("Daily question triggered")
        async with self.lock:
            logger.debug("Acquired lock for daily_question")
            self.live_qotd = None
            if utils.check_toggle_state(
                self.bot.get_channel(config.qotd_toggle), config.qotd_toggle
            ):
                logger.info("Toggle is ON, proceeding to post QOTD")
                await self._daily_question()
            else:
                logger.info("Toggle is OFF, skipping QOTD post")
            logger.debug("Released lock for daily_question")

    async def update_leaderboard(self) -> bool:
        """Update the leaderboard with the latest QOTD statistics."""
        logger.info("Updating leaderboard")
        async with self.lock:
            logger.debug("Acquired lock for update_leaderboard")
            result = await self._update_leaderboard_stats()
            logger.info(f"Leaderboard update result: {result}")
            logger.debug("Released lock for update_leaderboard")
            return result

    async def merge_leaderboard(self, qotd_num: int, action: bool) -> None:
        """Merge the leaderboard for a specific QOTD number."""
        logger.info(f"Merging leaderboard for QOTD {qotd_num}, action: {action}")
        async with self.lock:
            logger.debug("Acquired lock for merge_leaderboard")
            self._merge_leaderboard(qotd_num, action)
            logger.info(f"Leaderboard merged for QOTD {qotd_num}")
            logger.debug("Released lock for merge_leaderboard")

    async def fetch(
        self,
        channel: utils.ChannelType,
        qotd_num: int,
    ) -> bool:
        """Post the QOTD for a specific QOTD number."""
        logger.info(f"Fetch request for QOTD {qotd_num} in channel {channel.id if channel else 'None'}")
        async with self.lock:
            logger.debug("Acquired lock for fetch")
            main_sheet = self.gss["Sheet1"]
            if qotd_num < 1 or qotd_num >= len(main_sheet.get_data()):
                logger.warning(f"Invalid QOTD number: {qotd_num}")
                logger.debug("Released lock for fetch")
                return False
            valid_channel_ids = [
                config.qotd_botspam,
                config.qotd_planning,
            ]
            if main_sheet[qotd_num, COLUMN["status"]] == "done" or (channel and channel.id in valid_channel_ids):
                logger.info(f"Posting QOTD {qotd_num}")
                await utils.post_question(
                    channel=channel,
                    num=self.gss["Sheet1"][qotd_num, COLUMN["qotd_num"]],
                    date=self.gss["Sheet1"][qotd_num, COLUMN["date"]],
                    day=self.gss["Sheet1"][qotd_num, COLUMN["day"]],
                    links=self.gss["Sheet1"][qotd_num, COLUMN["question link"]],
                    creator=self.gss["Sheet1"][qotd_num, COLUMN["creator"]],
                    source=self.gss["Sheet1"][qotd_num, COLUMN["source"]],
                    difficulty=self.gss["Sheet1"][qotd_num, COLUMN["difficulty"]],
                )
                logger.debug("Released lock for fetch")
                return True
            else:
                logger.warning(f"Invalid status or channel for QOTD {qotd_num}")
                logger.debug("Released lock for fetch")
                return False

    async def solution(
        self, user: Union[discord.User, discord.Member], qotd_num: int, link: Optional[str] = None
    ) -> str:
        logger.info(f"Solution request for QOTD {qotd_num} by {user.id}")
        async with self.lock:
            logger.debug("Acquired lock for solution")
            main_sheet = self.gss["Sheet1"]
            if qotd_num < 1 or qotd_num >= len(main_sheet.get_data()):
                logger.warning(f"Invalid QOTD number: {qotd_num}")
                logger.debug("Released lock for solution")
                return "Invalid QOTD number"
            if link and isinstance(user, discord.Member) and user.get_role(config.qotd_creator):
                logger.info(f"Updating solution link for QOTD {qotd_num}")
                main_sheet[qotd_num, COLUMN["solution"]] = link
                main_sheet.commit()
                logger.info("Solution link updated successfully")
                logger.debug("Released lock for solution")
                return "Solution link updated successfully"
            else:
                if main_sheet[qotd_num, COLUMN["solution"]] == "done":
                    logger.info(f"Fetching solution for QOTD {qotd_num}")
                    qotd_creator = main_sheet[qotd_num, COLUMN["creator"]]
                    source = main_sheet[qotd_num, COLUMN["source"]]
                    solution = main_sheet[qotd_num, COLUMN["solution"]]
                    answer = main_sheet[qotd_num, COLUMN["answer"]]
                    post = (
                        f"**QOTD {qotd_num} Solution**\n"
                        + f"QOTD Creator: **{qotd_creator}**\n"
                        + f"Answer: {answer}\n"
                        + f"Source: {source}\n"
                        + f"{solution}"
                    )
                    logger.debug("Released lock for solution")
                    return post
                else:
                    logger.warning(f"Solution not available for QOTD {qotd_num}")
                    channel = self.bot.get_channel(config.log_important)
                    assert isinstance(channel, discord.TextChannel), "The channel must be a TextChannel to send the message."
                    await channel.send(
                        f"User {user} tried to fetch solution for QOTD {qotd_num}, but it is not available yet."
                    )
                    logger.debug("Released lock for solution")
                    return "Solution not available yet"

    async def submit(
        self, interaction: discord.Interaction, qotd_num: Optional[int], answer: str
    ) -> None:
        """Submit an answer for the QOTD."""
        logger.info(f"Submit request by {interaction.user.id} for QOTD {qotd_num} with answer: {answer}")
        async with self.lock:
            logger.debug("Acquired lock for submit")
            await self._submit(interaction, qotd_num, answer)
            logger.debug("Released lock for submit")

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
        logger.info(f"Upload request in channel {channel.id} by {creator}")
        async with self.lock:
            logger.debug("Acquired lock for upload")
            main_sheet = self.gss["Sheet1"]
            qotd_num = len(main_sheet.get_data())
            logger.info(f"New QOTD number: {qotd_num}")
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
            logger.info("Posted preview, sending confirmation menu")
            await channel.send(
                view=Menu(main_sheet, to_append),
                content="Are you sure you want to upload this QOTD? This action cannot be undone.",
            )
            logger.debug("Released lock for upload")

    async def status(self, user: Union[discord.User, discord.Member]) -> str:
        """Send the status of the QOTD to the user."""
        logger.info(f"Status request by user {user.id}")
        async with self.lock:
            logger.debug("Acquired lock for status")
            main_sheet = self.gss["Sheet1"]
            qotd_num = self._get_live_qotd_num()
            if qotd_num is None:
                logger.warning("No live QOTD available for status")
                logger.debug("Released lock for status")
                return "No live QOTD available."
            message = f"**QOTD {qotd_num} Status**\n"
            answer_str = main_sheet[qotd_num, COLUMN["answer"]]
            tolerance_str = main_sheet[qotd_num, COLUMN["tolerance"]]
            answer = float(answer_str)
            tolerance = float(tolerance_str)
            multiplier = "0.0"
            for userid, *submissions in self.gss[f"qotd {qotd_num}"].get_data():
                if userid == str(user.id):
                    wrong_attempts = -1
                    if submissions:
                        for i, sub in enumerate(submissions, start=1):
                            verdict = (
                                "Correct"
                                if utils.is_correct_answer(
                                    answer, float(sub), tolerance
                                )
                                else "Incorrect"
                            )
                            message += f"Attempt {i}: {sub} - {verdict}\n"
                            if verdict == "Correct":
                                wrong_attempts = i - 1
                                break
                    multiplier = (
                        "0.0" if wrong_attempts == -1 else f"0.8 ^ {wrong_attempts}"
                    )
            score = "0.0"
            for userid, _score in self.gss["Leaderboard"].get_data()[1:]:
                if userid == str(user.id):
                    score = _score
            message += f"\nYour score: {score} + base x ({multiplier})\n"
            logger.info(f"Returning status for user {user.id}")
            logger.debug("Released lock for status")
            return message

    async def delete(self, qotd_num: int) -> bool:
        """Delete a QOTD by its number."""
        logger.info(f"Delete request for QOTD {qotd_num}")
        async with self.lock:
            logger.debug("Acquired lock for delete")
            main_sheet = self.gss["Sheet1"]
            if (
                qotd_num < 1
                or qotd_num >= len(main_sheet.get_data())
                or main_sheet[qotd_num, COLUMN["status"]] != "pending"
            ):
                logger.warning(f"Invalid deletion request for QOTD {qotd_num}")
                logger.debug("Released lock for delete")
                return False
            data = main_sheet.get_data()
            del data[qotd_num]
            main_sheet.update_data(data)
            main_sheet.commit()
            logger.info(f"QOTD {qotd_num} deleted successfully")
            logger.debug("Released lock for delete")
            return True

    async def _submit(
        self, interaction: discord.Interaction, qotd_num: Optional[int], answer_str: str
    ) -> None:
        logger.info(f"Processing submission for QOTD {qotd_num} by {interaction.user.id}")
        main_sheet = self.gss["Sheet1"]
        user = interaction.user
        assert interaction.channel
        

        qotd_num = qotd_num or self._get_live_qotd_num()
        if qotd_num is None:
            logger.warning("No live QOTD for submission")
            await interaction.followup.send(
                "No live QOTD available to submit an answer for."
            )
            return
        if (
            qotd_num < 1
            or qotd_num >= len(main_sheet.get_data())
            or main_sheet[qotd_num, COLUMN["status"]] == "pending"
        ):
            logger.warning(f"Invalid QOTD number {qotd_num} for submission")
            await interaction.followup.send("Invalid QOTD number")
            return
        try:
            answer = float(answer_str)
        except ValueError:
            logger.error(f"Invalid answer format: {answer_str}")
            await interaction.followup.send(
                "Invalid answer format. Please provide a numeric answer."
            )
            return
        correct_ans = float(main_sheet[qotd_num, COLUMN["answer"]])
        tolerance = float(main_sheet[qotd_num, COLUMN["tolerance"]])
        is_correct = utils.is_correct_answer(correct_ans, answer, tolerance)
        logger.info(f"Answer correctness: {is_correct}")
        embed = self._get_submit_embed(
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
                    logger.info(f"Appended answer to existing user submission")
                    break
            else:
                data.append([str(user.id), str(answer)])
                logger.info(f"Created new submission record for user")
            qotd_sheet.update_data(data)
            qotd_sheet.commit()
            qotd_botspam = self.bot.get_channel(config.qotd_botspam)
            assert isinstance(qotd_botspam, discord.TextChannel), "QOTD Botspam channel not found"
            await qotd_botspam.send(embed=embed)
            if is_correct:
                member = phods.get_member(user.id)
                if member:
                    role = phods.get_role(config.qotd_solver)
                    if role is not None:
                        await member.add_roles(role)
                        logger.info(f"Added solver role to user {user.id}")
        await interaction.followup.send(embed=embed)
        logger.info("Submission processed successfully")

    async def _daily_question(self) -> None:
        logger.info("Processing daily question")
        main_sheet = self.gss["Sheet1"]
        qotd_num_to_post = self._get_qotd_num_to_post()
        if qotd_num_to_post is None:
            logger.warning("No QOTD available to post")
            qotd_planning = self.bot.get_channel(config.qotd_planning)
            assert isinstance(qotd_planning, discord.TextChannel), "QOTD Creator channel not found"
            await qotd_planning.send(
                f"<@&{config.qotd_creator}> Toggle is on but no QOTD is available to post. Previous Qotd is still live."
            )
            return

        # Complete the previous QOTD if it is still live
        if main_sheet[qotd_num_to_post - 1, COLUMN["status"]] == "live":
            logger.info(f"Completing previous QOTD {qotd_num_to_post-1}")
            self._merge_leaderboard(qotd_num_to_post - 1, True)
            main_sheet[qotd_num_to_post - 1, COLUMN["status"]] = "done"

        # Increment the QOTD number in the for leaderboard
        data_sheet = self.gss["data"]
        data_sheet[1, 1] = str(int(data_sheet[1, 1]) + 1)
        data_sheet.commit()
        logger.info(f"Creating new sheet for QOTD {qotd_num_to_post}")
        try:
            self.gss.create_sheet(f"qotd {qotd_num_to_post}")
        except Exception as e:
            logger.error(e)
        # Update the main sheet with the new QOTD details
        logger.info(f"Setting QOTD {qotd_num_to_post} status to live")
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
        )
        logger.info("Posted new QOTD")
        phods = self.bot.get_guild(config.phods)
        assert phods, "PHODS guild not found"
        qotd_solver_role = phods.get_role(config.qotd_solver)
        assert qotd_solver_role, "QOTD Solver role not found"
        await utils.remove_roles(qotd_solver_role)
        logger.info("Reset solver roles")
        # stats
        stats_embed = self._get_statistics_embed(
            num=qotd_num_to_post,
            creator=main_sheet[qotd_num_to_post, COLUMN["creator"]],
        )
        question_of_the_day_channel = self.bot.get_channel(config.question_of_the_day)
        assert isinstance(question_of_the_day_channel, discord.TextChannel), "Question of the Day channel not found"
        leader_board_channel = self.bot.get_channel(config.leaderboard)
        assert isinstance(leader_board_channel, discord.TextChannel), "Leaderboard channel not found"
        
        stats_msg = await question_of_the_day_channel.send(
            embed=stats_embed
        )
        logger.debug(len(main_sheet.get_data()))
        logger.debug(qotd_num_to_post)
        main_sheet[qotd_num_to_post, COLUMN["stats"]] = str(stats_msg.id)
        # leaderboard
        leaderboard_msg = await leader_board_channel.send(
            "Placeholder for leaderboard message"
        )
        main_sheet[qotd_num_to_post, COLUMN["leaderboard"]] = str(leaderboard_msg.id)
        # remove old QOTD
        logger.info(f"Removing old QOTD sheet: qotd {qotd_num_to_post - 3}")
        del self.gss[f"qotd {qotd_num_to_post - 3}"]
        main_sheet.commit()
        logger.info("Daily question processing completed")

    def _get_qotd_num_to_post(self) -> Optional[int]:
        logger.debug("Finding next QOTD to post")
        main_sheet = self.gss["Sheet1"]
        for num in range(1, len(main_sheet.get_data())):
            if main_sheet[num, COLUMN["status"]] == "pending":
                logger.info(f"Found pending QOTD {num} to post")
                return num
        logger.warning("No pending QOTD found")
        return None

    def _grade(
        self, correct_ans: str, tolerance: str, submission: list[list[str]]
    ) -> tuple[list[list[Any]], float, float, int, int]:
        logger.info(f"Grading submissions for answer: {correct_ans}, tolerance: {tolerance}")
        totalatt = 0
        weigting = {}
        for sub in submission:
            user, *attp = sub
            totalatt += len(attp)
            score = 1.0 / 0.8
            for ans in attp[:6]:
                score *= 0.8
                if utils.is_correct_answer(float(correct_ans), float(ans), float(tolerance)):
                    break
            else:
                score = 0
            weigting[user] = score
        weightsolve = sum(weigting.values())
        numsolved = len(list(filter(lambda k: weigting[k], weigting)))
        base = A1 * np.exp(a1 * weightsolve) + B1 * np.exp(b1 * weightsolve)
        points = [[user, str(weigting[user] * base)] for user in weigting]
        logger.info(f"Grading completed: solved={numsolved}, attempts={totalatt}, base={base:.2f}")
        return points, base, weightsolve, numsolved, totalatt

    def _grade_and_merge(
        self, qotd_num: int, action: bool
    ) -> Tuple[list[list[str]], float, float, int, int]:
        logger.info(f"Grading and merging leaderboard for QOTD {qotd_num}, action={action}")
        main_sheet = self.gss["Sheet1"]
        qotd_sheet = self.gss[f"qotd {qotd_num}"]
        leaderboard_sheet = self.gss["Leaderboard"]
        points, base, weightsolve, numsolved, totalatt = self._grade(
            correct_ans=main_sheet[qotd_num, COLUMN["answer"]],
            tolerance=main_sheet[qotd_num, COLUMN["tolerance"]],
            submission=qotd_sheet.get_data(),
        )
        points_dict = {user: score for user, score in points}
        update = [["users", "points"]]
        for user_str, past_score_str in leaderboard_sheet.get_data()[1:]:
            try:
                past_score = float(past_score_str)
                if action:
                    past_score += float(points_dict[user_str])
                else:
                    past_score -= float(points_dict[user_str])
                del points_dict[user_str]
            except KeyError:
                pass
            except ValueError:
                continue
            update.append([user_str, str(past_score)])

        for user_str, score in points_dict.items():
            update.append([user_str, score])

        logger.info(f"Leaderboard updated with {len(update)} entries")
        return update, base, weightsolve, numsolved, totalatt

    def _merge_leaderboard(self, qotd_num: int, action: bool) -> None:
        logger.info(f"Merging leaderboard for QOTD {qotd_num}, action={action}")
        update = self._grade_and_merge(qotd_num, action)[0]
        leaderboard_sheet = self.gss["Leaderboard"]
        leaderboard_sheet.update_data(update)
        leaderboard_sheet.commit()
        logger.info("Leaderboard merged and committed")

    def _get_statistics_embed(
        self,
        num: int,
        creator: str,
        base=A1 + B1,
        weighted_solves=0,
        solves_official=0,
        total_attempts=0,
    ) -> discord.Embed:
        logger.debug(f"Creating statistics embed for QOTD {num}")
        embed = discord.Embed(
            title=f"Live Statistics for QoTD {num}",
        )
        embed.set_footer(text=f"Creator: {creator}")
        embed.add_field(name="Base Points", value=f"{base:.3f}")
        embed.add_field(
            name="Weighted Solves", value=str(weighted_solves), inline=False
        )
        embed.add_field(
            name="Solves (official)", value=str(solves_official), inline=False
        )
        embed.add_field(name="Total attempts", value=str(total_attempts), inline=False)
        return embed

    async def _update_leaderboard_stats(self) -> bool:
        logger.info("Updating leaderboard stats")
        qotd_num = self._get_live_qotd_num()
        if qotd_num is None:
            logger.warning("No live QOTD for leaderboard update")
            return False
        logger.info(f"Updating stats for live QOTD {qotd_num}")
        main_sheet = self.gss["Sheet1"]
        update, base, weighted_solves, solves_official, total_attempts = (
            self._grade_and_merge(qotd_num, True)
        )
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
        for rank, (userid, point) in enumerate(
            sorted(update[1:], key=lambda x: float(x[1]), reverse=True)[:30], start=1
        ):
            rank_dot = f"{rank}."
            username = await self._get_user_name_or_id(userid)
            message += f"\n{rank_dot:4} {username[:30]:30} {float(point):.3f}"
        message += "\n```"
        leaderboard_channel = self.bot.get_channel(config.leaderboard)
        assert isinstance(leaderboard_channel, discord.TextChannel), "Leaderboard channel not found"
        logger.debug("Posting leaderboard message")
        leaderboard_msg = await leaderboard_channel.fetch_message(
            int(main_sheet[qotd_num, COLUMN["leaderboard"]])
        )
        await leaderboard_msg.edit(content=message)
        question_of_the_day = self.bot.get_channel(config.question_of_the_day)
        assert isinstance(question_of_the_day, discord.TextChannel), "Question of the Day channel not found"
        stats_msg = await question_of_the_day.fetch_message(int(main_sheet[qotd_num, COLUMN["stats"]]))
        stats_embed = self._get_statistics_embed(
            num=qotd_num,
            creator=main_sheet[qotd_num, COLUMN["creator"]],
            base=base,
            weighted_solves=weighted_solves,
            solves_official=solves_official,
            total_attempts=total_attempts,
        )
        await stats_msg.edit(embed=stats_embed)
        logger.info("Leaderboard stats updated")
        return True
    
    async def _get_user_name_or_id(self, user_id: str) -> str:
        logger.debug(f"Fetching username for {user_id}")
        if user_id in self.users:
            logger.debug(f"Found cached username for {user_id}")
            return self.users[user_id]
        try:
            user = await self.bot.fetch_user(int(user_id))
            self.users[user_id] = str(user)
            logger.debug(f"Fetched username: {user}")
            return str(user)
        except discord.NotFound:
            self.users[user_id] = user_id
            logger.warning(f"User not found: {user_id}")
            return user_id
        except Exception as e:
            log_error = self.bot.get_channel(config.log_error)
            assert isinstance(log_error, discord.TextChannel), "Log error channel not found"
            await log_error.send(
                f"Error fetching user {user_id}: {e}"
            )
            logger.error(f"Error fetching user {user_id}: {e}")
            return user_id

    def _get_live_qotd_num(self) -> Optional[int]:
        logger.debug("Getting live QOTD number")
        if self.live_qotd is not None:
            logger.debug(f"Using cached live QOTD: {self.live_qotd}")
            return self.live_qotd
        main_sheet = self.gss["Sheet1"]
        for num in range(1, len(main_sheet.get_data())):
            if main_sheet[num, COLUMN["status"]] == "live":
                self.live_qotd = num
                logger.info(f"Found live QOTD: {num}")
                return num
        logger.warning("No live QOTD found")
        return None

    def _get_submit_embed(
        self, user: Union[discord.User, discord.Member], qotd_num: int, answer: float, correct: bool
    ) -> discord.Embed:
        logger.debug(f"Creating submit embed for user {user.id}")
        embed = discord.Embed(
            description=f"**Submission to QOTD {qotd_num} made by {user}**",
            colour=config.green if correct else config.red,
            timestamp=datetime.now(timezone.utc),
        )
        embed.set_author(name=user.name, icon_url=user.display_avatar.url)
        embed.add_field(name="Submitted Answer:", value=answer, inline=False)
        embed.add_field(
            name="Verdict:", value="Correct" if correct else "Incorrect", inline=False
        )
        return embed