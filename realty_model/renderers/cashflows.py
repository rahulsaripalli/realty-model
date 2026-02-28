from realty_model.renderers.base_renderer import BaseRenderer
from realty_model.models.results import FinancialResults
from realty_model.models.property import ProFormaInput


class AnnualCashFlowRenderer(BaseRenderer):
    def render(self, wb, results: FinancialResults, inp: ProFormaInput):
        ws = wb.create_sheet("Annual Cash Flows")
        ws.sheet_view.showGridLines = False

        hold = inp.assumptions.hold_period_years
        n_cols = hold + 1   # label col + year cols

        # Title
        self.add_title_row(ws, 1, "Annual Cash Flow Projections", n_cols)

        # Column widths
        self.set_col_width(ws, 1, 30)
        for col in range(2, n_cols + 1):
            self.set_col_width(ws, col, 15)

        # Year headers row 2
        ws.cell(row=2, column=1, value="").fill = self._fill(self.HDR_BG)
        for y in range(1, hold + 1):
            cell = ws.cell(row=2, column=y + 1, value=f"Year {y}")
            self.style_header(cell)

        ws.freeze_panes = 'B3'

        cf_df = results.annual_cash_flows

        def year_val(col_name, year_idx):
            return cf_df.loc[year_idx, col_name] if year_idx < len(cf_df) else None

        row = 3

        # Helper to write a data row
        def write_row(label, col_name=None, values=None, fmt='currency',
                      bold=False, bg=None, section=False, indent=0, negate=False):
            nonlocal row
            if section:
                ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=n_cols)
                self.style_section(ws.cell(row=row, column=1), label)
                row += 1
                return

            cell_l = ws.cell(row=row, column=1, value=label)
            alt_bg = self.GRAY_BG if row % 2 == 0 else None
            effective_bg = bg or alt_bg
            cell_l.font = self._font(bold=bold, size=10)
            cell_l.alignment = self._align(h='left', indent=indent)
            if effective_bg:
                cell_l.fill = self._fill(effective_bg)

            for y in range(hold):
                if values is not None:
                    val = values[y]
                elif col_name is not None:
                    val = cf_df.iloc[y][col_name]
                else:
                    val = None

                if negate and val is not None:
                    val = -abs(val)

                cell_v = ws.cell(row=row, column=y + 2, value=val)
                cell_v.font = self._font(bold=bold, size=10)
                cell_v.alignment = self._align(h='right')
                if effective_bg:
                    cell_v.fill = self._fill(effective_bg)
                if fmt == 'currency':
                    self.fmt_currency(cell_v)
                elif fmt == 'percent':
                    self.fmt_percent(cell_v, decimals=2)
                elif fmt == 'number':
                    self.fmt_number(cell_v)

            row += 1

        # INCOME
        write_row("INCOME", section=True)
        write_row("Gross Scheduled Rent", col_name='Gross Rent')
        write_row("Vacancy Loss", col_name='Vacancy Loss', negate=True)
        write_row("Other Income", values=[
            cf_df.iloc[y]['EGI'] - cf_df.iloc[y]['Gross Rent'] * (1 - inp.income.vacancy_rate)
            for y in range(hold)
        ])
        write_row("Effective Gross Income (EGI)", col_name='EGI', bold=True,
                  bg=self.DARK_GRAY)

        # EXPENSES
        write_row("OPERATING EXPENSES", section=True)
        write_row("Total Operating Expenses", col_name='Total Expenses', bold=True,
                  bg=self.DARK_GRAY, negate=True)

        # NOI
        write_row("NET OPERATING INCOME", section=True)
        write_row("NOI", col_name='NOI', bold=True, bg=self.GREEN_BG)

        # DEBT SERVICE
        write_row("DEBT SERVICE", section=True)
        write_row("Interest",   col_name='Debt Service Interest', negate=True)
        write_row("Principal",  col_name='Debt Service Principal', negate=True)
        write_row("Total Debt Service", col_name='Debt Service', bold=True,
                  bg=self.DARK_GRAY, negate=True)

        # CASH FLOW
        write_row("CASH FLOW", section=True)
        cf_vals = list(cf_df['Net Cash Flow'])
        cf_bgs = [self.GREEN_BG if v >= 0 else self.RED_BG for v in cf_vals]
        # Write cash flow row with per-cell coloring
        label = "Net Cash Flow (After Debt)"
        cell_l = ws.cell(row=row, column=1, value=label)
        cell_l.font = self._font(bold=True, size=10)
        cell_l.alignment = self._align(h='left')
        for y in range(hold):
            val = cf_vals[y]
            cell_v = ws.cell(row=row, column=y + 2, value=val)
            cell_v.font = self._font(bold=True, size=10,
                                     color=self.GREEN_FG if val >= 0 else self.RED_FG)
            cell_v.alignment = self._align(h='right')
            cell_v.fill = self._fill(self.GREEN_BG if val >= 0 else self.RED_BG)
            self.fmt_currency(cell_v)
        row += 1

        write_row("Cash-on-Cash Return", col_name='Cash-on-Cash', fmt='percent', bold=True)
        write_row("DSCR", values=[
            round(cf_df.iloc[y]['NOI'] / cf_df.iloc[y]['Debt Service'], 2)
            if cf_df.iloc[y]['Debt Service'] > 0 else 0
            for y in range(hold)
        ], fmt='number')

        # BALANCE SHEET
        write_row("EQUITY POSITION", section=True)
        write_row("Ending Loan Balance", col_name='Ending Loan Balance', negate=False)
        write_row("Cumulative Cash Flow", col_name='Cumulative Cash Flow')

        # EXIT ANALYSIS
        write_row("EXIT ANALYSIS (Base Scenario)", section=True)
        exit_cap = inp.assumptions.exit_cap_rate

        exit_vals = []
        for y in range(hold):
            noi_y = cf_df.iloc[y]['NOI']
            exit_vals.append(noi_y / exit_cap if exit_cap > 0 else 0)

        write_row("Projected Exit Value (at base cap)", values=exit_vals, fmt='currency', bold=False)

        equity_invested = (inp.property_info.purchase_price
                           - inp.financing.loan_amount
                           + inp.financing.closing_costs)
        em_vals = []
        for y in range(hold):
            cum_cf = cf_df.iloc[y]['Cumulative Cash Flow']
            proj_exit = exit_vals[y]
            lb = cf_df.iloc[y]['Ending Loan Balance']
            net_exit = proj_exit * (1 - inp.assumptions.cost_of_sale) - lb
            em = (cum_cf + net_exit) / equity_invested if equity_invested > 0 else 0
            em_vals.append(em)
        write_row("Equity Multiple (cumulative)", values=em_vals, fmt='number')
