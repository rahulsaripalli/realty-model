from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PropertyInfo:
    address: str
    property_type: str
    year_built: int
    units: int
    square_feet: float
    purchase_price: float


@dataclass
class FinancingTerms:
    loan_amount: float
    interest_rate: float          # annual decimal
    loan_term_years: int
    interest_only_years: int = 0
    closing_costs: float = 0.0


@dataclass
class IncomeAssumptions:
    gross_scheduled_rent: float   # annual
    vacancy_rate: float           # decimal
    other_income: float = 0.0
    rent_growth_rate: float = 0.03


@dataclass
class ExpenseAssumptions:
    property_taxes: float
    insurance: float
    property_management: float    # decimal (<1) or absolute $ (>=1000)
    maintenance_repairs: float
    utilities: float = 0.0
    landscaping_trash: float = 0.0
    capex_reserve: float = 0.0    # decimal (<1) or absolute $ (>=1000)
    expense_growth_rate: float = 0.025


@dataclass
class HoldAssumptions:
    hold_period_years: int = 10
    discount_rate: float = 0.08
    exit_cap_rate: float = 0.055
    cost_of_sale: float = 0.03


@dataclass
class WaterfallTerms:
    enabled: bool = False
    lp_equity_pct: float = 0.90
    gp_equity_pct: float = 0.10
    preferred_return: float = 0.08
    promote_pct: float = 0.20


@dataclass
class ProFormaInput:
    property_info: PropertyInfo
    financing: FinancingTerms
    income: IncomeAssumptions
    expenses: ExpenseAssumptions
    assumptions: HoldAssumptions
    waterfall: WaterfallTerms = field(default_factory=WaterfallTerms)
