"""
ExcelStyles — centralised colour and formatting constants for the workbook.
"""
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter


class ExcelStyles:
    # ── Colour constants (ARGB hex strings) ──────────────────────────────────
    BLUE        = "FF0000FF"   # historical inputs / hard-coded assumptions
    BLACK       = "FF000000"   # same-sheet formula cells
    GREEN       = "FF008000"   # cross-sheet link formulas
    RED_FILL    = "FFFF0000"   # fail / mismatch banner background
    GREEN_FILL  = "FF00FF00"   # pass / balanced banner background

    # ── Number formats ───────────────────────────────────────────────────────
    currency_format = "#,##0.00"
    pct_format      = "0.00%"

    # ── Pre-built fills ──────────────────────────────────────────────────────
    @classmethod
    def _make_fill(cls, argb: str) -> PatternFill:
        return PatternFill(fill_type="solid", fgColor=argb)

    red_fill_obj   = None   # populated on first call to avoid class-level side-effects
    green_fill_obj = None

    @classmethod
    def _ensure_fills(cls):
        if cls.red_fill_obj is None:
            cls.red_fill_obj   = cls._make_fill(cls.RED_FILL)
            cls.green_fill_obj = cls._make_fill(cls.GREEN_FILL)

    # ── Helper: apply a header row style ────────────────────────────────────
    @classmethod
    def header_style(cls, ws, row: int, fill_color: str):
        """Bold, centred, filled background for every used cell in *row*."""
        fill = cls._make_fill(fill_color)
        for cell in ws[row]:
            cell.font      = Font(bold=True, color="FF000000")
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.fill      = fill

    # ── Helper: apply font colour to a single cell ───────────────────────────
    @staticmethod
    def apply_font(cell, color: str, bold: bool = False, size: int = 10):
        cell.font = Font(color=color, bold=bold, size=size)

    # ── Helper: thin border ──────────────────────────────────────────────────
    @staticmethod
    def thin_border() -> Border:
        thin = Side(style="thin")
        return Border(left=thin, right=thin, top=thin, bottom=thin)

    # ── Helper: apply currency format ────────────────────────────────────────
    @staticmethod
    def fmt_currency(cell):
        cell.number_format = ExcelStyles.currency_format

    @staticmethod
    def fmt_pct(cell):
        cell.number_format = ExcelStyles.pct_format
