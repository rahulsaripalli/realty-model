import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd


def build_parser():
    p = argparse.ArgumentParser(
        prog='realty-model',
        description='Generate investor-grade real estate financial models from pro forma inputs.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  realty-model input.csv
  realty-model input.xlsx --output deal_analysis.xlsx
  realty-model input.csv --verbose
  realty-model --template > my_template.csv
  realty-model input.csv --validate-only
        """,
    )
    p.add_argument('input', nargs='?', help='Path to input CSV or XLSX file')
    p.add_argument('-o', '--output', default=None,
                   help='Output Excel path (default: <input_stem>_model.xlsx)')
    p.add_argument('--discount-rate', type=float, default=None,
                   help='Override discount rate for NPV (e.g. 0.08)')
    p.add_argument('--hold-years', type=int, default=None,
                   help='Override hold period in years')
    p.add_argument('--template', action='store_true',
                   help='Print a blank CSV input template to stdout and exit')
    p.add_argument('--validate-only', action='store_true',
                   help='Parse and validate input, then exit without generating output')
    p.add_argument('--verbose', '-v', action='store_true',
                   help='Print key metrics to the terminal after generation')
    return p


def run():
    parser = build_parser()
    args = parser.parse_args()

    if args.template:
        _print_template()
        sys.exit(0)

    if not args.input:
        parser.print_help()
        sys.exit(1)

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"ERROR: File not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    ext = input_path.suffix.lower()
    if ext == '.csv':
        from realty_model.parsers.csv_parser import CSVParser
        inp = CSVParser().parse(str(input_path))
    elif ext in ('.xlsx', '.xls'):
        from realty_model.parsers.excel_parser import ExcelParser
        inp = ExcelParser().parse(str(input_path))
    else:
        print(f"ERROR: Unsupported file type '{ext}'. Use .csv or .xlsx", file=sys.stderr)
        sys.exit(1)

    # CLI overrides
    if args.discount_rate is not None:
        inp.assumptions.discount_rate = args.discount_rate
    if args.hold_years is not None:
        inp.assumptions.hold_period_years = args.hold_years

    # Validate
    from realty_model.parsers.validator import validate_input
    errors, warnings = validate_input(inp)
    for w in warnings:
        print(f"WARNING [{w.field}]: {w.message}")
    if errors:
        for e in errors:
            print(f"ERROR [{e.field}]: {e.message}", file=sys.stderr)
        sys.exit(1)

    if args.validate_only:
        print("Validation passed.")
        sys.exit(0)

    print("Building financial model...")
    results = calculate_all(inp)

    output_path = args.output or _default_output_path(str(input_path))

    from realty_model.renderers.workbook import WorkbookRenderer
    WorkbookRenderer().render(results, inp, output_path)

    print(f"Model saved: {output_path}")

    if args.verbose:
        _print_summary(results)


def calculate_all(inp):
    from realty_model.calculators import debt as debt_calc
    from realty_model.calculators import cashflows as cf_calc
    from realty_model.calculators import returns as ret_calc
    from realty_model.calculators import sensitivity as sens_calc
    from realty_model.calculators import waterfall as wf_calc
    from realty_model.models.results import (
        FinancialResults, KeyMetrics, ExitScenario,
    )

    # Build amortization schedule
    amort = debt_calc.build_amortization_schedule(
        principal=inp.financing.loan_amount,
        annual_rate=inp.financing.interest_rate,
        term_years=inp.financing.loan_term_years,
        io_years=inp.financing.interest_only_years,
    )

    # Project annual cash flows
    annual_cfs = cf_calc.project_cash_flows(inp, amort)
    equity = (inp.property_info.purchase_price
              - inp.financing.loan_amount
              + inp.financing.closing_costs)

    hold = inp.assumptions.hold_period_years

    # Exit at end of hold period at base cap rate
    lb_hold = debt_calc.loan_balance_at_year(amort, hold)
    exit_noi = annual_cfs[hold - 1].noi
    exit_base = cf_calc.compute_exit_proceeds(
        exit_noi,
        inp.assumptions.exit_cap_rate,
        inp.assumptions.cost_of_sale,
        lb_hold,
    )

    # Return metrics
    lev_irr = ret_calc.levered_irr(equity, annual_cfs, exit_base['net_equity_proceeds'])
    noi_list = [y.noi for y in annual_cfs]
    unlev_irr = ret_calc.unlevered_irr(
        inp.property_info.purchase_price, noi_list, exit_base['gross_sale_price']
    )
    cf_list = [y.cash_flow for y in annual_cfs]
    npv = ret_calc.npv_calc(
        inp.assumptions.discount_rate, equity, cf_list, exit_base['net_equity_proceeds']
    )
    total_dists = sum(cf_list)
    em = ret_calc.equity_multiple(equity, total_dists, exit_base['net_equity_proceeds'])

    # Key metrics
    year1_noi = annual_cfs[0].noi
    going_in_cap = cf_calc.going_in_cap_rate(year1_noi, inp.property_info.purchase_price)
    grm_val = cf_calc.grm(inp.property_info.purchase_price, inp.income.gross_scheduled_rent)
    ds1_total, _, _ = debt_calc.annual_debt_service(amort, 1)
    dscr_y1 = debt_calc.dscr(year1_noi, ds1_total)
    beo = cf_calc.break_even_occupancy(
        annual_cfs[0].total_expenses, ds1_total, inp.income.gross_scheduled_rent
    )
    stab_idx = min(2, hold - 1)  # year 3 or last if hold < 3

    key = KeyMetrics(
        purchase_price=inp.property_info.purchase_price,
        loan_amount=inp.financing.loan_amount,
        equity_invested=equity,
        ltv=debt_calc.ltv(inp.financing.loan_amount, inp.property_info.purchase_price),
        going_in_cap_rate=going_in_cap,
        grm=grm_val,
        dscr_year1=dscr_y1,
        break_even_occupancy=beo,
        cash_on_cash_year1=annual_cfs[0].cash_on_cash,
        cash_on_cash_stabilized=annual_cfs[stab_idx].cash_on_cash,
        levered_irr=lev_irr,
        unlevered_irr=unlev_irr,
        npv=npv,
        equity_multiple=em,
        total_return=total_dists + exit_base['net_equity_proceeds'],
        exit_value=exit_base['gross_sale_price'],
        exit_proceeds=exit_base['net_equity_proceeds'],
    )

    # Sensitivity tables
    base_cap = inp.assumptions.exit_cap_rate
    cap_range = [round(base_cap + delta, 4)
                 for delta in np.arange(-0.015, 0.0175, 0.0025)]
    base_vac = inp.income.vacancy_rate
    vac_range = [max(0.0, min(0.99, round(base_vac + delta, 2)))
                 for delta in [-0.05, -0.03, 0.0, 0.03, 0.05, 0.08]]
    vac_range = sorted(set(vac_range))

    sens_irr = sens_calc.sensitivity_table_irr(inp, amort, cap_range, vac_range)
    sens_coc = sens_calc.sensitivity_table_coc(inp, amort, cap_range, vac_range)

    # Exit scenario matrix
    exit_years = [y for y in [3, 5, 7, 10] if y <= hold]
    if hold not in exit_years:
        exit_years.append(hold)
    exit_caps = [round(base_cap + d, 4)
                 for d in [-0.010, -0.005, 0.0, 0.005, 0.010]]

    exit_scenarios = []
    for yr in exit_years:
        lb_yr = debt_calc.loan_balance_at_year(amort, yr)
        noi_yr = annual_cfs[yr - 1].noi
        for cap in exit_caps:
            ex = cf_calc.compute_exit_proceeds(noi_yr, cap, inp.assumptions.cost_of_sale, lb_yr)
            cfs_to_yr = annual_cfs[:yr]
            irr = ret_calc.levered_irr(equity, cfs_to_yr, ex['net_equity_proceeds'])
            dists = sum(y.cash_flow for y in cfs_to_yr)
            em_s = ret_calc.equity_multiple(equity, dists, ex['net_equity_proceeds'])
            exit_scenarios.append(ExitScenario(
                year=yr,
                exit_cap_rate=cap,
                gross_sale_price=ex['gross_sale_price'],
                cost_of_sale_dollars=ex['cost_of_sale_dollars'],
                net_sale_proceeds=ex['net_sale_proceeds'],
                loan_payoff=lb_yr,
                net_equity=ex['net_equity_proceeds'],
                total_distributions=dists,
                total_profit=dists + ex['net_equity_proceeds'] - equity,
                equity_multiple=em_s,
                levered_irr=irr,
            ))

    # Waterfall
    wf_df = pd.DataFrame()
    wf_exit = {}
    if inp.waterfall.enabled:
        wf_result = wf_calc.compute_waterfall(
            inp.waterfall, equity, annual_cfs, exit_base['net_equity_proceeds']
        )
        wf_df = pd.DataFrame(wf_result['yearly'])
        wf_exit = wf_result['exit']

    # Build annual cash flow DataFrame with extra columns
    annual_df = pd.DataFrame([
        {
            'Year':                  y.year,
            'Gross Rent':            y.gross_rent,
            'Vacancy Loss':          y.vacancy_loss,
            'EGI':                   y.egi,
            'Total Expenses':        y.total_expenses,
            'NOI':                   y.noi,
            'Debt Service':          y.debt_service,
            'Debt Service Interest': y.debt_service_interest,
            'Debt Service Principal': y.debt_service_principal,
            'Net Cash Flow':         y.cash_flow,
            'Cash-on-Cash':          y.cash_on_cash,
            'Cumulative Cash Flow':  y.cumulative_cash_flow,
            'Ending Loan Balance':   y.ending_loan_balance,
        }
        for y in annual_cfs
    ])

    amort_df = pd.DataFrame(amort)

    return FinancialResults(
        key_metrics=key,
        annual_cash_flows=annual_df,
        amortization_schedule=amort_df,
        sensitivity_irr=sens_irr,
        sensitivity_coc=sens_coc,
        exit_scenarios=exit_scenarios,
        waterfall_by_year=wf_df,
        waterfall_exit=wf_exit,
    )


def _default_output_path(input_path: str) -> str:
    p = Path(input_path)
    return str(p.parent / f"{p.stem}_model.xlsx")


def _print_summary(results):
    m = results.key_metrics
    print()
    print("=" * 42)
    print("  KEY METRICS")
    print("=" * 42)
    print(f"  Purchase Price:       ${m.purchase_price:>14,.0f}")
    print(f"  Equity Invested:      ${m.equity_invested:>14,.0f}")
    print(f"  LTV:                  {m.ltv:>14.1%}")
    print(f"  Going-In Cap Rate:    {m.going_in_cap_rate:>14.2%}")
    print(f"  GRM:                  {m.grm:>14.2f}x")
    print(f"  DSCR (Year 1):        {m.dscr_year1:>14.2f}x")
    print(f"  Break-Even Occ.:      {m.break_even_occupancy:>14.1%}")
    print(f"  Cash-on-Cash (Yr 1):  {m.cash_on_cash_year1:>14.2%}")
    print(f"  Levered IRR:          {m.levered_irr:>14.2%}" if m.levered_irr == m.levered_irr
          else f"  Levered IRR:          {'N/A':>14}")
    print(f"  Equity Multiple:      {m.equity_multiple:>14.2f}x")
    print(f"  NPV:                  ${m.npv:>14,.0f}")
    print(f"  Exit Value:           ${m.exit_value:>14,.0f}")
    print("=" * 42)


def _print_template():
    print("""section,field,value,notes
PROPERTY,address,"1234 Oak Ave, City ST 00000",Full street address
PROPERTY,property_type,Multifamily,Multifamily / Office / Retail / Industrial
PROPERTY,year_built,1990,Four digit year
PROPERTY,units,12,Number of units (use 1 for single tenant)
PROPERTY,square_feet,8400,Total rentable SF
PROPERTY,purchase_price,2400000,Total acquisition cost
FINANCING,loan_amount,1680000,Leave blank to derive from ltv_pct
FINANCING,ltv_pct,0.70,Used if loan_amount is blank
FINANCING,interest_rate,0.0675,Annual rate as decimal (6.75% = 0.0675)
FINANCING,loan_term_years,30,Amortization years
FINANCING,interest_only_years,0,IO period before amortization begins
FINANCING,closing_costs,48000,Lender fees + title + escrow
INCOME,gross_scheduled_rent,192000,Annual gross rent at 100% occupancy
INCOME,vacancy_rate,0.05,Decimal (5% = 0.05)
INCOME,other_income,6000,Parking / laundry / storage (annual)
INCOME,rent_growth_rate,0.03,Annual rent escalation
EXPENSES,property_taxes,22000,Annual
EXPENSES,insurance,8400,Annual hazard insurance
EXPENSES,property_management,0.08,Decimal of EGI or dollar amount if over 1000
EXPENSES,maintenance_repairs,12000,Annual
EXPENSES,utilities,4800,Landlord paid annual
EXPENSES,landscaping_trash,3600,Annual
EXPENSES,capex_reserve,0.05,Decimal of EGI or dollar amount if over 1000
EXPENSES,expense_growth_rate,0.025,Annual expense escalation
ASSUMPTIONS,hold_period_years,10,Projection horizon
ASSUMPTIONS,discount_rate,0.08,For NPV calculation
ASSUMPTIONS,exit_cap_rate,0.0550,Assumed sale cap rate
ASSUMPTIONS,cost_of_sale,0.03,Broker + closing costs at exit
WATERFALL,structure,none,Set to LP/GP to enable waterfall sheet
WATERFALL,lp_equity_pct,0.90,LP share of equity
WATERFALL,gp_equity_pct,0.10,GP share of equity
WATERFALL,preferred_return,0.08,LP preferred return hurdle
WATERFALL,promote_pct,0.20,GP promote above preferred return
""")


if __name__ == '__main__':
    run()
