import numpy as np
from typing import Optional, Any, Union
from utils import utils
from datetime import datetime, timezone
from services.google_sheet_service import LocalSheet
import config
import discord

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


class Stats:
    def __init__(
        self,
        weight_solves: float = 0.0,
        total_solves: int = 0,
        total_attempts: int = 0,
        base: Optional[float] = None,
    ):
        self.base = base
        self.weight_solves = weight_solves
        self.total_solves = total_solves
        self.total_attempts = total_attempts

    def calc_base(self):
        self.base = A1 * np.exp(a1 * self.weight_solves) + B1 * np.exp(
            b1 * self.weight_solves
        )

    def get_score(self, attempt: int):
        assert self.base, "please call calc base first"
        return self.base * 0.8**attempt


def get_qotd_num_to_post(main_sheet) -> Optional[int]:
    for num in range(1, len(main_sheet.get_data())):
        if main_sheet[num, COLUMN["status"]] == "pending":
            return num
    return None


def is_correct_answer(correct_ans: float, answer: float, tolerance: float = 1) -> bool:
    return abs(correct_ans - answer) <= abs(correct_ans * tolerance / 100.0)


def get_stats(qotd_sheet: LocalSheet, correct_ans: str, tolerance: str):
    stats = Stats()
    for user, *submissions in qotd_sheet.get_data():
        stats.total_attempts += len(submissions)
        attempts = 0
        for his_ans in submissions:
            if is_correct_answer(float(correct_ans), float(his_ans), float(tolerance)):
                if attempts <= 5:
                    stats.weight_solves += 0.8**attempts
                stats.total_solves += 1
                break
            attempts += 1
    stats.calc_base()
    return stats


def get_score(submissions: list[str], correct_ans: str, tolerance: str, stats: Stats):
    attempts = 0
    for his_ans in submissions:
        if is_correct_answer(float(correct_ans), float(his_ans), float(tolerance)):
            if attempts <= 5:
                return stats.get_score(attempts)
        attempts += 1
    return 0


def grade(qotd_sheet: LocalSheet, correct_ans: str, tolerance: str):
    stats = get_stats(qotd_sheet, correct_ans, tolerance)
    scores = {
        user: get_score(sub, correct_ans, tolerance, stats)
        for user, *sub in qotd_sheet.get_data()
    }
    return scores, stats


def create_scores_embed(
    username: str, scores: list[tuple[str, float]]
) -> discord.Embed:
    embed = discord.Embed(
        title=f"🏆 Scores Card {username}", color=discord.Color.gold()
    )

    for name, score in scores:
        embed.add_field(name=name, value=f"{score:.3f}", inline=False)
    return embed


def create_submission_embed(
    user: discord.abc.User,
    qotd_num: int,
    submissions: list[str],
    answer: str,
    tolerance: str,
) -> discord.Embed:
    embed = discord.Embed(
        title=f"📨 QOTD #{qotd_num} - Submissions by {user.name}",
        color=discord.Color.blurple(),
    )

    if not submissions:
        embed.add_field(
            name="No Submissions",
            value="This user hasn't submitted any answers yet.",
            inline=False,
        )
        return embed

    for idx, sub in enumerate(submissions, start=1):
        verdict = is_correct_answer(float(answer), float(sub), float(tolerance))
        verdict_emoji = "✅" if verdict else "❌"
        embed.add_field(
            name=f"Attempt #{idx}", value=f"{verdict_emoji} `{sub}`", inline=False
        )

    embed.set_footer(text=str(user.id))
    return embed


def get_statistics_embed(
    num: int,
    creator: str,
    base=A1 + B1,
    weighted_solves=0,
    solves_official=0,
    total_attempts=0,
) -> discord.Embed:
    embed = discord.Embed(
        title=f"Statistics for QoTD {num}\nLast Updated at {utils.get_time()}",
    )
    embed.set_footer(text=f"Creator: {creator}")
    embed.add_field(name="Base Points", value=f"{base:.3f}")
    embed.add_field(
        name="Weighted Solves", value=f"{weighted_solves:.3f}", inline=False
    )
    embed.add_field(name="Solves (official)", value=str(solves_official), inline=False)
    embed.add_field(name="Total attempts", value=str(total_attempts), inline=False)
    return embed


def get_submit_embed(
    user: Union[discord.User, discord.Member],
    qotd_num: int,
    answer: float,
    correct: bool,
) -> discord.Embed:
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
    embed.set_footer(text=str(user.id))
    return embed

def create_log_embed(user: Union[discord.User, discord.Member], qotd_num: int, color: discord.Color) -> discord.Embed:
    embed = discord.Embed(
        title=f"🎉 QOTD Solver!",
        description=f"{user.mention} has submitted the correct answer for QOTD {qotd_num}!",
        color=color,
        timestamp=datetime.now(timezone.utc),
    )
    embed.set_author(name=user.name, icon_url=user.display_avatar.url)
    embed.set_footer(text=str(user.id))
    return embed