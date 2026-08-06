from pathlib import Path
fp = Path("scripts/parse_data_v4.py")
lines = fp.read_text(encoding="utf-8").split("\n")

# Find and fix the issues
new_lines = []
for i, line in enumerate(lines):
    # After first_img = "", add SQ/DQ definitions
    if line.strip() == 'first_img = ""' and i+1 < len(lines) and lines[i+1].strip() == "":
        new_lines.append(line)
        new_lines.append("    SQ = chr(39)")
        new_lines.append("    DQ = chr(34)")
        continue
    
    # Fix img_pattern - make all parts with backslash raw strings
    if "img_pattern = r'<img" in line and "SQ + DQ" in line:
        line = line.replace("'])", r"'])")
        line = line.replace("']+)", r"']+)")
        line = line.replace("' + SQ + DQ + ']", r"' + SQ + DQ + r']")
        line = line.replace("' + SQ + DQ + ']+)", r"' + SQ + DQ + r']+)")
        # Simpler: just rebuild it correctly
        line = "    img_pattern = r'<img\\s[^>]*src=([' + SQ + DQ + r'])([^' + SQ + DQ + r']+)\\1[^>]*>'"
    
    # Fix alt_m line
    if "alt_m = re.search(r'alt=" in line and "SQ + DQ" in line:
        line = "        alt_m = re.search(r'alt=([' + SQ + DQ + r'])([^' + SQ + DQ + r']*)\\1', m.group(0), re.I)"
    
    # Fix a_pattern
    if "a_pattern = r'<a\\s+href=" in line and "SQ + DQ" in line:
        line = "    a_pattern = r'<a\\s+href=([' + SQ + DQ + r'])([^' + SQ + DQ + r']+\\.html)\\1[^>]*>(.*?)</a>'"
    
    new_lines.append(line)

fp.write_text("\n".join(new_lines), encoding="utf-8", newline="\n")
print("Fixed lines")
