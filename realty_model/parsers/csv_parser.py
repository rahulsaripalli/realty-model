import csv
from realty_model.models.property import ProFormaInput
from realty_model.parsers.base import BaseParser


class CSVParser(BaseParser):
    def parse(self, filepath: str) -> ProFormaInput:
        raw = {}
        with open(filepath, newline='', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                section = str(row.get('section', '')).strip().upper()
                field = str(row.get('field', '')).strip().lower()
                value = str(row.get('value', '')).strip()
                if section and field:
                    raw[f"{section}.{field}"] = value
        return self._build_input(raw)
