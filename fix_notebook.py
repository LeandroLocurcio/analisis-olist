import json

notebook_path = r"c:\Leandro\Programacion\Olist\analisis-olist\EDA_1.ipynb"

with open(notebook_path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

def fix_source_list(source_list):
    new_source = []
    fixed = False
    for line in source_list:
        # Check if the line matches the pattern of being wrapped in quotes with extra spaces
        # e.g., '    "customer_unique = ...\n"'
        stripped = line.strip()
        if stripped.startswith('"') and stripped.endswith('"\n'):
            # It's a line that looks like '    "code"\n'
            # We want just 'code\n'
            code_content = stripped[1:-2] + '\n'
            new_source.append(code_content)
            fixed = True
        elif stripped.startswith('"') and stripped.endswith('"'):
             # It's a line that looks like '    "code"'
            code_content = stripped[1:-1]
            new_source.append(code_content)
            fixed = True
        else:
            new_source.append(line)
    return new_source, fixed

for cell in nb.get('cells', []):
    if cell.get('cell_type') == 'code':
        source = cell.get('source', [])
        if isinstance(source, list):
            new_source, fixed = fix_source_list(source)
            if fixed:
                cell['source'] = new_source
        elif isinstance(source, str):
            # If it's a single string, we might need different logic
            pass

with open(notebook_path, 'w', encoding='utf-8') as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)

print("Notebook fixed.")
