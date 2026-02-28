import math
from typing import List, Tuple


def monthly_payment(principal: float, annual_rate: float, term_years: int) -> float:
    r = annual_rate / 12
    n = term_years * 12
    if r == 0:
        return principal / n if n > 0 else 0.0
    return principal * r * (1 + r) ** n / ((1 + r) ** n - 1)


def build_amortization_schedule(
    principal: float,
    annual_rate: float,
    term_years: int,
    io_years: int = 0,
) -> List[dict]:
    r = annual_rate / 12
    io_months = io_years * 12
    amort_years = term_years - io_years
    pmt_amort = monthly_payment(principal, annual_rate, amort_years) if amort_years > 0 else 0.0

    schedule = []
    balance = principal
    cum_interest = 0.0
    cum_principal = 0.0

    for month in range(1, term_years * 12 + 1):
        interest = balance * r
        if month <= io_months:
            principal_paid = 0.0
            payment = interest
        else:
            principal_paid = max(pmt_amort - interest, 0.0)
            payment = pmt_amort

        balance -= principal_paid
        balance = max(balance, 0.0)
        cum_interest += interest
        cum_principal += principal_paid

        schedule.append({
            'month': month,
            'year': math.ceil(month / 12),
            'payment': payment,
            'interest_paid': interest,
            'principal_paid': principal_paid,
            'ending_balance': balance,
            'cumulative_interest': cum_interest,
            'cumulative_principal': cum_principal,
        })

    return schedule


def annual_debt_service(schedule: List[dict], year: int) -> Tuple[float, float, float]:
    year_rows = [r for r in schedule if r['year'] == year]
    return (
        sum(r['payment'] for r in year_rows),
        sum(r['interest_paid'] for r in year_rows),
        sum(r['principal_paid'] for r in year_rows),
    )


def loan_balance_at_year(schedule: List[dict], year: int) -> float:
    year_rows = [r for r in schedule if r['year'] == year]
    return year_rows[-1]['ending_balance'] if year_rows else 0.0


def dscr(noi: float, annual_ds: float) -> float:
    if annual_ds == 0:
        return float('inf')
    return noi / annual_ds


def ltv(loan_amount: float, value: float) -> float:
    return loan_amount / value if value > 0 else 0.0
