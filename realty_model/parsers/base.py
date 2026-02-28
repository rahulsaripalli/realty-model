from abc import ABC, abstractmethod
from realty_model.models.property import ProFormaInput


class BaseParser(ABC):
    @abstractmethod
    def parse(self, filepath: str) -> ProFormaInput:
        ...

    def _resolve_pct_or_dollar(self, value: float, base: float) -> float:
        if value < 1.0:
            return value * base
        return value

    def _float(self, raw: dict, key: str, default=None) -> float:
        val = raw.get(key)
        if val is None or str(val).strip() == '':
            if default is not None:
                return float(default)
            raise KeyError(f"Required field missing: {key}")
        try:
            return float(str(val).strip())
        except ValueError:
            raise ValueError(f"Cannot parse '{val}' as a number for field '{key}'")

    def _int(self, raw: dict, key: str, default=None) -> int:
        return int(self._float(raw, key, default))

    def _str(self, raw: dict, key: str, default: str = '') -> str:
        val = raw.get(key)
        if val is None or str(val).strip() == '':
            return default
        return str(val).strip()

    def _build_input(self, raw: dict) -> ProFormaInput:
        from realty_model.models.property import (
            PropertyInfo, FinancingTerms, IncomeAssumptions,
            ExpenseAssumptions, HoldAssumptions, WaterfallTerms, ProFormaInput,
        )

        purchase_price = self._float(raw, 'PROPERTY.purchase_price')

        # Derive loan_amount from ltv_pct if not given
        loan_amount_raw = raw.get('FINANCING.loan_amount', '').strip()
        if loan_amount_raw == '' or loan_amount_raw == '0':
            ltv_pct = self._float(raw, 'FINANCING.ltv_pct', 0.70)
            loan_amount = purchase_price * ltv_pct
        else:
            loan_amount = self._float(raw, 'FINANCING.loan_amount')

        property_info = PropertyInfo(
            address=self._str(raw, 'PROPERTY.address', 'Unknown'),
            property_type=self._str(raw, 'PROPERTY.property_type', 'Multifamily'),
            year_built=self._int(raw, 'PROPERTY.year_built', 2000),
            units=self._int(raw, 'PROPERTY.units', 1),
            square_feet=self._float(raw, 'PROPERTY.square_feet', 0),
            purchase_price=purchase_price,
        )

        financing = FinancingTerms(
            loan_amount=loan_amount,
            interest_rate=self._float(raw, 'FINANCING.interest_rate'),
            loan_term_years=self._int(raw, 'FINANCING.loan_term_years', 30),
            interest_only_years=self._int(raw, 'FINANCING.interest_only_years', 0),
            closing_costs=self._float(raw, 'FINANCING.closing_costs', 0),
        )

        income = IncomeAssumptions(
            gross_scheduled_rent=self._float(raw, 'INCOME.gross_scheduled_rent'),
            vacancy_rate=self._float(raw, 'INCOME.vacancy_rate', 0.05),
            other_income=self._float(raw, 'INCOME.other_income', 0),
            rent_growth_rate=self._float(raw, 'INCOME.rent_growth_rate', 0.03),
        )

        expenses = ExpenseAssumptions(
            property_taxes=self._float(raw, 'EXPENSES.property_taxes', 0),
            insurance=self._float(raw, 'EXPENSES.insurance', 0),
            property_management=self._float(raw, 'EXPENSES.property_management', 0.08),
            maintenance_repairs=self._float(raw, 'EXPENSES.maintenance_repairs', 0),
            utilities=self._float(raw, 'EXPENSES.utilities', 0),
            landscaping_trash=self._float(raw, 'EXPENSES.landscaping_trash', 0),
            capex_reserve=self._float(raw, 'EXPENSES.capex_reserve', 0.05),
            expense_growth_rate=self._float(raw, 'EXPENSES.expense_growth_rate', 0.025),
        )

        assumptions = HoldAssumptions(
            hold_period_years=self._int(raw, 'ASSUMPTIONS.hold_period_years', 10),
            discount_rate=self._float(raw, 'ASSUMPTIONS.discount_rate', 0.08),
            exit_cap_rate=self._float(raw, 'ASSUMPTIONS.exit_cap_rate', 0.055),
            cost_of_sale=self._float(raw, 'ASSUMPTIONS.cost_of_sale', 0.03),
        )

        structure = self._str(raw, 'WATERFALL.structure', 'none').lower()
        waterfall = WaterfallTerms(
            enabled=(structure == 'lp/gp'),
            lp_equity_pct=self._float(raw, 'WATERFALL.lp_equity_pct', 0.90),
            gp_equity_pct=self._float(raw, 'WATERFALL.gp_equity_pct', 0.10),
            preferred_return=self._float(raw, 'WATERFALL.preferred_return', 0.08),
            promote_pct=self._float(raw, 'WATERFALL.promote_pct', 0.20),
        )

        return ProFormaInput(
            property_info=property_info,
            financing=financing,
            income=income,
            expenses=expenses,
            assumptions=assumptions,
            waterfall=waterfall,
        )
