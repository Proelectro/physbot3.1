from time import time
import gspread

class QotdData:
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
    
    def __init__(self) -> None:
        self.gc: gspread.Client = gspread.service_account(filename='secrets/creds.json')
        self.workbook: gspread.Spreadsheet = self.gc.open("QOTD")
        self.qotd_sheet: gspread.Worksheet = self.workbook.worksheet("Sheet1")
        self._last_fetched: float = 0.0
        self._data: list[list[str]] = []
        
    def fetch_data(self) -> None:
        if time() - self._last_fetched < 60 * 60 * 24:  # 24 hours
            return
        self._data = self.qotd_sheet.get_all_values()
        self._last_fetched = time()


if __name__ == "__main__":
    # Example usage
    qotd_data = QotdData()
    data = qotd_data.fetch_data()
    # get 100th QOTD number
    qotd_num = qotd_data._data[100][QotdData.COLUMN["qotd_num"]]
    qotd_question = qotd_data._data[100][QotdData.COLUMN["question link"]]
    print(f"QOTD #{qotd_num}: {qotd_question}")