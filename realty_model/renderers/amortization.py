from realty_model.renderers.base_renderer import BaseRenderer
from realty_model.models.results import FinancialResults
from realty_model.models.property import ProFormaInput
from realty_model.config import PALETTE


class AmortizationRenderer(BaseRenderer):
    def render(self, wb, results: FinancialResults, inp: ProFormaInput):
        ws = wb.create_sheet("Amortization Schedule")
        ws.sheet_view.showGridLines = False

        headers = [
            'Month', 'Year', 'Payment', 'Interest', 'Principal',
            'Ending Balance', 'Cum. Interest', 'Cum. Principal'
        ]
        col_widths = [8, 8, 14, 14, 14, 16, 16, 16]

        # Summary mini-table at top
        self.add_title_row(ws, 1, "Loan Amortization Schedule", len(headers))
        ws.row_dimensions[1].height = 28

        amort_df = results.amortization_schedule
        total_interest = amort_df['cumulative_interest'].iloc[-1]
        total_principal = amort_df['cumulative_principal'].iloc[-1]
        loan_amount = inp.financing.loan_amount

        summary_items = [
            ("Loan Amount",        loan_amount,     'currency'),
            ("Interest Rate",      inp.financing.interest_rate, 'percent2'),
            ("Loan Term",          f"{inp.financing.loan_term_years} years", None),
            ("IO Period",          f"{inp.financing.interest_only_years} years", None),
            ("Total Interest Paid",total_interest,  'currency'),
            ("Total Principal",    total_principal, 'currency'),
            ("Total Cost of Debt", total_interest + total_principal, 'currency'),
        ]

        ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=4)
        self.style_subheader(ws.cell(row=2, column=1), "LOAN SUMMARY")

        for i, (label, value, fmt) in enumerate(summary_items):
            r = 3 + i
            bg = self.GRAY_BG if r % 2 == 0 else None
            cell_l = ws.cell(row=r, column=1, value=label)
            cell_l.font = self._font(size=10)
            cell_l.alignment = self._align(h='left')
            if bg:
                cell_l.fill = self._fill(bg)
            cell_v = ws.cell(row=r, column=2, value=value)
            cell_v.font = self._font(bold=True, size=10)
            cell_v.alignment = self._align(h='right')
            if bg:
                cell_v.fill = self._fill(bg)
            if fmt == 'currency':
                self.fmt_currency(cell_v)
            elif fmt == 'percent2':
                self.fmt_percent(cell_v, decimals=2)

        # Headers for schedule
        header_row = 12
        for col_idx, (h, w) in enumerate(zip(headers, col_widths), 1):
            cell = ws.cell(row=header_row, column=col_idx, value=h)
            self.style_header(cell)
            self.set_col_width(ws, col_idx, w)

        ws.freeze_panes = f'A{header_row + 1}'

        # Data rows
        for i, sched_row in amort_df.iterrows():
            r = header_row + 1 + i
            is_year_end = sched_row['month'] % 12 == 0
            bg = self.SEC_BG if is_year_end else (self.GRAY_BG if r % 2 == 0 else None)

            values = [
                sched_row['month'],
                sched_row['year'],
                sched_row['payment'],
                sched_row['interest_paid'],
                sched_row['principal_paid'],
                sched_row['ending_balance'],
                sched_row['cumulative_interest'],
                sched_row['cumulative_principal'],
            ]
            fmts = ['integer', 'integer', 'currency', 'currency', 'currency',
                    'currency', 'currency', 'currency']

            for col_idx, (val, fmt) in enumerate(zip(values, fmts), 1):
                cell = ws.cell(row=r, column=col_idx, value=val)
                cell.font = self._font(bold=is_year_end, size=9)
                cell.alignment = self._align(h='right')
                if bg:
                    cell.fill = self._fill(bg)
                if fmt == 'currency':
                    self.fmt_currency(cell)
                elif fmt == 'integer':
                    self.fmt_integer(cell)
