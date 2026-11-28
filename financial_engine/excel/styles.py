"""
Institutional Wall Street styling, typography, color codes, and cell formats.
"""

from typing import Dict, Any

# Colors (Hex without #)
COLOR_NAVY_HEADER = "1F4E79"
COLOR_HEADER_TEXT = "FFFFFF"
COLOR_SUBHEADER_FILL = "DDEBF7"
COLOR_ACCENT = "2F5597"

# Font colors
FONT_BLUE_INPUT = "0000FF"      # Blue = hardcoded inputs
FONT_BLACK_FORMULA = "000000"   # Black = formulas
FONT_GREEN_LINK = "008000"      # Green = cross-sheet links
FONT_RED_ALERT = "C00000"       # Red = checks / errors

# Fills
FILL_LIGHT_YELLOW = "FFF2CC"    # Focus / work cells
FILL_LIGHT_GREEN = "C6EFCE"     # Success / pass
FILL_LIGHT_RED = "FFC7CE"       # Discrepancy / fail
FILL_LIGHT_GREY = "F2F2F2"      # Inactive / padding

# Number Format Strings
FORMAT_AMOUNT = '#,##0.0;(#,##0.0);"-"'
FORMAT_INTEGER = '#,##0;(#,##0);"-"'
FORMAT_PERCENT = "0.0%"
FORMAT_PERCENT_2DEC = "0.00%"
FORMAT_DAYS = "0"
FORMAT_DISCOUNT_FACTOR = "0.000"
FORMAT_SHARE_PRICE = '"Rs " #,##0'
FORMAT_SHARE_PRICE_USD = '"$"#,##0.00'
FORMAT_MULTIPLE = '0.0"x"'
