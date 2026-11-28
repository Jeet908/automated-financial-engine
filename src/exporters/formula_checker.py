"""
formula_checker.py
FormulaChecker scans an Excel workbook for formula errors.
"""
from dataclasses import dataclass, field
from typing import List, Tuple
import openpyxl


@dataclass
class FormulaCheckResult:
    error_cells: List[Tuple[str, str, str]] = field(default_factory=list)
    has_errors: bool = False
    total_formulas_scanned: int = 0


class FormulaChecker:
    ERROR_TOKENS = ["#REF!", "#DIV/0!", "#VALUE!", "#NAME?", "#N/A", "#NUM!"]

    def __init__(self):
        pass

    def scan(self, xlsx_path: str) -> FormulaCheckResult:
        """
        Scans xlsx_path for broken formula patterns using string matching.
        """
        wb = openpyxl.load_workbook(xlsx_path, data_only=False)
        error_cells = []
        total_formulas = 0

        for sheetname in wb.sheetnames:
            ws = wb[sheetname]
            for row in ws.iter_rows():
                for cell in row:
                    val = cell.value
                    if isinstance(val, str) and val.startswith("="):
                        total_formulas += 1
                        for err in self.ERROR_TOKENS:
                            if err in val:
                                error_cells.append((sheetname, cell.coordinate, val))
                                break

        return FormulaCheckResult(
            error_cells=error_cells,
            has_errors=len(error_cells) > 0,
            total_formulas_scanned=total_formulas
        )
