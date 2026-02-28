from dataclasses import dataclass, field
from typing import List
import pandas as pd


@dataclass
class YearMetrics:
    year: int
    gross_rent: float
    vacancy_loss: float
    egi: float           # Effective Gross Income
    total_expenses: float
    noi: float
    debt_service: float
    debt_service_interest: float
    debt_service_principal: float
    cash_flow: float
    cash_on_cash: float
    cumulative_cash_flow: float
    ending_loan_balance: float


@dataclass
class KeyMetrics:
    purchase_price: float
    loan_amount: float
    equity_invested: float
    ltv: float
    going_in_cap_rate: float
    grm: float
    dscr_year1: float
    break_even_occupancy: float
    cash_on_cash_year1: float
    cash_on_cash_stabilized: float
    levered_irr: float
    unlevered_irr: float
    npv: float
    equity_multiple: float
    total_return: float
    exit_value: float
    exit_proceeds: float


@dataclass
class ExitScenario:
    year: int
    exit_cap_rate: float
    gross_sale_price: float
    cost_of_sale_dollars: float
    net_sale_proceeds: float
    loan_payoff: float
    net_equity: float
    total_distributions: float
    total_profit: float
    equity_multiple: float
    levered_irr: float


@dataclass
class FinancialResults:
    key_metrics: KeyMetrics
    annual_cash_flows: pd.DataFrame
    amortization_schedule: pd.DataFrame
    sensitivity_irr: pd.DataFrame
    sensitivity_coc: pd.DataFrame
    exit_scenarios: List[ExitScenario]
    waterfall_by_year: pd.DataFrame
    waterfall_exit: dict = field(default_factory=dict)
