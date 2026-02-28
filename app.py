import io
import tempfile
from pathlib import Path

import streamlit as st
import pandas as pd

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Rental Property Financial Model",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .metric-card {
        background: #f8f9fa;
        border-left: 4px solid #1F3864;
        border-radius: 6px;
        padding: 14px 18px;
        margin-bottom: 8px;
    }
    .metric-label { font-size: 12px; color: #666; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }
    .metric-value { font-size: 22px; font-weight: 700; color: #1F3864; }
    .good  { border-left-color: #375623; }
    .okay  { border-left-color: #C9A84C; }
    .bad   { border-left-color: #C00000; }
    .good  .metric-value { color: #375623; }
    .okay  .metric-value { color: #C9A84C; }
    .bad   .metric-value { color: #C00000; }
    .section-header {
        font-size: 15px; font-weight: 700; color: #1F3864;
        border-bottom: 2px solid #1F3864;
        padding-bottom: 4px; margin: 20px 0 12px 0;
    }
    div[data-testid="stDownloadButton"] button {
        background-color: #1F3864; color: white;
        font-weight: 600; font-size: 16px;
        padding: 12px 32px; border-radius: 6px;
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────────
def _color(value, good_thresh, bad_thresh, higher_is_better=True):
    if higher_is_better:
        if value >= good_thresh: return "good"
        if value >= bad_thresh:  return "okay"
        return "bad"
    else:
        if value <= good_thresh: return "good"
        if value <= bad_thresh:  return "okay"
        return "bad"


def metric_card(label, value_str, color_class=""):
    st.markdown(f"""
    <div class="metric-card {color_class}">
        <div class="metric-label">{label}</div>
        <div class="metric-value">{value_str}</div>
    </div>""", unsafe_allow_html=True)


def fmt_currency(v):
    if v is None: return "—"
    return f"${v:,.0f}"

def fmt_pct(v, decimals=1):
    if v is None or v != v: return "N/A"
    return f"{v:.{decimals}%}"

def fmt_x(v, decimals=2):
    if v is None: return "—"
    return f"{v:.{decimals}f}x"


# ── Sample CSV ────────────────────────────────────────────────────────────────
SAMPLE_CSV = """section,field,value,notes
PROPERTY,address,"1234 Oak Ave, San Diego CA 92101",Full street address
PROPERTY,property_type,Multifamily,Multifamily / Office / Retail / Industrial
PROPERTY,year_built,1987,Four digit year
PROPERTY,units,12,Number of rentable units
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
"""


# ── Core: run the model ───────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def run_model(file_bytes: bytes, filename: str):
    from realty_model.parsers.csv_parser import CSVParser
    from realty_model.parsers.excel_parser import ExcelParser
    from realty_model.parsers.validator import validate_input
    from realty_model.cli import calculate_all
    from realty_model.renderers.workbook import WorkbookRenderer
    from realty_model.parsers.validator import ValidationError

    suffix = Path(filename).suffix.lower()

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_in:
            tmp_in.write(file_bytes)
            tmp_in.flush()
            tmp_in_path = tmp_in.name

        if suffix == ".csv":
            inp = CSVParser().parse(tmp_in_path)
        else:
            inp = ExcelParser().parse(tmp_in_path)
    except KeyError as e:
        return None, None, [ValidationError("input", f"Missing required field: {e}")], [], None
    except ValueError as e:
        return None, None, [ValidationError("input", str(e))], [], None
    except Exception as e:
        return None, None, [ValidationError("input", f"Could not read file: {e}")], [], None

    errors, warnings = validate_input(inp)
    if errors:
        return None, None, errors, warnings, None

    try:
        results = calculate_all(inp)
    except Exception as e:
        return None, None, [ValidationError("calculation", f"Model error: {e}")], [], None

    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp_out:
        tmp_out_path = tmp_out.name

    WorkbookRenderer().render(results, inp, tmp_out_path)

    with open(tmp_out_path, "rb") as f:
        xlsx_bytes = f.read()

    return results, inp, errors, warnings, xlsx_bytes


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/real-estate.png", width=64)
    st.title("Pro Forma Analyzer")
    st.markdown("Upload your rental property pro forma to generate an investor-grade financial model.")

    st.divider()
    st.markdown("**Step 1 — Download the template**")
    st.download_button(
        "⬇ Download Input Template (CSV)",
        data=SAMPLE_CSV,
        file_name="pro_forma_template.csv",
        mime="text/csv",
        use_container_width=True,
    )

    st.markdown("**Step 2 — Fill in your numbers**")
    st.markdown("Edit the `value` column in the CSV with your property data.")

    st.markdown("**Step 3 — Upload and analyze**")
    uploaded_file = st.file_uploader(
        "Upload completed pro forma",
        type=["csv", "xlsx"],
        label_visibility="collapsed",
    )

    st.divider()
    st.caption("Supports CSV or Excel input. Generates a 6-sheet Excel workbook with IRR, NPV, sensitivity analysis, exit scenarios, and more.")


# ── Main ──────────────────────────────────────────────────────────────────────
st.title("🏢 Rental Property Financial Model")

if uploaded_file is None:
    # Landing state
    st.info("Upload your pro forma CSV or Excel file in the sidebar to get started.")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("#### What you get")
        st.markdown("""
- **Summary Dashboard** with key metrics
- **10-Year Cash Flow** projections
- **Amortization Schedule** (month-by-month)
- **Sensitivity Analysis** (IRR & CoC heat maps)
- **Exit Scenarios** (hold year × cap rate matrix)
- **Equity Waterfall** (LP/GP splits)
        """)
    with col2:
        st.markdown("#### Metrics calculated")
        st.markdown("""
- NOI, Cap Rate, GRM
- DSCR, Break-Even Occupancy
- Levered & Unlevered IRR
- NPV & Equity Multiple
- Cash-on-Cash (Yr 1 & Stabilized)
- LTV, Exit Proceeds
        """)
    with col3:
        st.markdown("#### Input format")
        st.markdown("""
- Simple CSV with `section / field / value` columns
- Sections: PROPERTY, FINANCING, INCOME, EXPENSES, ASSUMPTIONS, WATERFALL
- Download the template from the sidebar
- Also accepts `.xlsx` format
        """)

else:
    file_bytes = uploaded_file.read()

    with st.spinner("Building financial model..."):
        results, inp, errors, warnings, xlsx_bytes = run_model(file_bytes, uploaded_file.name)

    if warnings:
        for w in warnings:
            st.warning(f"**{w.field}**: {w.message}")

    if errors:
        for e in errors:
            st.error(f"**{e.field}**: {e.message}")
        st.stop()

    m = results.key_metrics

    # ── Download button (top) ──────────────────────────────────────────────
    st.success(f"Model built for **{inp.property_info.address}**")

    col_dl, col_info = st.columns([1, 2])
    with col_dl:
        stem = Path(uploaded_file.name).stem
        st.download_button(
            "⬇ Download Excel Model (6 sheets)",
            data=xlsx_bytes,
            file_name=f"{stem}_model.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
    with col_info:
        st.caption(f"**{inp.property_info.property_type}**  ·  {inp.property_info.units} units  ·  "
                   f"{inp.property_info.square_feet:,.0f} SF  ·  Built {inp.property_info.year_built}  ·  "
                   f"{inp.assumptions.hold_period_years}-year hold")

    st.divider()

    # ── Key Metrics ────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">Key Metrics</div>', unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("Purchase Price",   fmt_currency(m.purchase_price))
        metric_card("Equity Invested",  fmt_currency(m.equity_invested))
        metric_card("Loan Amount",      fmt_currency(m.loan_amount))
        metric_card("LTV",              fmt_pct(m.ltv),
                    _color(m.ltv, 0.65, 0.80, higher_is_better=False))
    with c2:
        metric_card("Going-In Cap Rate", fmt_pct(m.going_in_cap_rate, 2))
        metric_card("GRM",               fmt_x(m.grm))
        metric_card("DSCR (Year 1)",     fmt_x(m.dscr_year1),
                    _color(m.dscr_year1, 1.35, 1.10))
        metric_card("Break-Even Occ.",   fmt_pct(m.break_even_occupancy),
                    _color(m.break_even_occupancy, 0.70, 0.85, higher_is_better=False))
    with c3:
        metric_card("Cash-on-Cash (Yr 1)",  fmt_pct(m.cash_on_cash_year1, 2),
                    _color(m.cash_on_cash_year1, 0.08, 0.05))
        metric_card("Cash-on-Cash (Stab.)", fmt_pct(m.cash_on_cash_stabilized, 2),
                    _color(m.cash_on_cash_stabilized, 0.08, 0.05))
        metric_card("Levered IRR",          fmt_pct(m.levered_irr, 2),
                    _color(m.levered_irr, 0.15, 0.10) if m.levered_irr == m.levered_irr else "")
        metric_card("Unlevered IRR",        fmt_pct(m.unlevered_irr, 2),
                    _color(m.unlevered_irr, 0.10, 0.07) if m.unlevered_irr == m.unlevered_irr else "")
    with c4:
        metric_card("Equity Multiple",  fmt_x(m.equity_multiple),
                    _color(m.equity_multiple, 2.0, 1.5))
        metric_card("NPV",              fmt_currency(m.npv),
                    "good" if m.npv > 0 else "bad")
        metric_card("Exit Value",       fmt_currency(m.exit_value))
        metric_card("Net Exit Proceeds",fmt_currency(m.exit_proceeds))

    st.divider()

    # ── 10-Year Cash Flow Table ────────────────────────────────────────────
    st.markdown('<div class="section-header">10-Year Cash Flow Projections</div>', unsafe_allow_html=True)

    cf_df = results.annual_cash_flows.copy()
    display_cols = {
        'Year':                  'Year',
        'Gross Rent':            'Gross Rent',
        'EGI':                   'EGI',
        'Total Expenses':        'Expenses',
        'NOI':                   'NOI',
        'Debt Service':          'Debt Service',
        'Net Cash Flow':         'Net Cash Flow',
        'Cash-on-Cash':          'CoC Return',
        'Ending Loan Balance':   'Loan Balance',
    }
    cf_display = cf_df[list(display_cols.keys())].rename(columns=display_cols)

    def style_cf(df):
        styles = pd.DataFrame('', index=df.index, columns=df.columns)
        for i, val in enumerate(df['Net Cash Flow']):
            color = '#E2EFDA' if val >= 0 else '#FCE4D6'
            styles.loc[i, 'Net Cash Flow'] = f'background-color: {color}'
        return styles

    currency_cols = ['Gross Rent', 'EGI', 'Expenses', 'NOI', 'Debt Service', 'Net Cash Flow', 'Loan Balance']
    pct_cols = ['CoC Return']

    fmt_map = {c: '${:,.0f}' for c in currency_cols}
    fmt_map.update({c: '{:.2%}' for c in pct_cols})

    st.dataframe(
        cf_display.style
            .format(fmt_map)
            .apply(style_cf, axis=None),
        use_container_width=True,
        hide_index=True,
    )

    st.divider()

    # ── Charts ─────────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">Projections</div>', unsafe_allow_html=True)

    ch1, ch2 = st.columns(2)

    with ch1:
        chart_df = cf_df[['Year', 'NOI', 'Net Cash Flow']].set_index('Year')
        st.markdown("**NOI vs Net Cash Flow**")
        st.line_chart(chart_df, use_container_width=True)

    with ch2:
        bar_df = cf_df[['Year', 'EGI', 'Total Expenses']].set_index('Year')
        bar_df.columns = ['EGI', 'Operating Expenses']
        st.markdown("**EGI vs Operating Expenses**")
        st.bar_chart(bar_df, use_container_width=True)

    st.divider()

    # ── Sensitivity ────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">Sensitivity Analysis — Levered IRR</div>', unsafe_allow_html=True)
    st.caption("Exit Cap Rate (rows) × Vacancy Rate (columns) — green = strong, yellow = okay, red = weak")

    sens_df = results.sensitivity_irr.copy()

    def style_irr(v):
        if not isinstance(v, float) or v != v:
            return 'background-color: #f2f2f2'
        if v >= 0.15:   return 'background-color: #E2EFDA; color: #375623; font-weight: bold'
        if v >= 0.10:   return 'background-color: #FFF2CC; color: #7F6000'
        if v >= 0.05:   return 'background-color: #FCE4D6; color: #C00000'
        return 'background-color: #C00000; color: white; font-weight: bold'

    st.dataframe(
        sens_df.style
            .applymap(style_irr)
            .format("{:.2%}"),
        use_container_width=True,
    )

    st.divider()

    # ── Exit Scenarios ─────────────────────────────────────────────────────
    st.markdown('<div class="section-header">Exit Scenarios</div>', unsafe_allow_html=True)

    exit_rows = []
    for s in results.exit_scenarios:
        exit_rows.append({
            'Hold Year':        s.year,
            'Exit Cap Rate':    s.exit_cap_rate,
            'Gross Sale Price': s.gross_sale_price,
            'Net Equity':       s.net_equity,
            'Total Profit':     s.total_profit,
            'Equity Multiple':  s.equity_multiple,
            'Levered IRR':      s.levered_irr,
        })
    exit_df = pd.DataFrame(exit_rows)

    def style_exit_irr(v):
        if not isinstance(v, float) or v != v:
            return ''
        if v >= 0.15: return 'background-color: #E2EFDA; color: #375623'
        if v >= 0.10: return 'background-color: #FFF2CC'
        return 'background-color: #FCE4D6; color: #C00000'

    st.dataframe(
        exit_df.style
            .format({
                'Exit Cap Rate':    '{:.2%}',
                'Gross Sale Price': '${:,.0f}',
                'Net Equity':       '${:,.0f}',
                'Total Profit':     '${:,.0f}',
                'Equity Multiple':  '{:.2f}x',
                'Levered IRR':      '{:.2%}',
            })
            .applymap(style_exit_irr, subset=['Levered IRR']),
        use_container_width=True,
        hide_index=True,
    )

    # ── Waterfall (if enabled) ─────────────────────────────────────────────
    if inp.waterfall.enabled and not results.waterfall_by_year.empty:
        st.divider()
        st.markdown('<div class="section-header">Equity Waterfall — LP / GP</div>', unsafe_allow_html=True)
        st.caption(f"LP {inp.waterfall.lp_equity_pct:.0%} / GP {inp.waterfall.gp_equity_pct:.0%}  ·  "
                   f"{inp.waterfall.preferred_return:.0%} preferred return  ·  "
                   f"{inp.waterfall.promote_pct:.0%} GP promote")
        wf_df = results.waterfall_by_year.copy()
        wf_display = wf_df[['year', 'total_cash_flow', 'lp_total', 'gp_total',
                             'lp_preferred_paid', 'lp_residual', 'gp_residual']]
        wf_display.columns = ['Year', 'Total CF', 'LP Total', 'GP Total',
                               'LP Pref Paid', 'LP Residual', 'GP Residual']
        dollar_cols_wf = ['Total CF', 'LP Total', 'GP Total', 'LP Pref Paid', 'LP Residual', 'GP Residual']
        st.dataframe(
            wf_display.style.format({c: '${:,.0f}' for c in dollar_cols_wf}),
            use_container_width=True,
            hide_index=True,
        )

    # ── Bottom download reminder ───────────────────────────────────────────
    st.divider()
    st.markdown("### Download the full model")
    st.markdown("The Excel workbook includes all 6 sheets with formatting, charts, and conditional coloring.")
    stem = Path(uploaded_file.name).stem
    st.download_button(
        "⬇ Download Excel Model (6 sheets)",
        data=xlsx_bytes,
        file_name=f"{stem}_model.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=False,
    )
