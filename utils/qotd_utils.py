import numpy as np
from typing import Optional, Any, Union
from utils import utils
from datetime import datetime, timezone
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


def get_qotd_num_to_post(main_sheet) -> Optional[int]:
    for num in range(1, len(main_sheet.get_data())):
        if main_sheet[num, COLUMN["status"]] == "pending":
            return num
    return None

def grade(
    correct_ans: str, tolerance: str, submission: list[list[str]]
) -> tuple[list[list[Any]], float, float, int, int]:
    totalatt = 0
    weigting = {}
    for sub in submission:
        user, *attp = sub
        totalatt += len(attp)
        score = 1.0 / 0.8
        for ans in attp[:6]:
            score *= 0.8
            if utils.is_correct_answer(
                float(correct_ans), float(ans), float(tolerance)
            ):
                break
        else:
            score = 0
        weigting[user] = score
    weightsolve = sum(weigting.values())
    numsolved = len(list(filter(lambda k: weigting[k], weigting)))
    base = A1 * np.exp(a1 * weightsolve) + B1 * np.exp(b1 * weightsolve)
    points = [[user, str(weigting[user] * base)] for user in weigting]
    return points, base, weightsolve, numsolved, totalatt
    
def get_statistics_embed(
    num: int,
    creator: str,
    base=A1 + B1,
    weighted_solves=0,
    solves_official=0,
    total_attempts=0,
) -> discord.Embed:
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
    return embed