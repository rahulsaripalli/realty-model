from typing import List
from realty_model.models.property import WaterfallTerms
from realty_model.models.results import YearMetrics


def compute_waterfall(
    terms: WaterfallTerms,
    equity_invested: float,
    cash_flows: List[YearMetrics],
    exit_proceeds: float,
) -> dict:
    lp_equity = equity_invested * terms.lp_equity_pct
    gp_equity = equity_invested * terms.gp_equity_pct
    promote = terms.promote_pct
    pref_rate = terms.preferred_return

    lp_cum_pref_unpaid = 0.0
    yearly = []

    for cf in cash_flows:
        distributable = cf.cash_flow

        # Tier 1: LP preferred return (simple, not compounding)
        lp_pref_due = lp_equity * pref_rate + lp_cum_pref_unpaid
        lp_pref_paid = min(max(distributable, 0.0), lp_pref_due)
        lp_cum_pref_unpaid = max(0.0, lp_pref_due - lp_pref_paid)
        distributable -= lp_pref_paid

        # Tier 2: Residual split (GP promote kicks in above pref)
        lp_residual = distributable * (1 - promote) if distributable > 0 else 0.0
        gp_residual = distributable * promote if distributable > 0 else 0.0

        lp_total = lp_pref_paid + lp_residual
        gp_total = gp_residual

        yearly.append({
            'year': cf.year,
            'total_cash_flow': cf.cash_flow,
            'lp_preferred_paid': lp_pref_paid,
            'lp_preferred_accrued': lp_cum_pref_unpaid,
            'lp_residual': lp_residual,
            'gp_residual': gp_residual,
            'lp_total': lp_total,
            'gp_total': gp_total,
        })

    # Exit waterfall
    exit_dist = exit_proceeds

    # Catch up any unpaid preferred
    lp_pref_catch = min(max(exit_dist, 0.0), lp_cum_pref_unpaid)
    exit_dist -= lp_pref_catch

    # Return of capital
    lp_roc = min(max(exit_dist, 0.0), lp_equity)
    exit_dist -= lp_roc
    gp_roc = min(max(exit_dist, 0.0), gp_equity)
    exit_dist -= gp_roc

    # Promote on remaining upside
    lp_promote_split = exit_dist * (1 - promote) if exit_dist > 0 else 0.0
    gp_promote_split = exit_dist * promote if exit_dist > 0 else 0.0

    exit_result = {
        'lp_pref_catchup': lp_pref_catch,
        'lp_return_of_capital': lp_roc,
        'gp_return_of_capital': gp_roc,
        'lp_promote_split': lp_promote_split,
        'gp_promote_split': gp_promote_split,
        'lp_exit_total': lp_pref_catch + lp_roc + lp_promote_split,
        'gp_exit_total': gp_roc + gp_promote_split,
    }

    return {'yearly': yearly, 'exit': exit_result}
