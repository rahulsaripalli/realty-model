from copy import deepcopy
from typing import List
import pandas as pd

from realty_model.models.property import ProFormaInput
from realty_model.calculators.cashflows import project_cash_flows, compute_exit_proceeds
from realty_model.calculators.debt import loan_balance_at_year
from realty_model.calculators.returns import levered_irr, equity_multiple


def _compute_for_scenario(inp: ProFormaInput, amort_schedule: list, vacancy: float, exit_cap: float):
    inp_copy = deepcopy(inp)
    inp_copy.income.vacancy_rate = vacancy
    inp_copy.assumptions.exit_cap_rate = exit_cap

    equity = (inp_copy.property_info.purchase_price
              - inp_copy.financing.loan_amount
              + inp_copy.financing.closing_costs)

    cfs = project_cash_flows(inp_copy, amort_schedule)
    hold = inp_copy.assumptions.hold_period_years
    lb = loan_balance_at_year(amort_schedule, hold)
    exit_noi = cfs[hold - 1].noi
    exit_data = compute_exit_proceeds(exit_noi, exit_cap, inp_copy.assumptions.cost_of_sale, lb)

    irr = levered_irr(equity, cfs, exit_data['net_equity_proceeds'])
    total_dists = sum(cf.cash_flow for cf in cfs)
    em = equity_multiple(equity, total_dists, exit_data['net_equity_proceeds'])
    coc_y1 = cfs[0].cash_on_cash

    return irr, coc_y1, em


def sensitivity_table_irr(
    inp: ProFormaInput,
    amort_schedule: list,
    cap_rate_range: List[float],
    vacancy_range: List[float],
) -> pd.DataFrame:
    data = {}
    for vac in vacancy_range:
        col_data = []
        for cap in cap_rate_range:
            irr, _, _ = _compute_for_scenario(inp, amort_schedule, vac, cap)
            col_data.append(irr)
        data[f"{vac:.0%} Vac"] = col_data

    df = pd.DataFrame(data, index=[f"{c:.2%}" for c in cap_rate_range])
    df.index.name = "Exit Cap Rate"
    return df


def sensitivity_table_coc(
    inp: ProFormaInput,
    amort_schedule: list,
    cap_rate_range: List[float],
    vacancy_range: List[float],
) -> pd.DataFrame:
    data = {}
    for vac in vacancy_range:
        col_data = []
        for cap in cap_rate_range:
            _, coc, _ = _compute_for_scenario(inp, amort_schedule, vac, cap)
            col_data.append(coc)
        data[f"{vac:.0%} Vac"] = col_data

    df = pd.DataFrame(data, index=[f"{c:.2%}" for c in cap_rate_range])
    df.index.name = "Exit Cap Rate"
    return df
