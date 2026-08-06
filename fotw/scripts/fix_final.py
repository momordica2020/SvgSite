from pathlib import Path
import re

fp = Path("scripts/parse_data_v4.py")
txt = fp.read_text(encoding="utf-8")

# Add import os
if "import os" not in txt:
    txt = txt.replace("import sys\nimport re", "import sys\nimport os\nimport re")

# Build new quick_parse_header
def make_qph():
    lines = []
    lines.append("def quick_parse_header(html_path, code):")
    lines.append('    """轻量解析HTML：只提取title/keywords/editor/last_modified/第一张图，不做BS4完整解析"""')
    lines.append("    try:")
    lines.append("        with open(html_path, 'r', encoding='utf-8', errors='ignore') as f:")
    lines.append("            html_content = f.read()")
    lines.append("    except:")
    lines.append("        return None")
    lines.append("")
    lines.append("    result = {")
    lines.append('        "code": code, "title": code, "subtitle": "", "main_image": "",')
    lines.append('        "flag_ratio": "", "toc": [], "all_flags": [], "content_blocks": [],')
    lines.append('        "see_also": [], "links": [], "keywords": [], "last_modified": "",')
    lines.append('        "intro": "", "editor": "",')
    lines.append("    }")
    lines.append("    title_m = re.search(r'<title>([^<]+)</title>', html_content, re.I)")
    lines.append("    if title_m:")
    lines.append('        result["title"] = clean_text(unescape(title_m.group(1)))')
    lines.append('        result["title"] = re.sub(r"\\s*-\\s*Flags of the World.*$", "", result["title"], flags=re.IGNORECASE).strip()')
    lines.append("")
    lines.append("    info = extract_custom_tags(html_content)")
    lines.append('    result["keywords"] = info["keywords"]')
    lines.append('    result["editor"] = info["editor"]')
    lines.append('    result["subtitle"] = info["subtitle"]')
    lines.append("")
    lines.append('    letter = code[0].lower() if code else "a"')
    lines.append('    default_path = f"images/{letter}/{code}.gif"')
    lines.append("    all_found_imgs = []")
    lines.append('    first_img = ""')
    lines.append("")
    q = chr(39)  # single quote
    dq = chr(34)
    lines.append(f"    img_pattern = r'<img\\s[^>]*src=([{q}{dq}])([^{q}{dq}]+)\\1[^>]*>'")
    lines.append("    for m in re.finditer(img_pattern, html_content, re.I):")
    lines.append("        src = normalize_img_src(m.group(2))")
    lines.append(f"        alt_m = re.search(r'alt=([{q}{dq}])([^{q}{dq}]*)\\1', m.group(0), re.I)")
    lines.append('        alt_text = clean_text(unescape(alt_m.group(2))) if alt_m else ""')
    lines.append("        if src and not is_image_skippable(src):")
    lines.append('            all_found_imgs.append({"src": src, "alt": alt_text})')
    lines.append("            if not first_img:")
    lines.append("                first_img = src")
    lines.append("")
    lines.append("    base_dir_p = Path(__file__).parent.parent")
    lines.append("    main_image = first_img or default_path")
    lines.append("    found_existing = False")
    lines.append("    for img_info in all_found_imgs:")
    lines.append('        img_path = base_dir_p / img_info["src"]')
    lines.append("        if img_path.exists():")
    lines.append('            main_image = img_info["src"]')
    lines.append("            found_existing = True")
    lines.append("            break")
    lines.append("    if not found_existing:")
    lines.append("        main_image = find_existing_image(code, letter, first_img)")
    lines.append('    result["main_image"] = main_image')
    lines.append('    result["all_flags"] = all_found_imgs')
    lines.append("")
    lines.append("    sub_pages = []")
    lines.append("    code_prefix = code[:2].lower()")
    lines.append(f"    a_pattern = r'<a\\s+href=([{q}{dq}])([^{q}{dq}]+\\.html)\\1[^>]*>(.*?)</a>'")
    lines.append("    for m in re.finditer(a_pattern, html_content, re.I | re.DOTALL):")
    lines.append("        href = m.group(2)")
    lines.append("        text = clean_text(unescape(re.sub(r'<[^>]+>', '', m.group(3))))")
    lines.append("        if href.startswith('http'):")
    lines.append("            continue")
    lines.append("        if href.startswith('#') or href.startswith('mailto:') or href.startswith('javascript:'):")
    lines.append("            continue")
    lines.append("        href_clean = href.replace('../', '').rsplit('.', 1)[0]")
    lines.append("        if href_clean.lower() == code.lower():")
    lines.append("            continue")
    lines.append("        if not href_clean or not href_clean[0].isalnum():")
    lines.append("            continue")
    lines.append("        if href_clean.lower().startswith(code_prefix):")
    lines.append("            if len(text) > 0 and len(href_clean) <= 30:")
    lines.append('                sub_pages.append({"code": href_clean, "title": text})')
    lines.append("")
    lines.append("    content_blocks = []")
    lines.append("    p_pattern = r'<p[^>]*>(.*?)</p>'")
    lines.append("    para_count = 0")
    lines.append("    for m in re.finditer(p_pattern, html_content, re.I | re.DOTALL):")
    lines.append("        p_text = clean_text(unescape(re.sub(r'<[^>]+>', '', m.group(1))))")
    lines.append("        if len(p_text) > 20:")
    lines.append('            content_blocks.append({"type": "paragraph", "text": p_text})')
    lines.append("            para_count += 1")
    lines.append("            if para_count >= 5:")
    lines.append("                break")
    lines.append("")
    lines.append("    if sub_pages:")
    lines.append("        content_blocks.append({")
    lines.append('            "type": "sub_pages",')
    lines.append('            "title": f"相关旗帜（{len(sub_pages)}个）",')
    lines.append('            "links": sub_pages')
    lines.append("        })")
    lines.append("")
    lines.append('    if not sub_pages and para_count == 0 and result.get("title"):')
    lines.append("        content_blocks.append({")
    lines.append('            "type": "paragraph",')
    lines.append("            \"text\": f\"这是「{result['title']}」的分类索引页面。\"")
    lines.append("        })")
    lines.append("")
    lines.append('    result["content_blocks"] = content_blocks')
    lines.append("")
    lines.append("    lm = re.search(r'Last modified:\\s*<strong>([^<]+)</strong>', html_content, re.I)")
    lines.append("    if lm:")
    lines.append('        result["last_modified"] = clean_text(lm.group(1))')
    lines.append("")
    lines.append("    return result")
    lines.append("")
    lines.append("")
    return "\n".join(lines)

new_qph = make_qph()

# Find old quick_parse_header boundaries
q_start = txt.find("def quick_parse_header(html_path, code):")
# Find parse_countries
pc_start = txt.find("\ndef parse_countries():", q_start)
if pc_start == -1:
    pc_start = txt.find("def parse_countries():", q_start)
    if pc_start > 0 and txt[pc_start-1] != '\n':
        pass  # it's at the start

print(f"q_start={q_start}, pc_start={pc_start}")

# Replace
txt = txt[:q_start] + new_qph + txt[pc_start:]

# Fix deep parse main_image
old_deep = '''    if not main_img:
        letter = code[0].lower() if code else "a"
        main_img = f"images/{letter}/{code}.gif"
    result["main_image"] = main_img'''

new_deep = '''    if not main_img:
        letter = code[0].lower() if code else "a"
        main_img = f"images/{letter}/{code}.gif"
    letter_dp = code[0].lower() if code else "a"
    base_dir_dp = Path(__file__).parent.parent
    main_img_path = base_dir_dp / main_img if main_img else None
    if not main_img or not main_img_path.exists():
        main_img = find_existing_image(code, letter_dp, main_img)
    result["main_image"] = main_img'''

if old_deep in txt:
    txt = txt.replace(old_deep, new_deep)
    print("Fixed deep parse")
else:
    print("WARNING: old deep not found")
    # Try finding result["main_image"] = main_img that's NOT in quick_parse_header
    idx = txt.find('result["main_image"] = main_img')
    while idx != -1:
        # Check if this is in the deep parse section (should be after all_flags assignment)
        context = txt[max(0,idx-200):idx]
        if "all_images" in context:
            print(f"Found deep parse main_img at {idx}")
            break
        idx = txt.find('result["main_image"] = main_img', idx+1)

fp.write_text(txt, encoding="utf-8", newline="\n")
print("Written OK, length:", len(txt))
