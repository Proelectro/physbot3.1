import numpy as np
from typing import Optional, Any, Union
from utils import utils
from datetime import datetime, timezone
from services.google_sheet_service import LocalSheet
import config
import discord

COLUMN = {
    "potd_num": 0,
    "date": 1,
    "day": 2,
    "creator": 3,
    "source": 4,
    "points": 5,
    "problem path": 6,
    "topic": 7,
    "difficulty": 8,
    "solution": 9,
    "status": 10,
    "id": 11,
}


def get_potd_num_to_post(main_sheet) -> Optional[int]:
    for num in range(1, len(main_sheet.get_data())):
        if main_sheet[num, COLUMN["status"]] == "pending":
            return num
    return None



