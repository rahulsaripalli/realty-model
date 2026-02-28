from openpyxl import Workbook

from realty_model.models.results import FinancialResults
from realty_model.models.property import ProFormaInput
from realty_model.renderers.summary import SummaryRenderer
from realty_model.renderers.cashflows import AnnualCashFlowRenderer
from realty_model.renderers.amortization import AmortizationRenderer
from realty_model.renderers.sensitivity import SensitivityRenderer
from realty_model.renderers.exit_scenarios import ExitScenariosRenderer
from realty_model.renderers.waterfall import WaterfallRenderer


class WorkbookRenderer:
    def render(self, results: FinancialResults, inp: ProFormaInput, output_path: str) -> str:
        wb = Workbook()
        wb.remove(wb.active)  # Remove default empty sheet

        SummaryRenderer().render(wb, results, inp)
        AnnualCashFlowRenderer().render(wb, results, inp)
        AmortizationRenderer().render(wb, results, inp)
        SensitivityRenderer().render(wb, results, inp)
        ExitScenariosRenderer().render(wb, results, inp)

        if inp.waterfall.enabled:
            WaterfallRenderer().render(wb, results, inp)

        # Tab colors
        tab_colors = {
            "Summary Dashboard":   "1F3864",
            "Annual Cash Flows":   "375623",
            "Amortization Schedule": "2F5496",
            "Sensitivity Analysis": "C9A84C",
            "Exit Scenarios":      "7030A0",
            "Equity Waterfall":    "C00000",
        }
        for sheet_name, color in tab_colors.items():
            if sheet_name in wb.sheetnames:
                wb[sheet_name].sheet_properties.tabColor = color

        # Document properties
        wb.properties.title = f"Investment Analysis - {inp.property_info.address}"
        wb.properties.creator = "RealtyModel CLI"
        wb.properties.description = (
            f"Investor-grade financial model for {inp.property_info.address}"
        )

        try:
            wb.save(output_path)
        except PermissionError:
            raise PermissionError(
                f"Cannot write to '{output_path}'. Is the file open in Excel?"
            )

        return output_path
