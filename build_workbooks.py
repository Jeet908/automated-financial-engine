import os
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

os.makedirs("assets", exist_ok=True)

# Styling constants
FONT_TITLE = Font(name="Calibri", size=14, bold=True)
FONT_SECTION = Font(name="Calibri", size=11, bold=True, color="1F4E79")
FONT_HEADER = Font(name="Calibri", size=11, bold=True)
FONT_LABEL = Font(name="Calibri", size=11)
FONT_BOLD = Font(name="Calibri", size=11, bold=True)
FONT_BLUE = Font(name="Calibri", size=11, color="0000FF") # Hardcoded inputs
FONT_BLACK = Font(name="Calibri", size=11, color="000000") # Calculated formulas
FONT_MUTED = Font(name="Calibri", size=9, italic=True, color="595959")

FILL_HEADER = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
FILL_SECTION = PatternFill(start_color="F2F2F2", end_color="F2F2F2", fill_type="solid")
FILL_YELLOW = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")
FILL_GREEN = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
FILL_BLUE_MODULE = PatternFill(start_color="9BC2E6", end_color="9BC2E6", fill_type="solid")
FILL_GREY_MODULE = PatternFill(start_color="E7E6E6", end_color="E7E6E6", fill_type="solid")

BORDER_THIN = Border(
    left=Side(style='thin', color='D9D9D9'),
    right=Side(style='thin', color='D9D9D9'),
    top=Side(style='thin', color='D9D9D9'),
    bottom=Side(style='thin', color='D9D9D9')
)
BORDER_TOP_THIN_BOTTOM_DOUBLE = Border(
    top=Side(style='thin', color='000000'),
    bottom=Side(style='double', color='000000')
)

FMT_AMOUNT = "#,##0.0"
FMT_PERCENT = "0.0%"
FMT_DAYS = "0"
FMT_FACTOR = "0.000"
FMT_SHARE = "#,##0"

COL_YEARS = {
    'C': 'FY23A',
    'D': 'FY24A',
    'E': 'FY25A',
    'F': 'FY26E',
    'G': 'FY27E',
    'H': 'FY28E',
    'I': 'FY29E',
    'J': 'FY30E'
}

def init_workbook():
    wb = openpyxl.Workbook()
    default_sheet = wb.active
    
    # Sheet order: Tutor Map, Inputs, IS, BS, CF, Schedules, DCF, Checks
    sheets = ["Tutor Map", "Inputs", "IS", "BS", "CF", "Schedules", "DCF", "Checks"]
    ws_dict = {}
    for s in sheets:
        ws_dict[s] = wb.create_sheet(title=s)
    wb.remove(default_sheet)
    
    for name, ws in ws_dict.items():
        ws.views.sheetView[0].showGridLines = True
        ws.column_dimensions['A'].width = 3
        ws.column_dimensions['B'].width = 38
        for col_letter in COL_YEARS.keys():
            ws.column_dimensions[col_letter].width = 13
        
        # Row 1 Title & Row 2 Currency
        if name != "Tutor Map":
            ws['B1'] = f"Kaveri Foods Ltd - {name}"
            ws['B1'].font = FONT_TITLE
            ws['B2'] = "INR crore"
            ws['B2'].font = FONT_MUTED
            
            # Row 3 Year headers
            for col_letter, yr in COL_YEARS.items():
                cell = ws[f"{col_letter}3"]
                cell.value = yr
                cell.font = FONT_HEADER
                cell.alignment = Alignment(horizontal="right")
                cell.fill = FILL_HEADER
                cell.border = BORDER_THIN

    return wb, ws_dict

def populate_tutor_map(ws, current_module=0, current_step="0.1 Meet the practice company", target_link="Inputs!E5"):
    ws['B1'] = "Excel Financial Modelling Tutor"
    ws['B1'].font = FONT_TITLE
    ws['B2'] = "Tutor Map: Kaveri Foods financial model"
    ws['B2'].font = FONT_BOLD
    
    modules = [
        "0 Setup", "1 Historicals", "2 Ratios", "3 Assumptions",
        "4 Rev to EBITDA", "5 Working Capital", "6 Fixed Assets", "7 Debt",
        "8 Profit", "9 Cash Flow", "10 Balance Sheet", "11 DCF", "12 Sensitivity"
    ]
    # Row 4: Columns B to N
    for idx, mod_name in enumerate(modules):
        col_letter = get_column_letter(idx + 2) # Col B is 2
        cell = ws[f"{col_letter}4"]
        cell.value = mod_name
        cell.font = FONT_BOLD
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = BORDER_THIN
        ws.column_dimensions[col_letter].width = 16
        
        if idx < current_module:
            cell.fill = FILL_GREEN
        elif idx == current_module:
            cell.fill = FILL_BLUE_MODULE
        else:
            cell.fill = FILL_GREY_MODULE
            
    ws['B6'] = f"Now: {current_step}"
    ws['B6'].font = FONT_BOLD
    
    ws['B7'] = f'=HYPERLINK("#{target_link}", "Go to {target_link}")'
    ws['B7'].font = Font(name="Calibri", size=11, color="0563C1", underline="single")

def populate_inputs_structure(ws, is_solution=False):
    labels = {
        4: "[Historical income statement]",
        5: "Revenue",
        6: "Cost of goods sold (COGS)",
        8: "Employee costs",
        9: "Other expenses",
        11: "Depreciation",
        13: "Interest",
        15: "Tax",
        17: "Dividends paid",
        19: "[Historical balance sheet]",
        21: "Cash",
        22: "Receivables",
        23: "Inventory",
        24: "Net fixed assets (net block)",
        26: "Payables",
        27: "Debt",
        28: "Share capital",
        29: "Retained earnings",
        31: "[Projection assumptions]",
        32: "Revenue growth",
        33: "COGS % revenue",
        34: "Employee costs % revenue",
        35: "Other expenses % revenue",
        36: "Receivable days",
        37: "Inventory days (on COGS)",
        38: "Payable days (on COGS)",
        39: "Capex % revenue",
        40: "Depreciation % opening net block",
        41: "Interest rate on debt",
        42: "Debt repayment",
        43: "Tax rate",
        44: "Dividend payout",
        46: "[Valuation inputs]",
        47: "Risk-free rate (practice value, 10Y G-sec)",
        48: "Beta",
        49: "Equity risk premium",
        50: "Pre-tax cost of debt",
        51: "Debt weight in capital (D/V)",
        52: "Terminal growth rate",
        53: "Shares outstanding (crore)"
    }
    
    for r, txt in labels.items():
        cell = ws[f"B{r}"]
        cell.value = txt
        if txt.startswith("["):
            cell.font = FONT_SECTION
            cell.fill = FILL_SECTION
        else:
            cell.font = FONT_LABEL

    # Historical IS
    hist_is = {
        5: [1000.0, 1120.0, 1243.2],
        6: [585.0, 649.6, 716.1],
        8: [100.0, 109.8, 120.6],
        9: [122.0, 134.4, 147.9],
        11: [38.0, 40.0, 43.0],
        13: [28.4, 25.7, 23.0],
        15: [31.9, 40.4, 48.5],
        17: [23.7, 30.0, 36.0]
    }
    for r, vals in hist_is.items():
        for i, val in enumerate(vals):
            col = ['C', 'D', 'E'][i]
            c = ws[f"{col}{r}"]
            c.value = val
            c.font = FONT_BLUE
            c.number_format = FMT_AMOUNT

    # Historical BS
    hist_bs = {
        21: [222.8, 239.8, 269.5],
        22: [123.3, 138.1, 153.3],
        23: [80.1, 89.0, 98.1],
        24: [400.0, 430.0, 465.0],
        26: [96.2, 106.8, 117.7],
        27: [300.0, 270.0, 240.0],
        28: [50.0, 50.0, 50.0],
        29: [380.0, 470.1, 578.2]
    }
    for r, vals in hist_bs.items():
        for i, val in enumerate(vals):
            col = ['C', 'D', 'E'][i]
            c = ws[f"{col}{r}"]
            c.value = val
            c.font = FONT_BLUE
            c.number_format = FMT_AMOUNT

    # Projections F:J (Rows 34 to 44)
    proj_inputs = {
        34: (0.097, FMT_PERCENT),
        35: (0.119, FMT_PERCENT),
        36: (45, FMT_DAYS),
        37: (50, FMT_DAYS),
        38: (60, FMT_DAYS),
        39: (0.05, FMT_PERCENT),
        40: (0.10, FMT_PERCENT),
        41: (0.09, FMT_PERCENT),
        42: (30.0, FMT_AMOUNT),
        43: (0.2517, FMT_PERCENT),
        44: (0.25, FMT_PERCENT)
    }
    for r, (val, fmt) in proj_inputs.items():
        for col in ['F', 'G', 'H', 'I', 'J']:
            c = ws[f"{col}{r}"]
            c.value = val
            c.font = FONT_BLUE
            c.number_format = fmt

    # Valuation inputs in C47:C53
    val_inputs = {
        47: (0.065, FMT_PERCENT),
        48: (0.9, "0.0"),
        49: (0.07, FMT_PERCENT),
        50: (0.09, FMT_PERCENT),
        51: (0.20, FMT_PERCENT),
        52: (0.05, FMT_PERCENT),
        53: (10.0, "#,##0.0")
    }
    for r, (val, fmt) in val_inputs.items():
        c = ws[f"C{r}"]
        c.value = val
        c.font = FONT_BLUE
        c.number_format = fmt

    # Rows 32 and 33
    if is_solution:
        # Module 3 fills these
        growth_vals = [0.12, 0.11, 0.10, 0.09, 0.08]
        for idx, col in enumerate(['F', 'G', 'H', 'I', 'J']):
            c = ws[f"{col}32"]
            c.value = growth_vals[idx]
            c.font = FONT_BLUE
            c.number_format = FMT_PERCENT
        
        ws['F33'] = "=1-AVERAGE(IS!C20:E20)"
        ws['F33'].font = FONT_BLACK
        ws['F33'].number_format = FMT_PERCENT
        for col, prev in [('G','F'), ('H','G'), ('I','H'), ('J','I')]:
            c = ws[f"{col}33"]
            c.value = f"={prev}33"
            c.font = FONT_BLACK
            c.number_format = FMT_PERCENT

def setup_template_sheets(ws_dict):
    # IS labels
    is_labels = {
        4: "[Income statement]",
        5: "Revenue",
        6: "COGS",
        7: "Gross profit",
        8: "Employee costs",
        9: "Other expenses",
        10: "EBITDA",
        11: "Depreciation",
        12: "EBIT",
        13: "Interest",
        14: "Profit before tax",
        15: "Tax",
        16: "Net profit (PAT)",
        18: "[Ratios]",
        19: "Revenue growth",
        20: "Gross margin",
        21: "EBITDA margin",
        22: "Net profit margin"
    }
    for r, txt in is_labels.items():
        c = ws_dict['IS'][f"B{r}"]
        c.value = txt
        if txt.startswith("["):
            c.font = FONT_SECTION
            c.fill = FILL_SECTION
        elif txt in ["Gross profit", "EBITDA", "EBIT", "Profit before tax", "Net profit (PAT)"]:
            c.font = FONT_BOLD
        else:
            c.font = FONT_LABEL

    # BS labels
    bs_labels = {
        4: "[Assets]",
        5: "Cash",
        6: "Receivables",
        7: "Inventory",
        8: "Net fixed assets",
        9: "Total assets",
        10: "[Liabilities and equity]",
        11: "Payables",
        12: "Debt",
        13: "Share capital",
        14: "Retained earnings",
        15: "Total liabilities and equity",
        17: "Balance check (must be 0)"
    }
    for r, txt in bs_labels.items():
        c = ws_dict['BS'][f"B{r}"]
        c.value = txt
        if txt.startswith("["):
            c.font = FONT_SECTION
            c.fill = FILL_SECTION
        elif txt in ["Total assets", "Total liabilities and equity", "Balance check (must be 0)"]:
            c.font = FONT_BOLD
        else:
            c.font = FONT_LABEL

    # CF labels
    cf_labels = {
        4: "[Operating]",
        5: "Net profit",
        6: "Add: depreciation",
        7: "Less: increase in working capital",
        8: "Cash from operations",
        9: "[Investing]",
        10: "Capex",
        11: "Cash from investing",
        12: "[Financing]",
        13: "Debt repayment",
        14: "Dividends",
        15: "Cash from financing",
        17: "Net change in cash",
        18: "Opening cash",
        19: "Closing cash"
    }
    for r, txt in cf_labels.items():
        c = ws_dict['CF'][f"B{r}"]
        c.value = txt
        if txt.startswith("["):
            c.font = FONT_SECTION
            c.fill = FILL_SECTION
        elif txt in ["Cash from operations", "Cash from investing", "Cash from financing", "Net change in cash", "Closing cash"]:
            c.font = FONT_BOLD
        else:
            c.font = FONT_LABEL

    # Schedules labels
    sched_labels = {
        4: "[Working capital]",
        5: "Receivable days",
        6: "Inventory days",
        7: "Payable days",
        9: "Receivables",
        10: "Inventory",
        11: "Payables",
        12: "Net working capital",
        13: "Change in working capital",
        15: "[Fixed assets]",
        16: "Opening net block",
        17: "Capex",
        18: "Depreciation",
        19: "Closing net block",
        21: "[Debt]",
        22: "Opening debt",
        23: "Repayment",
        24: "Closing debt",
        25: "Interest"
    }
    for r, txt in sched_labels.items():
        c = ws_dict['Schedules'][f"B{r}"]
        c.value = txt
        if txt.startswith("["):
            c.font = FONT_SECTION
            c.fill = FILL_SECTION
        elif txt in ["Net working capital", "Change in working capital", "Closing net block", "Closing debt"]:
            c.font = FONT_BOLD
        else:
            c.font = FONT_LABEL

    # DCF labels
    dcf_labels = {
        4: "[Free cash flow]",
        5: "EBIT",
        6: "Tax on EBIT",
        7: "NOPAT",
        8: "Add: depreciation",
        9: "Less: capex",
        10: "Less: increase in working capital",
        11: "Free cash flow to firm (FCFF)",
        13: "[Discount rate]",
        14: "Cost of equity",
        15: "After-tax cost of debt",
        16: "WACC",
        23: "[Discounting]",
        24: "Year number",
        25: "Discount factor",
        26: "PV of FCFF",
        28: "[Valuation]",
        29: "Sum of PV of FCFF",
        30: "Terminal value",
        31: "PV of terminal value",
        32: "Enterprise value",
        33: "Less: debt (FY25)",
        34: "Add: cash (FY25)",
        35: "Equity value",
        36: "Shares outstanding (crore)",
        37: "Value per share (Rs)",
        39: "[Sensitivity: value per share (Rs)]",
        40: "WACC down, terminal growth across",
        41: "Terminal growth →",
        42: "WACC ↓"
    }
    for r, txt in dcf_labels.items():
        c = ws_dict['DCF'][f"B{r}"]
        c.value = txt
        if txt.startswith("["):
            c.font = FONT_SECTION
            c.fill = FILL_SECTION
        elif txt in ["NOPAT", "Free cash flow to firm (FCFF)", "WACC", "Enterprise value", "Equity value", "Value per share (Rs)"]:
            c.font = FONT_BOLD
        else:
            c.font = FONT_LABEL
            
    # DCF pre-fill
    # F24:J24 = 1, 2, 3, 4, 5 (blue)
    for idx, col in enumerate(['F', 'G', 'H', 'I', 'J']):
        c = ws_dict['DCF'][f"{col}24"]
        c.value = idx + 1
        c.font = FONT_BLUE
        c.alignment = Alignment(horizontal="right")
        
    # D41:H41 = 4%, 4.5%, 5%, 5.5%, 6% (blue)
    rates = [0.04, 0.045, 0.05, 0.055, 0.06]
    for idx, col in enumerate(['D', 'E', 'F', 'G', 'H']):
        c = ws_dict['DCF'][f"{col}41"]
        c.value = rates[idx]
        c.font = FONT_BLUE
        c.number_format = FMT_PERCENT
        c.alignment = Alignment(horizontal="right")
        
    # C42:C46
    ws_dict['DCF']['C42'] = "=$C$16-0.02"
    ws_dict['DCF']['C43'] = "=$C$16-0.01"
    ws_dict['DCF']['C44'] = "=$C$16"
    ws_dict['DCF']['C45'] = "=$C$16+0.01"
    ws_dict['DCF']['C46'] = "=$C$16+0.02"
    for r in range(42, 47):
        c = ws_dict['DCF'][f"C{r}"]
        c.font = FONT_BLACK
        c.number_format = FMT_PERCENT

    # Checks labels
    ws_dict['Checks']['B4'] = "[Model checks]"
    ws_dict['Checks']['B4'].font = FONT_SECTION
    ws_dict['Checks']['B4'].fill = FILL_SECTION
    ws_dict['Checks']['B5'] = "Balance sheet balances every year"
    ws_dict['Checks']['B5'].font = FONT_LABEL

def build_starter_workbook():
    wb, ws_dict = init_workbook()
    populate_tutor_map(ws_dict['Tutor Map'], current_module=0, current_step="0.1 Meet the practice company", target_link="Inputs!E5")
    populate_inputs_structure(ws_dict['Inputs'], is_solution=False)
    setup_template_sheets(ws_dict)
    
    # Highlight Inputs!E5 yellow as step 0.1 specifies
    ws_dict['Inputs']['E5'].fill = FILL_YELLOW
    
    wb.save("assets/kaveri-starter.xlsx")
    print("Saved assets/kaveri-starter.xlsx")

def build_solution_workbook():
    wb, ws_dict = init_workbook()
    populate_tutor_map(ws_dict['Tutor Map'], current_module=12, current_step="Course Complete · 89 of 89 Steps Done", target_link="DCF!F44")
    populate_inputs_structure(ws_dict['Inputs'], is_solution=True)
    setup_template_sheets(ws_dict)
    
    # --- IS Sheet ---
    # 1.1 - 1.3 Links
    for col in ['C', 'D', 'E']:
        ws_dict['IS'][f"{col}5"] = f"=Inputs!{col}5"
        ws_dict['IS'][f"{col}6"] = f"=Inputs!{col}6"
        ws_dict['IS'][f"{col}8"] = f"=Inputs!{col}8"
        ws_dict['IS'][f"{col}9"] = f"=Inputs!{col}9"
        ws_dict['IS'][f"{col}11"] = f"=Inputs!{col}11"
        ws_dict['IS'][f"{col}13"] = f"=Inputs!{col}13"
        ws_dict['IS'][f"{col}15"] = f"=Inputs!{col}15"
        
    # 4.1 - 4.6 Projections
    ws_dict['IS']['F5'] = "=E5*(1+Inputs!F32)"
    for col, prev in [('G','F'), ('H','G'), ('I','H'), ('J','I')]:
        ws_dict['IS'][f"{col}5"] = f"={prev}5*(1+Inputs!{col}32)"
        
    for col in ['F', 'G', 'H', 'I', 'J']:
        ws_dict['IS'][f"{col}6"] = f"={col}5*Inputs!{col}33"
        ws_dict['IS'][f"{col}8"] = f"={col}5*Inputs!{col}34"
        ws_dict['IS'][f"{col}9"] = f"={col}5*Inputs!{col}35"
        ws_dict['IS'][f"{col}11"] = f"=Schedules!{col}18" # 6.6
        ws_dict['IS'][f"{col}13"] = f"=Schedules!{col}25" # 7.6
        ws_dict['IS'][f"{col}15"] = f"={col}14*Inputs!{col}43" # 8.3
        
    # 1.4 - 1.8 & 4.4, 4.7, 8.1, 8.2, 8.4 Calculations
    for col in ['C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']:
        ws_dict['IS'][f"{col}7"] = f"={col}5-{col}6"
        ws_dict['IS'][f"{col}10"] = f"={col}7-{col}8-{col}9"
        ws_dict['IS'][f"{col}12"] = f"={col}10-{col}11"
        ws_dict['IS'][f"{col}14"] = f"={col}12-{col}13"
        ws_dict['IS'][f"{col}16"] = f"={col}14-{col}15"

    # 2.1 - 2.4 & 8.5 Ratios
    for col, prev in [('D','C'), ('E','D'), ('F','E'), ('G','F'), ('H','G'), ('I','H'), ('J','I')]:
        ws_dict['IS'][f"{col}19"] = f"={col}5/{prev}5-1"
    for col in ['C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']:
        ws_dict['IS'][f"{col}20"] = f"={col}7/{col}5"
        ws_dict['IS'][f"{col}21"] = f"={col}10/{col}5"
        ws_dict['IS'][f"{col}22"] = f"={col}16/{col}5"

    for r in range(5, 17):
        for col in ['C','D','E','F','G','H','I','J']:
            ws_dict['IS'][f"{col}{r}"].number_format = FMT_AMOUNT
            ws_dict['IS'][f"{col}{r}"].font = FONT_BLACK
    for r in range(19, 23):
        for col in ['C','D','E','F','G','H','I','J']:
            ws_dict['IS'][f"{col}{r}"].number_format = FMT_PERCENT
            ws_dict['IS'][f"{col}{r}"].font = FONT_BLACK

    # --- Schedules Sheet ---
    # 2.5 - 2.7 Historical days
    for col in ['C', 'D', 'E']:
        ws_dict['Schedules'][f"{col}5"] = f"=Inputs!{col}22/IS!{col}5*365"
        ws_dict['Schedules'][f"{col}6"] = f"=Inputs!{col}23/IS!{col}6*365"
        ws_dict['Schedules'][f"{col}7"] = f"=Inputs!{col}26/IS!{col}6*365"
    # 5.1 Projected days
    for col in ['F', 'G', 'H', 'I', 'J']:
        ws_dict['Schedules'][f"{col}5"] = f"=Inputs!{col}36"
        ws_dict['Schedules'][f"{col}6"] = f"=Inputs!{col}37"
        ws_dict['Schedules'][f"{col}7"] = f"=Inputs!{col}38"
        
    # 5.2 Historical balances
    for col in ['C', 'D', 'E']:
        ws_dict['Schedules'][f"{col}9"] = f"=Inputs!{col}22"
        ws_dict['Schedules'][f"{col}10"] = f"=Inputs!{col}23"
        ws_dict['Schedules'][f"{col}11"] = f"=Inputs!{col}26"
    # 5.3 - 5.5 Projected balances
    for col in ['F', 'G', 'H', 'I', 'J']:
        ws_dict['Schedules'][f"{col}9"] = f"={col}5/365*IS!{col}5"
        ws_dict['Schedules'][f"{col}10"] = f"={col}6/365*IS!{col}6"
        ws_dict['Schedules'][f"{col}11"] = f"={col}7/365*IS!{col}6"
        
    # 5.6 - 5.7 Working Capital
    for col in ['C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']:
        ws_dict['Schedules'][f"{col}12"] = f"={col}9+{col}10-{col}11"
    for col, prev in [('D','C'), ('E','D'), ('F','E'), ('G','F'), ('H','G'), ('I','H'), ('J','I')]:
        ws_dict['Schedules'][f"{col}13"] = f"={col}12-{prev}12"

    # 6.1 Historical net block
    for col in ['C', 'D', 'E']:
        ws_dict['Schedules'][f"{col}19"] = f"=Inputs!{col}24"
    # 6.2 - 6.5 Fixed assets roll forward
    ws_dict['Schedules']['F16'] = "=E19"
    for col, prev in [('G','F'), ('H','G'), ('I','H'), ('J','I')]:
        ws_dict['Schedules'][f"{col}16"] = f"={prev}19"
    for col in ['F', 'G', 'H', 'I', 'J']:
        ws_dict['Schedules'][f"{col}17"] = f"=IS!{col}5*Inputs!{col}39"
        ws_dict['Schedules'][f"{col}18"] = f"={col}16*Inputs!{col}40"
        ws_dict['Schedules'][f"{col}19"] = f"={col}16+{col}17-{col}18"

    # 7.1 Historical debt
    for col in ['C', 'D', 'E']:
        ws_dict['Schedules'][f"{col}24"] = f"=Inputs!{col}27"
    # 7.2 - 7.5 Debt roll forward
    ws_dict['Schedules']['F22'] = "=E24"
    for col, prev in [('G','F'), ('H','G'), ('I','H'), ('J','I')]:
        ws_dict['Schedules'][f"{col}22"] = f"={prev}24"
    for col in ['F', 'G', 'H', 'I', 'J']:
        ws_dict['Schedules'][f"{col}23"] = f"=Inputs!{col}42"
        ws_dict['Schedules'][f"{col}24"] = f"={col}22-{col}23"
        ws_dict['Schedules'][f"{col}25"] = f"=AVERAGE({col}22,{col}24)*Inputs!{col}41"

    for r in range(5, 8):
        for col in ['C','D','E','F','G','H','I','J']:
            ws_dict['Schedules'][f"{col}{r}"].number_format = FMT_DAYS
            ws_dict['Schedules'][f"{col}{r}"].font = FONT_BLACK
    for r in [9, 10, 11, 12, 13, 16, 17, 18, 19, 22, 23, 24, 25]:
        for col in ['C','D','E','F','G','H','I','J']:
            ws_dict['Schedules'][f"{col}{r}"].number_format = FMT_AMOUNT
            ws_dict['Schedules'][f"{col}{r}"].font = FONT_BLACK

    # --- CF Sheet ---
    # Module 9 Cash Flow
    for col in ['F', 'G', 'H', 'I', 'J']:
        ws_dict['CF'][f"{col}5"] = f"=IS!{col}16"
        ws_dict['CF'][f"{col}6"] = f"=IS!{col}11"
        ws_dict['CF'][f"{col}7"] = f"=-Schedules!{col}13"
        ws_dict['CF'][f"{col}8"] = f"=SUM({col}5:{col}7)"
        ws_dict['CF'][f"{col}10"] = f"=-Schedules!{col}17"
        ws_dict['CF'][f"{col}11"] = f"={col}10"
        ws_dict['CF'][f"{col}13"] = f"=-Schedules!{col}23"
        ws_dict['CF'][f"{col}14"] = f"=-IS!{col}16*Inputs!{col}44"
        ws_dict['CF'][f"{col}15"] = f"={col}13+{col}14"
        ws_dict['CF'][f"{col}17"] = f"={col}8+{col}11+{col}15"
        
    ws_dict['CF']['F18'] = "=BS!E5"
    for col, prev in [('G','F'), ('H','G'), ('I','H'), ('J','I')]:
        ws_dict['CF'][f"{col}18"] = f"=BS!{prev}5"
        
    for col in ['F', 'G', 'H', 'I', 'J']:
        ws_dict['CF'][f"{col}19"] = f"={col}18+{col}17"
        
    for r in range(5, 20):
        for col in ['F', 'G', 'H', 'I', 'J']:
            ws_dict['CF'][f"{col}{r}"].number_format = FMT_AMOUNT
            ws_dict['CF'][f"{col}{r}"].font = FONT_BLACK

    # --- BS Sheet ---
    # 1.9 & 10.1 - 10.2 Assets
    for col in ['C', 'D', 'E']:
        ws_dict['BS'][f"{col}5"] = f"=Inputs!{col}21"
        ws_dict['BS'][f"{col}6"] = f"=Inputs!{col}22"
        ws_dict['BS'][f"{col}7"] = f"=Inputs!{col}23"
        ws_dict['BS'][f"{col}8"] = f"=Inputs!{col}24"
    for col in ['F', 'G', 'H', 'I', 'J']:
        ws_dict['BS'][f"{col}5"] = f"=CF!{col}19"
        ws_dict['BS'][f"{col}6"] = f"=Schedules!{col}9"
        ws_dict['BS'][f"{col}7"] = f"=Schedules!{col}10"
        ws_dict['BS'][f"{col}8"] = f"=Schedules!{col}19"

    # 1.10 & 10.3 Total Assets
    for col in ['C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']:
        ws_dict['BS'][f"{col}9"] = f"=SUM({col}5:{col}8)"

    # 1.11 & 10.4 - 10.6 Liabilities and Equity
    for col in ['C', 'D', 'E']:
        ws_dict['BS'][f"{col}11"] = f"=Inputs!{col}26"
        ws_dict['BS'][f"{col}12"] = f"=Inputs!{col}27"
        ws_dict['BS'][f"{col}13"] = f"=Inputs!{col}28"
        ws_dict['BS'][f"{col}14"] = f"=Inputs!{col}29"
        
    for col in ['F', 'G', 'H', 'I', 'J']:
        ws_dict['BS'][f"{col}11"] = f"=Schedules!{col}11"
        ws_dict['BS'][f"{col}12"] = f"=Schedules!{col}24"
    ws_dict['BS']['F13'] = "=E13"
    for col, prev in [('G','F'), ('H','G'), ('I','H'), ('J','I')]:
        ws_dict['BS'][f"{col}13"] = f"={prev}13"
    ws_dict['BS']['F14'] = "=E14+IS!F16+CF!F14"
    for col, prev in [('G','F'), ('H','G'), ('I','H'), ('J','I')]:
        ws_dict['BS'][f"{col}14"] = f"={prev}14+IS!{col}16+CF!{col}14"

    # 1.12 - 1.13 & 10.7 Total Liabilities & Balance Check
    for col in ['C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']:
        ws_dict['BS'][f"{col}15"] = f"=SUM({col}11:{col}14)"
        ws_dict['BS'][f"{col}17"] = f"={col}9-{col}15"
        
    for r in range(5, 18):
        for col in ['C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']:
            ws_dict['BS'][f"{col}{r}"].number_format = FMT_AMOUNT
            ws_dict['BS'][f"{col}{r}"].font = FONT_BLACK

    # --- Checks Sheet ---
    # 10.8 Checks
    ws_dict['Checks']['C5'] = '=IF(MAX(BS!C17:J17)-MIN(BS!C17:J17)<0.01,"OK","ERROR")'
    ws_dict['Checks']['C5'].font = FONT_BOLD

    # --- DCF Sheet ---
    # Module 11
    for col in ['F', 'G', 'H', 'I', 'J']:
        ws_dict['DCF'][f"{col}5"] = f"=IS!{col}12"
        ws_dict['DCF'][f"{col}6"] = f"={col}5*Inputs!{col}43"
        ws_dict['DCF'][f"{col}7"] = f"={col}5-{col}6"
        ws_dict['DCF'][f"{col}8"] = f"=IS!{col}11"
        ws_dict['DCF'][f"{col}9"] = f"=Schedules!{col}17"
        ws_dict['DCF'][f"{col}10"] = f"=Schedules!{col}13"
        ws_dict['DCF'][f"{col}11"] = f"={col}7+{col}8-{col}9-{col}10"

    ws_dict['DCF']['C14'] = "=Inputs!C47+Inputs!C48*Inputs!C49"
    ws_dict['DCF']['C15'] = "=Inputs!C50*(1-Inputs!J43)"
    ws_dict['DCF']['C16'] = "=C14*(1-Inputs!C51)+C15*Inputs!C51"
    ws_dict['DCF']['C14'].number_format = FMT_PERCENT
    ws_dict['DCF']['C15'].number_format = FMT_PERCENT
    ws_dict['DCF']['C16'].number_format = FMT_PERCENT

    for col in ['F', 'G', 'H', 'I', 'J']:
        ws_dict['DCF'][f"{col}25"] = f"=1/(1+$C$16)^{col}24"
        ws_dict['DCF'][f"{col}26"] = f"={col}11*{col}25"
        ws_dict['DCF'][f"{col}25"].number_format = FMT_FACTOR
        ws_dict['DCF'][f"{col}26"].number_format = FMT_AMOUNT

    ws_dict['DCF']['C29'] = "=SUM(F26:J26)"
    ws_dict['DCF']['C30'] = "=J11*(1+Inputs!C52)/(C16-Inputs!C52)"
    ws_dict['DCF']['C31'] = "=C30*J25"
    ws_dict['DCF']['C32'] = "=C29+C31"
    ws_dict['DCF']['C33'] = "=BS!E12"
    ws_dict['DCF']['C34'] = "=BS!E5"
    ws_dict['DCF']['C35'] = "=C32-C33+C34"
    ws_dict['DCF']['C36'] = "=Inputs!C53"
    ws_dict['DCF']['C37'] = "=C35/C36"

    for r in [29, 30, 31, 32, 33, 34, 35]:
        ws_dict['DCF'][f"C{r}"].number_format = FMT_AMOUNT
    ws_dict['DCF']['C36'].number_format = "#,##0.0"
    ws_dict['DCF']['C37'].number_format = FMT_SHARE

    # Module 12 Sensitivity
    for r in range(42, 47):
        for col in ['D', 'E', 'F', 'G', 'H']:
            ws_dict['DCF'][f"{col}{r}"] = f"=(SUMPRODUCT($F$11:$J$11,1/(1+$C{r})^$F$24:$J$24)+$J$11*(1+{col}$41)/($C{r}-{col}$41)/(1+$C{r})^5-$C$33+$C$34)/$C$36"
            ws_dict['DCF'][f"{col}{r}"].number_format = FMT_SHARE
            ws_dict['DCF'][f"{col}{r}"].font = FONT_BLACK

    # Heatmap conditional formatting on D42:H46
    color_scale = openpyxl.formatting.rule.ColorScaleRule(
        start_type='min', start_color='F8696B',
        mid_type='percentile', mid_value=50, mid_color='FFEB84',
        end_type='max', end_color='63BE7B'
    )
    ws_dict['DCF'].conditional_formatting.add("D42:H46", color_scale)

    wb.save("assets/kaveri-solution.xlsx")
    print("Saved assets/kaveri-solution.xlsx")

if __name__ == "__main__":
    build_starter_workbook()
    build_solution_workbook()
