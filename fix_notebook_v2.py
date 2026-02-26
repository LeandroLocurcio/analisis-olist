import json
import re

notebook_path = r"c:\Leandro\Programacion\Olist\analisis-olist\EDA_1.ipynb"

with open(notebook_path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

def fix_line(line):
    # Pattern 1: Leading spaces and a quote at the start
    # e.g. '    "customer_unique = ...'
    # We want to remove the spaces and the first quote
    new_line = line
    fixed = False
    
    # Remove leading spaces and then check for a quote
    stripped_leading = line.lstrip()
    if stripped_leading.startswith('"'):
        # Check if it has a matching quote at the end or if it's just a rogue quote
        # In the cases we saw, it looks like it's just '    "code\n'
        # Let's remove the leading quote if it followed by typical code
        content = stripped_leading[1:]
        # If the line ended with \n, keep it
        new_line = content
        fixed = True
        print(f"Fixed line: {line!r} -> {new_line!r}")
    
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

print("Notebook fixed (v2).")
