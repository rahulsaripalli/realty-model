"""
Shared cell-address constants so every renderer references
the same locations in Assumptions and Annual Cash Flows.
"""

# ── Assumptions sheet — column B row numbers ────────────────────────────────
ASM = "Assumptions"

# PROPERTY
ASM_PURCHASE_PRICE_ROW = 4
ASM_LOAN_AMOUNT_ROW    = 12
ASM_INTEREST_RATE_ROW  = 13
ASM_LOAN_TERM_ROW      = 14
ASM_IO_YEARS_ROW       = 15
ASM_CLOSING_COSTS_ROW  = 16
ASM_EQUITY_ROW         = 17   # formula: =B4-B12+B16
ASM_LTV_ROW            = 18   # formula: =B12/B4

# INCOME
ASM_GROSS_RENT_ROW     = 21
ASM_VACANCY_ROW        = 22
ASM_OTHER_INCOME_ROW   = 23
ASM_RENT_GROWTH_ROW    = 24

# EXPENSES
ASM_TAXES_ROW          = 27
ASM_INSURANCE_ROW      = 28
ASM_MGMT_ROW           = 29
ASM_MAINTENANCE_ROW    = 30
ASM_UTILITIES_ROW      = 31
ASM_LANDSCAPING_ROW    = 32
ASM_CAPEX_ROW          = 33
ASM_EXP_GROWTH_ROW     = 34

# HOLD ASSUMPTIONS
ASM_HOLD_YEARS_ROW     = 37
ASM_DISCOUNT_RATE_ROW  = 38
ASM_EXIT_CAP_ROW       = 39
ASM_COST_OF_SALE_ROW   = 40


def asm(row: int) -> str:
    """Absolute reference to Assumptions column B."""
    return f"'{ASM}'!$B${row}"


# ── Annual Cash Flows sheet — row numbers ────────────────────────────────────
CF_SHEET = "Annual Cash Flows"

CF_ROW_YEAR_HDR        = 2
CF_ROW_GROSS_RENT      = 4
CF_ROW_VACANCY         = 5
CF_ROW_OTHER_INCOME    = 6
CF_ROW_EGI             = 8
CF_ROW_TAXES           = 10
CF_ROW_INSURANCE       = 11
CF_ROW_MGMT            = 12
CF_ROW_MAINTENANCE     = 13
CF_ROW_UTILITIES       = 14
CF_ROW_LANDSCAPING     = 15
CF_ROW_CAPEX           = 16
CF_ROW_TOTAL_EXPENSES  = 18
CF_ROW_NOI             = 20
CF_ROW_DS_INTEREST     = 22
CF_ROW_DS_PRINCIPAL    = 23
CF_ROW_DS_TOTAL        = 24
CF_ROW_CASH_FLOW       = 26
CF_ROW_COC             = 27
CF_ROW_DSCR            = 28
CF_ROW_LOAN_BALANCE    = 30
CF_ROW_CUM_CF          = 31
CF_ROW_EXIT_VALUE      = 33
CF_ROW_SALE_COSTS      = 34
CF_ROW_NET_PROCEEDS    = 35
CF_ROW_NET_EQUITY      = 36
CF_ROW_TOTAL_RETURN    = 37
CF_ROW_EQUITY_MULTIPLE = 38

# Hidden IRR / NPV array row (below visible data)
CF_ROW_IRR_ARRAY       = 42


# ── Amortization Schedule sheet — column indices ─────────────────────────────
AMORT_SHEET      = "Amortization Schedule"
AMORT_HDR_ROW    = 12       # header row
AMORT_DATA_START = 13       # first data row
AMORT_COL_MONTH  = "A"      # col A: month number (1-360)
AMORT_COL_YEAR   = "B"      # col B: year number (1-30)
AMORT_COL_PMT    = "C"      # col C: payment
AMORT_COL_INT    = "D"      # col D: interest paid
AMORT_COL_PRIN   = "E"      # col E: principal paid
AMORT_COL_BAL    = "F"      # col F: ending balance
