from typing import List
import numpy_financial as npf

from realty_model.models.results import YearMetrics


def levered_irr(equity_invested: float, cash_flows: List[YearMetrics], exit_proceeds: float) -> float:
    cfs = [-equity_invested]
    for i, cf in enumerate(cash_flows):
        if i < len(cash_flows) - 1:
            cfs.append(cf.cash_flow)
        else:
            cfs.append(cf.cash_flow + exit_proceeds)
    try:
        result = npf.irr(cfs)
        return float(result) if result is not None and not (result != result) else float('nan')
    except Exception:
        return float('nan')


def unlevered_irr(purchase_price: float, noi_flows: List[float], gross_exit_price: float) -> float:
    cfs = [-purchase_price]
    for i, noi in enumerate(noi_flows):
        if i < len(noi_flows) - 1:
            cfs.append(noi)
        else:
            cfs.append(noi + gross_exit_price)
    try:
        result = npf.irr(cfs)
        return float(result) if result is not None and not (result != result) else float('nan')
    except Exception:
        return float('nan')


def npv_calc(
    discount_rate: float,
    equity_invested: float,
    cash_flows: List[float],
    exit_proceeds: float,
) -> float:
    all_cfs = list(cash_flows)
    all_cfs[-1] = all_cfs[-1] + exit_proceeds
    pv = sum(cf / (1 + discount_rate) ** t for t, cf in enumerate(all_cfs, 1))
    return pv - equity_invested


def equity_multiple(equity_invested: float, total_distributions: float, exit_proceeds: float) -> float:
    if equity_invested <= 0:
        return 0.0
    return (total_distributions + exit_proceeds) / equity_invested
