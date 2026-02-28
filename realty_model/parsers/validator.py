from dataclasses import dataclass
from typing import List, Tuple
from realty_model.models.property import ProFormaInput


@dataclass
class ValidationError:
    field: str
    message: str


@dataclass
class ValidationWarning:
    field: str
    message: str


def validate_input(inp: ProFormaInput) -> Tuple[List[ValidationError], List[ValidationWarning]]:
    errors: List[ValidationError] = []
    warnings: List[ValidationWarning] = []

    p = inp.property_info
    f = inp.financing
    i = inp.income
    e = inp.expenses
    a = inp.assumptions

    # Hard errors
    if p.purchase_price <= 0:
        errors.append(ValidationError("purchase_price", "Must be greater than 0"))
    if f.loan_amount < 0:
        errors.append(ValidationError("loan_amount", "Cannot be negative"))
    if f.loan_amount > p.purchase_price:
        errors.append(ValidationError("loan_amount", "Loan amount exceeds purchase price"))
    if f.interest_rate <= 0 or f.interest_rate > 0.30:
        errors.append(ValidationError("interest_rate", f"Value {f.interest_rate:.4f} is outside 0-30% range"))
    if f.loan_term_years <= 0:
        errors.append(ValidationError("loan_term_years", "Must be positive"))
    if f.interest_only_years >= f.loan_term_years:
        errors.append(ValidationError("interest_only_years", "IO years must be less than loan term"))
    if i.gross_scheduled_rent <= 0:
        errors.append(ValidationError("gross_scheduled_rent", "Must be greater than 0"))
    if not (0 <= i.vacancy_rate < 1):
        errors.append(ValidationError("vacancy_rate", "Must be between 0 and 1"))
    if a.hold_period_years <= 0:
        errors.append(ValidationError("hold_period_years", "Must be positive"))
    if a.exit_cap_rate <= 0:
        errors.append(ValidationError("exit_cap_rate", "Must be greater than 0"))

    # Warnings
    if i.rent_growth_rate > 0.08:
        warnings.append(ValidationWarning("rent_growth_rate", f"{i.rent_growth_rate:.1%} annual rent growth is aggressive"))
    if a.hold_period_years > 30:
        warnings.append(ValidationWarning("hold_period_years", "Hold period > 30 years may produce unreliable projections"))

    egi_approx = i.gross_scheduled_rent * (1 - i.vacancy_rate) + i.other_income
    going_in_cap = 0.0
    if p.purchase_price > 0:
        mgmt = e.property_management * egi_approx if e.property_management < 1.0 else e.property_management
        capex = e.capex_reserve * egi_approx if e.capex_reserve < 1.0 else e.capex_reserve
        approx_noi = (egi_approx - e.property_taxes - e.insurance - mgmt
                      - e.maintenance_repairs - e.utilities - e.landscaping_trash - capex)
        going_in_cap = approx_noi / p.purchase_price

    if going_in_cap > 0 and a.exit_cap_rate < going_in_cap * 0.6:
        warnings.append(ValidationWarning(
            "exit_cap_rate",
            f"Exit cap rate {a.exit_cap_rate:.2%} is very aggressive vs going-in cap ~{going_in_cap:.2%}"
        ))

    return errors, warnings
