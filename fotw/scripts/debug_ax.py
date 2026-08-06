from pathlib import Path

html_path = Path(r'd:\Projects\SvgSite\fotw\flags\ax.html')
with open(html_path, 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

for i in range(54, 78):
    if i < len(lines):
        print(f"{i+1:4d}: {lines[i].rstrip()}"[:200])
