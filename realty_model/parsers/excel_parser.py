from realty_model.models.property import ProFormaInput
from realty_model.parsers.base import BaseParser


class ExcelParser(BaseParser):
    def parse(self, filepath: str) -> ProFormaInput:
        import openpyxl
        wb = openpyxl.load_workbook(filepath, data_only=True)
        ws = wb.active
        raw = {}
        for row in ws.iter_rows(min_row=2, values_only=True):
            if len(row) < 3:
                continue
            section = row[0]
            field = row[1]
            value = row[2]
            if section and field and value is not None:
                key = f"{str(section).strip().upper()}.{str(field).strip().lower()}"
                raw[key] = str(value).strip()
        return self._build_input(raw)
