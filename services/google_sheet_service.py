import gspread
class LocalSheet:
    def __init__(self, workbook: gspread.Spreadsheet, sheet_name: str) -> None:
        self.sheet: gspread.Worksheet =  workbook.worksheet(sheet_name)
        self._data: list[list[str]] = self.sheet.get()
        self._dirty: bool = False
        self.sheet_name: str = sheet_name
    
    def __getitem__(self, cell_index: tuple[int, int]) -> str:
        row, col = cell_index
        return self._data[row][col]
    
    def __setitem__(self, cell_index: tuple[int, int], value: str) -> None:
        row, col = cell_index
        while len(self._data[row]) <= col:
            self._data[row].append("")
        self._data[row][col] = value
        self._dirty = True
        
    def get_data(self) -> list[list[str]]:
        return self._data
    
    def update_data(self, data: list[list[str]]) -> None:
        assert isinstance(data, list) and all(isinstance(row, list) for row in data) and all(isinstance(cell, str) for row in data for cell in row), "Assertion failer not all string"
        self._data = data
        self._dirty = True
        
    def append_row(self, row: list[str]) -> None:
        self._data.append(row)
        self._dirty = True
    
    def commit(self) -> None:
        if self._dirty:
            self.sheet.update(self._data)
            self._dirty = False                    
class GoogleSheetService:
    def __init__(self, workbook_name: str) -> None:
        self.gc: gspread.Client = gspread.service_account(filename='/secrets/creds.json')
        self.workbook: gspread.Spreadsheet = self.gc.open(workbook_name)
        self.sheets: dict[str, LocalSheet] = {}
        self.workbook_name: str = workbook_name
    
    def create_sheet(self, sheet_name: str) -> None:
        if sheet_name in self.sheets:
            raise ValueError(f"Sheet '{sheet_name}' already exists.")
        self.workbook.add_worksheet(title=sheet_name, rows=100, cols=20)
        self.sheets[sheet_name] = LocalSheet(self.workbook, sheet_name)
    
    def __getitem__(self, sheet_name) -> LocalSheet:
        if sheet_name not in self.sheets:
            self.sheets[sheet_name] = LocalSheet(self.workbook, sheet_name)
        return self.sheets[sheet_name]

    def __delitem__(self, sheet_name: str) -> None:
        try:
            if sheet_name in self.sheets:
                del self.sheets[sheet_name]
            self.workbook.del_worksheet(self.workbook.worksheet(sheet_name))
        except gspread.WorksheetNotFound:
            pass