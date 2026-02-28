import pandas as pd
from realty_model.renderers.base_renderer import BaseRenderer
from realty_model.models.results import FinancialResults
from realty_model.models.property import ProFormaInput


class WaterfallRenderer(BaseRenderer):
    def render(self, wb, results: FinancialResults, inp: ProFormaInput):
        if not inp.waterfall.enabled or results.waterfall_by_year.empty:
            return

        ws = wb.create_sheet("Equity Waterfall")
        ws.sheet_view.showGridLines = False

        wf = inp.waterfall

        self.add_title_row(ws, 1, "Equity Waterfall — LP / GP Distribution", 10)

        # Structure summary
        row = 3
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=4)
        self.style_subheader(ws.cell(row=row, column=1), "WATERFALL STRUCTURE")
        row += 1

        struct_items = [
            ("LP Equity",        f"{wf.lp_equity_pct:.0%}"),
            ("GP Equity",        f"{wf.gp_equity_pct:.0%}"),
            ("LP Preferred Return", f"{wf.preferred_return:.0%}"),
            ("GP Promote",       f"{wf.promote_pct:.0%}"),
        ]
        for label, val in struct_items:
            bg = self.GRAY_BG if row % 2 == 0 else None
            cell_l = ws.cell(row=row, column=1, value=label)
            cell_l.font = self._font(size=10)
            cell_l.alignment = self._align(h='left')
            cell_v = ws.cell(row=row, column=2, value=val)
            cell_v.font = self._font(bold=True, size=10)
            cell_v.alignment = self._align(h='right')
            if bg:
                cell_l.fill = self._fill(bg)
                cell_v.fill = self._fill(bg)
            row += 1

        row += 1

        # Annual distribution table
        df = results.waterfall_by_year
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=7)
        self.style_subheader(ws.cell(row=row, column=1), "ANNUAL DISTRIBUTIONS")
        row += 1

        headers = ['Year', 'Total CF', 'LP Pref Paid', 'LP Pref Accrued',
                   'LP Residual', 'GP Residual', 'LP Total', 'GP Total']
        col_widths = [8, 14, 14, 16, 12, 12, 12, 12]
        for col_idx, (h, w) in enumerate(zip(headers, col_widths), 1):
            cell = ws.cell(row=row, column=col_idx, value=h)
            self.style_header(cell)
            self.set_col_width(ws, col_idx, w)
        row += 1

        for _, wf_row in df.iterrows():
            bg = self.GRAY_BG if row % 2 == 0 else None
            values = [
                wf_row['year'],
                wf_row['total_cash_flow'],
                wf_row['lp_preferred_paid'],
                wf_row['lp_preferred_accrued'],
                wf_row['lp_residual'],
                wf_row['gp_residual'],
                wf_row['lp_total'],
                wf_row['gp_total'],
            ]
            fmts = ['integer', 'currency', 'currency', 'currency',
                    'currency', 'currency', 'currency', 'currency']
            for col_idx, (val, fmt) in enumerate(zip(values, fmts), 1):
                cell = ws.cell(row=row, column=col_idx, value=val)
                cell.font = self._font(size=10)
                cell.alignment = self._align(h='right')
                if bg:
                    cell.fill = self._fill(bg)
                if fmt == 'currency':
                    self.fmt_currency(cell)
                elif fmt == 'integer':
                    self.fmt_integer(cell)
            row += 1

        # Exit waterfall
        row += 1
        exit_data = results.waterfall_exit
        if exit_data:
            ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=4)
            self.style_subheader(ws.cell(row=row, column=1), "EXIT DISTRIBUTION")
            row += 1

            exit_items = [
                ("LP Preferred Catchup",  exit_data.get('lp_pref_catchup', 0)),
                ("LP Return of Capital",  exit_data.get('lp_return_of_capital', 0)),
                ("GP Return of Capital",  exit_data.get('gp_return_of_capital', 0)),
                ("LP Promote Split",      exit_data.get('lp_promote_split', 0)),
                ("GP Promote Split",      exit_data.get('gp_promote_split', 0)),
                ("LP Exit Total",         exit_data.get('lp_exit_total', 0)),
                ("GP Exit Total",         exit_data.get('gp_exit_total', 0)),
            ]
            for label, val in exit_items:
                is_total = 'Total' in label
                bg = self.GRAY_BG if row % 2 == 0 else None
                cell_l = ws.cell(row=row, column=1, value=label)
                cell_l.font = self._font(bold=is_total, size=10)
                cell_l.alignment = self._align(h='left')
                cell_v = ws.cell(row=row, column=2, value=val)
                cell_v.font = self._font(bold=is_total, size=10)
                cell_v.alignment = self._align(h='right')
                self.fmt_currency(cell_v)
                if is_total:
                    cell_l.fill = self._fill(self.DARK_GRAY)
                    cell_v.fill = self._fill(self.DARK_GRAY)
                elif bg:
                    cell_l.fill = self._fill(bg)
                    cell_v.fill = self._fill(bg)
                row += 1
