#!/usr/bin/env python3
import re
from pathlib import Path

file_path = Path(__file__).parent / "parse_data_v4.py"
content = file_path.read_text(encoding='utf-8')

# 1. Add import os if missing
if 'import os' not in content:
    content = content.replace('import sys\r\nimport re', 'import sys\r\nimport os\r\nimport re')

# 2. Replace quick_parse_header function
old_func_start = 'def quick_parse_header(html_path, code):'
old_func_end = '\r\n\r\n\r\ndef parse_countries():'

old_func_match = re.search(
    re.escape(old_func_start) + r'.*?' + re.escape(old_func_end),
    content,
    re.DOTALL
)

if old_func_match:
    old_func = old_func_match.group(0)
    print(f"Found old quick_parse_header, length: {len(old_func)}")
    
    new_func = '''def quick_parse_header(html_path, code):
    """轻量解析HTML：只提取title/keywords/editor/last_modified/第一张图，不做BS4完整解析"""
    try:
        with open(html_path, 'r', encoding='utf-8', errors='ignore') as f:
            html_content = f.read()
    except:
        return None

    result = {
        "code": code, "title": code, "subtitle": "", "main_image": "",
        "flag_ratio": "", "toc": [], "all_flags": [], "content_blocks": [],
        "see_also": [], "links": [], "keywords": [], "last_modified": "",
        "intro": "", "editor": "",
    }
    title_m = re.search(r'<title>([^<]+)</title>', html_content, re.I)
    if title_m:
        result["title"] = clean_text(unescape(title_m.group(1)))
        result["title"] = re.sub(r'\\s*-\\s*Flags of the World.*$', '', result["title"], flags=re.IGNORECASE).strip()

    info = extract_custom_tags(html_content)
    result["keywords"] = info["keywords"]
    result["editor"] = info["editor"]
    result["subtitle"] = info["subtitle"]

    # 提取所有有效旗帜图片
    letter = code[0].lower() if code else "a"
    default_path = f"images/{letter}/{code}.gif"
    all_found_imgs = []
    first_img = ""
    
    img_pattern = r'<img\\s[^>]*src=(["\\'])([^"\\']+)\\1[^>]*>'
    for m in re.finditer(img_pattern, html_content, re.I):
        src = normalize_img_src(m.group(2))
        alt_m = re.search(r'alt=(["\\'])([^"\\']*)\\1', m.group(0), re.I)
        alt_text = clean_text(unescape(alt_m.group(2))) if alt_m else ""
        if src and not is_image_skippable(src):
            all_found_imgs.append({"src": src, "alt": alt_text})
            if not first_img:
                first_img = src

    # 验证main_image是否在本地存在
    base_dir_p = Path(__file__).parent.parent
    main_image = first_img or default_path
    found_existing = False
    for img_info in all_found_imgs:
        img_path = base_dir_p / img_info["src"]
        if img_path.exists():
            main_image = img_info["src"]
            found_existing = True
            break
    if not found_existing:
        main_image = find_existing_image(code, letter, first_img)
    result["main_image"] = main_image
    result["all_flags"] = all_found_imgs

    # 提取子页面链接
    sub_pages = []
    code_prefix = code[:2].lower()
    a_pattern = r'<a\\s+href=(["\\'])([^"\\']+\\.html)\\1[^>]*>(.*?)</a>'
    for m in re.finditer(a_pattern, html_content, re.I | re.DOTALL):
        href = m.group(2)
        text = clean_text(unescape(re.sub(r'<[^>]+>', '', m.group(3))))
        if href.startswith('http'):
            continue
        if href.startswith('#') or href.startswith('mailto:') or href.startswith('javascript:'):
            continue
        href_clean = href.replace('../', '').rsplit('.', 1)[0]
        if href_clean.lower() == code.lower():
            continue
        if not href_clean or not href_clean[0].isalnum():
            continue
        if href_clean.lower().startswith(code_prefix):
            if len(text) > 0 and len(href_clean) <= 30:
                sub_pages.append({"code": href_clean, "title": text})

    # 提取段落文本
    content_blocks = []
    p_pattern = r'<p[^>]*>(.*?)</p>'
    para_count = 0
    for m in re.finditer(p_pattern, html_content, re.I | re.DOTALL):
        p_text = clean_text(unescape(re.sub(r'<[^>]+>', '', m.group(1))))
        if len(p_text) > 20:
            content_blocks.append({"type": "paragraph", "text": p_text})
            para_count += 1
            if para_count >= 5:
                break

    # 如果有sub_pages，添加相关旗帜block
    if sub_pages:
        content_blocks.append({
            "type": "sub_pages",
            "title": f"相关旗帜（{len(sub_pages)}个）",
            "links": sub_pages
        })

    # 如果既没有子页面也没有段落但有title，添加默认段落
    if not sub_pages and para_count == 0 and result.get("title"):
        content_blocks.append({
            "type": "paragraph",
            "text": f"这是「{result['title']}」的分类索引页面。"
        })

    result["content_blocks"] = content_blocks

    # last modified
    lm = re.search(r'Last modified:\\s*<strong>([^<]+)</strong>', html_content, re.I)
    if lm:
        result["last_modified"] = clean_text(lm.group(1))

    return result


def parse_countries():'''
    
    content = content.replace(old_func, new_func)
    print("Replaced quick_parse_header")

# 3. Fix deep parsing main_image verification (around line 875)
old_main_img_line = '    result["main_image"] = main_img'
new_main_img_code = '''    letter = code[0].lower() if code else "a"
    base_dir_p = Path(__file__).parent.parent
    main_img_path = base_dir_p / main_img if main_img else None
    if not main_img or not main_img_path.exists():
        main_img = find_existing_image(code, letter, main_img)
    result["main_image"] = main_img'''

# Find the section before the final return
if old_main_img_line in content:
    # Make sure we don't replace the one in quick_parse_header
    # The one in deep parse comes after: if not main_img: letter = ... main_img = f"images/{letter}/{code}.gif"
    deep_parse_context = '    if not main_img:\r\n        letter = code[0].lower() if code else "a"\r\n        main_img = f"images/{letter}/{code}.gif"\r\n    result["main_image"] = main_img'
    if deep_parse_context in content:
        new_deep_context = '''    if not main_img:
        letter = code[0].lower() if code else "a"
        main_img = f"images/{letter}/{code}.gif"
    letter = code[0].lower() if code else "a"
    base_dir_p = Path(__file__).parent.parent
    main_img_path = base_dir_p / main_img if main_img else None
    if not main_img or not main_img_path.exists():
        main_img = find_existing_image(code, letter, main_img)
    result["main_image"] = main_img'''
        content = content.replace(deep_parse_context, new_deep_context)
        print("Replaced deep parse main_image verification")

file_path.write_text(content, encoding='utf-8', newline='')
print("File saved successfully!")
