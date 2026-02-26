import json
import re

notebook_path = r"c:\Leandro\Programacion\Olist\analisis-olist\EDA_1.ipynb"

with open(notebook_path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

def fix_line(line):
    # Pattern to match: optional spaces, a quote, the code, \n, and an optional quote and comma
    # e.g. '    "code\n",' or '    "code\n'
    new_line = line
    fixed = False
    
    # Use regex to find the meat of the code if it's wrapped in quotes
    # Match: (zero or more spaces) + quote + (everything else) + (un-escaped \n) + (optional quote and comma)
    # Actually, in the Python string after json.load, \n is a real newline character.
    # So we look for: (spaces) + " + (CODE) + \n + " + optional comma
    
    match = re.search(r'^\s*"(.*)\\n",?$', line)
    if not match:
        # Try without the literal \n string if it was somehow already partially processed
        match = re.search(r'^\s*"(.*)",?$', line)
    
    if match:
        new_line = match.group(1) + '\n'
        fixed = True
        print(f"Fixed line: {line!r} -> {new_line!r}")
    else:
        # If it's already partially fixed (like from v2), it might look like:
        # "code\n","
        match = re.search(r'^(.*)\\n",?$', line)
        if match:
            new_line = match.group(1) + '\n'
            fixed = True
            print(f"Fixed partially fixed line: {line!r} -> {new_line!r}")

    return new_line, fixed

for cell in nb.get('cells', []):
    if cell.get('cell_type') == 'code':
        source = cell.get('source', [])
        if isinstance(source, list):
            new_source = []
            cell_fixed = False
            for line in source:
                fixed_line, was_fixed = fix_line(line)
                new_source.append(fixed_line)
                if was_fixed:
                    cell_fixed = True
            if cell_fixed:
                cell['source'] = new_source

with open(notebook_path, 'w', encoding='utf-8') as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)

print("Notebook fixed (v3).")
