"""
Institutional Excel generation and styling package.
"""

from financial_engine.excel.styles import (
    COLOR_NAVY_HEADER,
    COLOR_HEADER_TEXT,
    COLOR_SUBHEADER_FILL,
    FONT_BLUE_INPUT,
    FONT_BLACK_FORMULA,
    FONT_GREEN_LINK,
    FONT_RED_ALERT,
    FORMAT_AMOUNT,
    FORMAT_PERCENT,
    FORMAT_DAYS,
    FORMAT_DISCOUNT_FACTOR,
    FORMAT_SHARE_PRICE,
)
from financial_engine.excel.builder import (
    InstitutionalExcelBuilder,
    OPENPYXL_AVAILABLE,
)

__all__ = [
    "COLOR_NAVY_HEADER",
    "COLOR_HEADER_TEXT",
    "COLOR_SUBHEADER_FILL",
    "FONT_BLUE_INPUT",
    "FONT_BLACK_FORMULA",
    "FONT_GREEN_LINK",
    "FONT_RED_ALERT",
    "FORMAT_AMOUNT",
    "FORMAT_PERCENT",
    "FORMAT_DAYS",
    "FORMAT_DISCOUNT_FACTOR",
    "FORMAT_SHARE_PRICE",
    "InstitutionalExcelBuilder",
    "OPENPYXL_AVAILABLE",
]
