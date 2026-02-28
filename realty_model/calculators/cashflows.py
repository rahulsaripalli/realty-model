from typing import List
from realty_model.models.property import ProFormaInput
from realty_model.models.results import YearMetrics
from realty_model.calculators.debt import annual_debt_service, loan_balance_at_year


def _resolve_pct_or_dollar(value: float, base: float) -> float:
    if value < 1.0:
        return value * base
    return value


def compute_egi(gross_rent: float, vacancy_rate: float, other_income: float) -> float:
    return gross_rent * (1 - vacancy_rate) + other_income


def compute_total_expenses(
    taxes: float,
    insurance: float,
    management: float,
    maintenance: float,
    utilities: float,
    landscaping: float,
    capex: float,
    egi: float,
    is_management_pct: bool,
    is_capex_pct: bool,
) -> float:
    mgmt_dollar = egi * management if is_management_pct else management
    capex_dollar = egi * capex if is_capex_pct else capex
    return taxes + insurance + mgmt_dollar + maintenance + utilities + landscaping + capex_dollar


def compute_noi(egi: float, expenses: float) -> float:
    return egi - expenses


def going_in_cap_rate(noi_year1: float, purchase_price: float) -> float:
    return noi_year1 / purchase_price if purchase_price > 0 else 0.0


def grm(purchase_price: float, gross_scheduled_rent: float) -> float:
    return purchase_price / gross_scheduled_rent if gross_scheduled_rent > 0 else 0.0


def break_even_occupancy(total_expenses: float, debt_service: float, gross_rent: float) -> float:
    if gross_rent == 0:
        return 1.0
    return (total_expenses + debt_service) / gross_rent


def project_cash_flows(inp: ProFormaInput, amort_schedule: List[dict]) -> List[YearMetrics]:
    equity = (inp.property_info.purchase_price
              - inp.financing.loan_amount
              + inp.financing.closing_costs)

    exp = inp.expenses
    is_mgmt_pct = exp.property_management < 1.0
    is_capex_pct = exp.capex_reserve < 1.0

    base_rent = inp.income.gross_scheduled_rent
    base_other = inp.income.other_income

    # Fixed expense base (grows with expense_growth_rate)
    base_fixed = (exp.property_taxes + exp.insurance
                  + exp.maintenance_repairs + exp.utilities + exp.landscaping_trash)

    cumulative_cf = 0.0
    results = []

    for year in range(1, inp.assumptions.hold_period_years + 1):
        rg = (1 + inp.income.rent_growth_rate) ** (year - 1)
        eg = (1 + exp.expense_growth_rate) ** (year - 1)

        gross_rent = base_rent * rg
        other_income = base_other * rg
        egi = compute_egi(gross_rent, inp.income.vacancy_rate, other_income)

        fixed_exp = base_fixed * eg
        mgmt = exp.property_management if is_mgmt_pct else exp.property_management * eg
        capex = exp.capex_reserve if is_capex_pct else exp.capex_reserve * eg

        total_exp = compute_total_expenses(
            taxes=exp.property_taxes * eg,
            insurance=exp.insurance * eg,
            management=mgmt,
            maintenance=exp.maintenance_repairs * eg,
            utilities=exp.utilities * eg,
            landscaping=exp.landscaping_trash * eg,
            capex=capex,
            egi=egi,
            is_management_pct=is_mgmt_pct,
            is_capex_pct=is_capex_pct,
        )

        noi = compute_noi(egi, total_exp)
        ds_total, ds_interest, ds_principal = annual_debt_service(amort_schedule, year)
        cf = noi - ds_total
        coc = cf / equity if equity > 0 else 0.0
        cumulative_cf += cf
        lb = loan_balance_at_year(amort_schedule, year)

        results.append(YearMetrics(
            year=year,
            gross_rent=gross_rent,
            vacancy_loss=gross_rent * inp.income.vacancy_rate,
            egi=egi,
            total_expenses=total_exp,
            noi=noi,
            debt_service=ds_total,
            debt_service_interest=ds_interest,
            debt_service_principal=ds_principal,
            cash_flow=cf,
            cash_on_cash=coc,
            cumulative_cash_flow=cumulative_cf,
            ending_loan_balance=lb,
        ))

    return results


def compute_exit_proceeds(
    noi_at_exit: float,
    exit_cap_rate: float,
    cost_of_sale: float,
    loan_balance: float,
) -> dict:
    if exit_cap_rate <= 0:
        gross_value = 0.0
    else:
        gross_value = noi_at_exit / exit_cap_rate
    sale_costs = gross_value * cost_of_sale
    net_proceeds = gross_value - sale_costs
    net_equity = net_proceeds - loan_balance
    return {
        'gross_sale_price': gross_value,
        'cost_of_sale_dollars': sale_costs,
        'net_sale_proceeds': net_proceeds,
        'loan_payoff': loan_balance,
        'net_equity_proceeds': net_equity,
    }
