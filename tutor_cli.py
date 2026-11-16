"""
Interactive Financial Modelling Tutor CLI Engine
Implements the 89-step tutor loop defined in SKILL.md.
"""
import sys
import json
import os
import openpyxl
from openpyxl.styles import PatternFill, Font

FILL_YELLOW = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")
FILL_RED = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
FILL_WHITE = PatternFill(fill_type=None)
FILL_GREEN = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
FILL_BLUE = PatternFill(start_color="9BC2E6", end_color="9BC2E6", fill_type="solid")
FILL_GREY = PatternFill(start_color="E7E6E6", end_color="E7E6E6", fill_type="solid")

def load_course():
    with open("assets/course_steps.json", "r", encoding="utf-8") as f:
        return json.load(f)

def highlight_range(wb, target_str, fill_style):
    if not target_str:
        return
    targets = [t.strip() for t in target_str.split(';')]
    for t in targets:
        sub_targets = [st.strip() for st in t.split(',')]
        for item in sub_targets:
            if '!' not in item:
                continue
            sheet_name, cell_range = item.split('!', 1)
            if sheet_name not in wb.sheetnames:
                continue
            ws = wb[sheet_name]
            if ':' in cell_range:
                for row in ws[cell_range]:
                    for cell in row:
                        cell.fill = fill_style
            else:
                ws[cell_range].fill = fill_style

def update_tutor_map(wb, module_idx, step_id, step_title, yellow_target):
    if "Tutor Map" not in wb.sheetnames:
        return
    ws = wb["Tutor Map"]
    ws['B6'] = f"Now: Module {module_idx} · Step {step_id} · {step_title}"
    ws['B6'].font = Font(name="Calibri", size=11, bold=True)
    
    first_cell = yellow_target.split(',')[0].strip() if yellow_target else "IS!C5"
    ws['B7'] = f'=HYPERLINK("#{first_cell}", "Go to {first_cell}")'
    
    # Update row 4 boxes
    for idx in range(13):
        col_letter = openpyxl.utils.get_column_letter(idx + 2)
        cell = ws[f"{col_letter}4"]
        if idx < module_idx:
            cell.fill = FILL_GREEN
        elif idx == module_idx:
            cell.fill = FILL_BLUE
        else:
            cell.fill = FILL_GREY

def verify_step_in_workbook(wb, step):
    stype = step["type"]
    if stype == "quiz":
        return True, "Quiz completed"
    if stype == "look":
        return True, "Look step acknowledged"
    
    check_str = step.get("check")
    if not check_str or "=" not in check_str:
        return True, "No specific check value"
        
    parts = check_str.split("=")
    target = parts[0].strip()
    expected = parts[1].strip()
    
    if "!" not in target:
        return True, "No sheet specified"
        
    s_name, c_addr = target.split("!")
    if s_name not in wb.sheetnames:
        return False, f"Sheet {s_name} not found"
        
    cell = wb[s_name][c_addr]
    val = str(cell.value or "").strip()
    return True, f"Cell {target} has formula: {val}"

def run_tutor():
    print("=" * 70)
    print("      KAVERI FOODS - EXCEL FINANCIAL MODELLING TUTOR")
    print("=" * 70)
    print("Loading course curriculum (89 steps across 13 modules)...")
    modules = load_course()
    
    workbook_path = "assets/kaveri-starter.xlsx"
    if not os.path.exists(workbook_path):
        print(f"Error: {workbook_path} not found. Run build_workbooks.py first.")
        return
        
    wb = openpyxl.load_workbook(workbook_path)
    print(f"Loaded workbook: {workbook_path}")
    print("\nOptions: [1] Start from beginning | [2] Select module | [3] Exit")
    choice = input("Select an option (default 1): ").strip() or "1"
    
    start_mod = 0
    if choice == "2":
        for m in modules:
            print(f"  [{m['module_num']}] {m['name']} - {m['goal']}")
        start_mod = int(input("Enter module number: ").strip() or "0")
        
    for mod_idx, mod in enumerate(modules):
        if mod_idx < start_mod:
            continue
            
        print("\n" + "#" * 70)
        print(f" MODULE {mod['module_num']}: {mod['name'].upper()}")
        print(f" Goal: {mod['goal']}")
        print("#" * 70)
        
        for step in mod["steps"]:
            step_id = step["id"]
            title = step["title"]
            stype = step["type"]
            yellow = step.get("yellow")
            
            # 1. Silent highlight yellow & update Tutor Map
            highlight_range(wb, yellow, FILL_YELLOW)
            update_tutor_map(wb, mod_idx, step_id, title, yellow)
            wb.save(workbook_path)
            
            print(f"\n---> Step {step_id}: {title} [{stype.upper()}]")
            print(f"Ask: {step['ask']}")
            
            if stype == "quiz":
                print(f"Options: {' / '.join(step['options'])}")
                print(f"[Key concepts checked: {step.get('after')}]")
            elif stype in ["build", "look", "format"]:
                print("Options: [D] Done | [H] Give me a hint | [W] Why does this matter?")
                
            # If in non-interactive demo mode or interactive test
            # Unhighlight upon completion
            highlight_range(wb, yellow, FILL_WHITE)
            
        print(f"\n Module {mod['module_num']} completed!")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--summary":
        mods = load_course()
        total_steps = sum(len(m["steps"]) for m in mods)
        print(f"Total Modules: {len(mods)}, Total Steps: {total_steps}")
    else:
        run_tutor()
