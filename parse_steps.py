import re
import json

def parse_skill_steps(skill_path):
    with open(skill_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find section 6: The script
    sec6_match = re.search(r'## 6\. The script.*?(?=## 7\. Layout)', content, re.DOTALL)
    if not sec6_match:
        raise ValueError("Could not find section 6 in SKILL.md")
    
    script_text = sec6_match.group(0)
    
    # Split into modules
    module_blocks = re.split(r'### Module (\d+) · (.*?)\n', script_text)
    # module_blocks[0] is preamble before first module
    modules = []
    
    # regex for steps: **X.Y Title** (type)
    step_pattern = re.compile(
        r'\*\*(\d+\.\d+)\s+([^*]+)\*\*\s*\((build|quiz|look|format)\)\n(.*?)(?=\n\*\*\d+\.\d+|\Z)',
        re.DOTALL
    )
    
    i = 1
    total_steps = 0
    while i < len(module_blocks):
        mod_num = int(module_blocks[i])
        mod_name = module_blocks[i+1].strip()
        mod_body = module_blocks[i+2]
        
        goal_match = re.search(r'Goal:\s*(.*?)\n', mod_body)
        mod_goal = goal_match.group(1).strip() if goal_match else ""
        
        steps = []
        for step_match in step_pattern.finditer(mod_body):
            step_id = step_match.group(1)
            step_title = step_match.group(2).strip()
            step_type = step_match.group(3)
            step_details = step_match.group(4)
            
            # Extract fields
            def get_field(name):
                m = re.search(rf'- {name}:\s*(.*?)(?=\n- |\Z)', step_details, re.DOTALL)
                return m.group(1).strip() if m else None

            ask = get_field("Ask")
            options = get_field("Options")
            correct = get_field("Correct")
            after = get_field("After answering")
            answer = get_field("Answer")
            yellow = get_field("Yellow")
            check = get_field("Check")
            hint1 = get_field("Hint 1")
            hint2 = get_field("Hint 2")
            why = get_field("Why")
            
            steps.append({
                "id": step_id,
                "title": step_title,
                "type": step_type,
                "ask": ask,
                "options": [opt.strip() for opt in options.split('/')] if options else [],
                "correct": correct,
                "after": after,
                "answer": answer,
                "yellow": yellow,
                "check": check,
                "hint1": hint1,
                "hint2": hint2,
                "why": why
            })
            total_steps += 1
            
        modules.append({
            "module_num": mod_num,
            "name": mod_name,
            "goal": mod_goal,
            "steps": steps
        })
        i += 3
        
    print(f"Parsed {len(modules)} modules and {total_steps} steps.")
    return modules

if __name__ == "__main__":
    mods = parse_skill_steps("excel-financial-modelling-tutor/SKILL.md")
    with open("assets/course_steps.json", "w", encoding="utf-8") as f:
        json.dump(mods, f, indent=2)
    print("Saved course steps to assets/course_steps.json")
