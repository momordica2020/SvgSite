#!/usr/bin/env python3
"""改进的FOTW页面解析器 v5 - 使用线性文档遍历，不受嵌套影响"""
import sys
import re
import json
from pathlib import Path
from html import unescape

try:
    from bs4 import BeautifulSoup, NavigableString, Tag
    HAVE_BS4 = True
except ImportError:
    HAVE_BS4 = False

BASE_DIR = Path(__file__).resolve().parent.parent
FLAGS_DIR = BASE_DIR / "flags"
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def clean_text(text):
    if not text:
        return ""
    text = re.sub(r'\s+', ' ', text)
    text = text.replace('\xa0', ' ')
    return text.strip()


def normalize_img_src(src):
    if not src:
        return ""
    src = src.replace("../", "")
    if src.startswith("http"):
        return ""
    return src


def normalize_href(href):
    if not href:
        return ""
    href = href.split('#')[0]
    href = href.replace("../flags/", "").replace("../", "")
    if href.startswith("http") or href.startswith("mailto:"):
        return ""
    if href.startswith("misc/") or href.startswith("images/"):
        return ""
    if href.endswith(".pdf") or href.endswith(".gif") or href.endswith(".jpg") or href.endswith(".png"):
        return ""
    if href.endswith(".html") or href.endswith(".htm"):
        href = href.rsplit(".", 1)[0]
    return href


def extract_custom_tags(html):
    """Extract data from FOTW's non-standard custom tags in HEAD"""
    info = {"subtitle": "", "keywords": [], "editor": "", "abstract": ""}
    
    m = re.search(r'<SUBTITLE\s+([^>]*?)/?>', html, re.IGNORECASE)
    if m:
        attr_str = m.group(1)
        sub_text = unescape(attr_str)
        sub_text = re.sub(r'^["\']|["\']$', '', sub_text)
        sub_text = clean_text(sub_text)
        info["subtitle"] = sub_text
    
    m2 = re.search(r'<SUBTITLE[^>]*>([^<]*)</SUBTITLE>', html, re.IGNORECASE)
    if m2 and not info["subtitle"]:
        info["subtitle"] = clean_text(unescape(m2.group(1)))
    
    m = re.search(r'<KEYWORDS\s+([^>]*?)/?>', html, re.IGNORECASE)
    if m:
        kw_str = m.group(1).strip()
        kws = [clean_text(unescape(k)) for k in re.split(r'[,|]', kw_str) if clean_text(k)]
        info["keywords"] = kws[:15]
    
    m = re.search(r'<EDITOR\s+([^>]*?)/?>', html, re.IGNORECASE)
    if m:
        info["editor"] = clean_text(m.group(1))
    
    return info


def is_image_skippable(src):
    if not src:
        return True
    src_lower = src.lower()
    skip_patterns = ['linea', 'fotwbckg', 'spacer', 'dot.', 'bullet', 'icon_', 
                     'arrow', 'button', 'xoxo', 'oooo']
    for p in skip_patterns:
        if p in src_lower:
            return True
    return False


def is_link_navigational(code, text):
    if not code or not text:
        return True
    skip_codes = {'index', 'search', 'disclaim', 'mailme', 'mirror', 'host',
                  'help', 'faq', 'about', 'contact', 'whatsnew', 'fis', 'awards'}
    skip_starts = ['keyword', 'search', 'disclaim', 'mailme', 'mirror', 'host',
                   'xf-', 'bib-']
    if code in skip_codes:
        return True
    for s in skip_starts:
        if code.startswith(s):
            return True
    if len(text) > 80:
        return True
    return False


def parse_with_bs4(html_content, code):
    """使用BeautifulSoup解析 - 线性文档顺序遍历"""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    result = {
        "code": code,
        "title": "",
        "subtitle": "",
        "main_image": "",
        "flag_ratio": "",
        "images": [],
        "sections": [],
        "see_also": [],
        "links": [],
        "keywords": [],
        "last_modified": "",
        "intro": "",
        "editor": "",
    }
    
    custom = extract_custom_tags(html_content)
    result["subtitle"] = custom["subtitle"]
    result["keywords"] = custom["keywords"]
    result["editor"] = custom["editor"]
    
    title_tag = soup.find('title')
    if title_tag:
        result["title"] = clean_text(title_tag.get_text())
    
    h1_tag = soup.find('h1')
    if h1_tag:
        result["title"] = clean_text(h1_tag.get_text()) or result["title"]
    
    mod_match = re.search(r'Last modified:\s*(?:<strong>|<b>)?([^<\n|*]+)', html_content, re.IGNORECASE)
    if mod_match:
        result["last_modified"] = clean_text(unescape(mod_match.group(1)))
    
    cut_idx = html_content.find('<!--CUT ABOVE-->')
    if cut_idx >= 0:
        main_html = html_content[cut_idx + len('<!--CUT ABOVE-->'):]
    else:
        main_html = html_content
    
    main_soup = BeautifulSoup(main_html, 'html.parser')
    
    seen_imgs = set()
    all_images = []
    for img in main_soup.find_all('img'):
        src = normalize_img_src(img.get('src', ''))
        alt = clean_text(unescape(img.get('alt', '')))
        if src and src not in seen_imgs and not is_image_skippable(src):
            seen_imgs.add(src)
            all_images.append({"src": src, "alt": alt})
    
    result["images"] = all_images[:30]
    
    main_img = ""
    for img in all_images:
        s = img["src"].lower()
        if s.startswith("images/") and (s.endswith(".gif") or s.endswith(".png")):
            fname = s.split('/')[-1]
            if fname == f"{code.lower()}.gif" or fname == f"{code.lower()}.png":
                main_img = img["src"]
                break
    if not main_img:
        for img in all_images:
            if img["src"].startswith("images/"):
                main_img = img["src"]
                break
    if not main_img:
        letter = code[0].lower() if code else "a"
        main_img = f"images/{letter}/{code}.gif"
    result["main_image"] = main_img
    
    ratio_match = re.search(r'(\d+)\s*:\s*(\d+)', main_html[:2000])
    if ratio_match:
        result["flag_ratio"] = ratio_match.group(0)
    
    all_headings = []
    for heading in main_soup.find_all('h2'):
        text = clean_text(heading.get_text())
        if text:
            level = int(heading.name[1])
            all_headings.append((heading, level, text, heading.sourceline or 0))
    
    see_also_start_line = None
    see_also_end_line = None
    
    see_also_match = re.search(r'(?:<em>|<i>)?\s*(?:See also|See:)\s*:?\s*(?:</em>|</i>)?', main_html, re.IGNORECASE)
    if see_also_match:
        before_text = main_html[:see_also_match.start()]
        see_also_start_line = before_text.count('\n') + 1
        
        after_text = main_html[see_also_match.end():]
        next_hr = re.search(r'<hr', after_text, re.IGNORECASE)
        next_h2 = re.search(r'<h2[^>]*>', after_text, re.IGNORECASE)
        end_pos = len(after_text)
        if next_hr:
            end_pos = min(end_pos, next_hr.start())
        if next_h2:
            end_pos = min(end_pos, next_h2.start())
        see_also_end_line = see_also_start_line + after_text[:end_pos].count('\n') + 1
    
    for h, level, text, line in all_headings:
        text_lower = text.lower().strip(':')
        if text_lower in ('see also', 'navigation', 'nav', 'see'):
            if see_also_start_line is None or line < see_also_start_line:
                see_also_start_line = line
                next_h = None
                for h2, l2, t2, line2 in all_headings:
                    if line2 > line:
                        t2l = t2.lower().strip(':')
                        if t2l not in ('see also', 'navigation', 'nav', 'see'):
                            see_also_end_line = line2
                            break
            break
    
    sections = []
    seen_heading_texts = set()
    
    sections.append({
        "title": "概述",
        "level": 2,
        "anchor": "",
        "paragraphs": [],
        "images": [],
        "quotes": [],
        "lists": [],
        "links": []
    })
    
    content_headings = []
    for h, level, text, line in all_headings:
        text_lower = text.lower().strip(':')
        if text_lower in ('see also', 'navigation', 'nav', 'see'):
            continue
        if text in seen_heading_texts:
            continue
        seen_heading_texts.add(text)
        
        a_tag = h.find('a')
        anchor = ""
        if a_tag:
            anchor = a_tag.get('name', '') or a_tag.get('id', '')
        if not anchor:
            anchor = h.get('id', '')
        
        content_headings.append((h, level, text, line))
        sections.append({
            "title": text,
            "level": level,
            "anchor": anchor,
            "paragraphs": [],
            "images": [],
            "quotes": [],
            "lists": [],
            "links": []
        })
    
    see_also_links = []
    all_links = []
    seen_link_codes = set()
    
    def add_link(link_dict, section_idx):
        code_h = link_dict["code"]
        if code_h == code:
            return
        if is_link_navigational(code_h, link_dict["title"]):
            return
        if code_h not in seen_link_codes:
            seen_link_codes.add(code_h)
            all_links.append(link_dict)
        if section_idx >= 0 and section_idx < len(sections):
            if link_dict not in sections[section_idx]["links"]:
                sections[section_idx]["links"].append(link_dict)
    
    def is_in_see_also(el_line, el_text=""):
        if see_also_start_line is not None:
            if el_line >= see_also_start_line:
                if see_also_end_line is None or el_line < see_also_end_line:
                    return True
        if el_text and re.match(r'(see also|see:)', el_text.lower()[:20]):
            return True
        return False
    
    def get_current_section_idx(el):
        el_line = el.sourceline or 0
        el_text = clean_text(el.get_text()[:100])
        
        if is_in_see_also(el_line, el_text):
            return -2
        
        idx = 0
        for i, (h, lvl, htext, hline) in enumerate(content_headings):
            if el_line >= hline:
                idx = i + 1
            else:
                break
        
        return min(idx, len(sections) - 1)
    
    for p in main_soup.find_all('p'):
        sec_idx = get_current_section_idx(p)
        text = clean_text(p.get_text())
        if not text or len(text) < 3:
            for img in p.find_all('img'):
                src = normalize_img_src(img.get('src', ''))
                alt = clean_text(unescape(img.get('alt', '')))
                if src and not is_image_skippable(src):
                    img_info = {"src": src, "alt": alt}
                    if sec_idx >= 0 and sec_idx < len(sections):
                        sections[sec_idx]["images"].append(img_info)
            continue
        
        if sec_idx == -2:
            for a in p.find_all('a'):
                href = a.get('href', '')
                t = clean_text(a.get_text())
                code_h = normalize_href(href)
                if code_h and t and not is_link_navigational(code_h, t):
                    see_also_links.append({"code": code_h, "title": t})
            continue
        
        if re.match(r'^(image by|by\s|Image by|\d+:\d+\s*image by)', text) and len(text) < 100:
            for img in p.find_all('img'):
                src = normalize_img_src(img.get('src', ''))
                alt = clean_text(unescape(img.get('alt', '')))
                if src and not is_image_skippable(src):
                    img_info = {"src": src, "alt": alt}
                    if sec_idx >= 0 and sec_idx < len(sections):
                        sections[sec_idx]["images"].append(img_info)
            for a in p.find_all('a'):
                href = a.get('href', '')
                t = clean_text(a.get_text())
                code_h = normalize_href(href)
                if code_h and t and not is_link_navigational(code_h, t):
                    add_link({"code": code_h, "title": t}, sec_idx)
            continue
        
        for img in p.find_all('img'):
            src = normalize_img_src(img.get('src', ''))
            alt = clean_text(unescape(img.get('alt', '')))
            if src and not is_image_skippable(src):
                img_info = {"src": src, "alt": alt}
                if sec_idx >= 0 and sec_idx < len(sections):
                    sections[sec_idx]["images"].append(img_info)
        
        for a in p.find_all('a'):
            href = a.get('href', '')
            t = clean_text(a.get_text())
            code_h = normalize_href(href)
            if code_h and t and not is_link_navigational(code_h, t):
                add_link({"code": code_h, "title": t}, sec_idx)
        
        if sec_idx >= 0 and sec_idx < len(sections):
            sections[sec_idx]["paragraphs"].append(text[:1500])
    
    for bq in main_soup.find_all('blockquote'):
        sec_idx = get_current_section_idx(bq)
        if sec_idx == -2:
            for a in bq.find_all('a'):
                href = a.get('href', '')
                t = clean_text(a.get_text())
                code_h = normalize_href(href)
                if code_h and t and not is_link_navigational(code_h, t):
                    see_also_links.append({"code": code_h, "title": t})
            continue
        text = clean_text(bq.get_text())
        if text and len(text) > 10:
            for a in bq.find_all('a'):
                href = a.get('href', '')
                t = clean_text(a.get_text())
                code_h = normalize_href(href)
                if code_h and t and not is_link_navigational(code_h, t):
                    add_link({"code": code_h, "title": t}, sec_idx)
            for img in bq.find_all('img'):
                src = normalize_img_src(img.get('src', ''))
                alt = clean_text(unescape(img.get('alt', '')))
                if src and not is_image_skippable(src):
                    img_info = {"src": src, "alt": alt}
                    if sec_idx >= 0 and sec_idx < len(sections):
                        sections[sec_idx]["images"].append(img_info)
            if sec_idx >= 0 and sec_idx < len(sections):
                sections[sec_idx]["quotes"].append(text[:1500])
    
    first_content_line = None
    for p in main_soup.find_all('p'):
        text = clean_text(p.get_text())
        if text and len(text) > 80 and not re.match(r'^(image by|\d+:\d+)', text):
            first_content_line = p.sourceline or 0
            break
    
    nav_table_elements = set()
    for table in main_soup.find_all('table'):
        table_links = []
        for a in table.find_all('a'):
            href = a.get('href', '')
            t = clean_text(a.get_text())
            code_h = normalize_href(href)
            if code_h and t and not is_link_navigational(code_h, t):
                table_links.append({"code": code_h, "title": t})
        table_text = clean_text(table.get_text())
        is_nav = len(table_links) > 3 and len(table_text) < len(table_links) * 40
        if is_nav:
            for ul in table.find_all(['ul', 'ol']):
                nav_table_elements.add(ul)
    
    for list_tag in main_soup.find_all(['ul', 'ol']):
        if list_tag in nav_table_elements:
            sec_idx = get_current_section_idx(list_tag)
            for li in list_tag.find_all('li', recursive=False):
                for a in li.find_all('a'):
                    href = a.get('href', '')
                    t = clean_text(a.get_text())
                    code_h = normalize_href(href)
                    if code_h and t and not is_link_navigational(code_h, t):
                        if sec_idx == -2:
                            see_also_links.append({"code": code_h, "title": t})
                        else:
                            add_link({"code": code_h, "title": t}, sec_idx)
            continue
        
        sec_idx = get_current_section_idx(list_tag)
        items = []
        list_links = []
        for li in list_tag.find_all('li', recursive=False):
            li_text = clean_text(li.get_text())
            if li_text and len(li_text) < 500:
                items.append(li_text)
            for a in li.find_all('a'):
                href = a.get('href', '')
                t = clean_text(a.get_text())
                code_h = normalize_href(href)
                if code_h and t and not is_link_navigational(code_h, t):
                    list_links.append({"code": code_h, "title": t})
        
        if not items:
            for l in list_links:
                if sec_idx == -2:
                    see_also_links.append(l)
                else:
                    add_link(l, sec_idx)
            continue
        
        is_nav_list = False
        list_line = list_tag.sourceline or 0
        
        if first_content_line and list_line < first_content_line:
            is_nav_list = True
        
        link_ratio = len(list_links) / max(len(items), 1)
        avg_item_len = sum(len(i) for i in items) / max(len(items), 1)
        if link_ratio > 0.7 and avg_item_len < 80:
            is_nav_list = True
        
        if len(items) <= 10 and all(len(i) < 60 for i in items):
            for i in items:
                if re.search(r'(construction|vertical|anniversary|use of|history|symbol|colour|color|origin|law)', i.lower()):
                    is_nav_list = True
                    break
        
        if sec_idx == -2:
            for l in list_links:
                see_also_links.append(l)
            continue
        
        for l in list_links:
            add_link(l, sec_idx)
        
        if not is_nav_list and sec_idx >= 0 and sec_idx < len(sections):
            sections[sec_idx]["lists"].append(items[:25])
    
    for table in main_soup.find_all('table'):
        sec_idx = get_current_section_idx(table)
        table_links = []
        table_images = []
        for a in table.find_all('a'):
            href = a.get('href', '')
            t = clean_text(a.get_text())
            code_h = normalize_href(href)
            if code_h and t and not is_link_navigational(code_h, t):
                table_links.append({"code": code_h, "title": t})
        for img in table.find_all('img'):
            src = normalize_img_src(img.get('src', ''))
            alt = clean_text(unescape(img.get('alt', '')))
            if src and not is_image_skippable(src):
                table_images.append({"src": src, "alt": alt})
        
        table_text = clean_text(table.get_text())
        is_nav = len(table_links) > 3 and len(table_text) < len(table_links) * 40
        
        if is_nav:
            for l in table_links:
                add_link(l, sec_idx)
            for img in table_images:
                if sec_idx >= 0 and sec_idx < len(sections):
                    sections[sec_idx]["images"].append(img)
            continue
        
        for l in table_links:
            add_link(l, sec_idx)
        for img in table_images:
            if sec_idx >= 0 and sec_idx < len(sections):
                sections[sec_idx]["images"].append(img)
        
        if table_text and len(table_text) > 50 and sec_idx >= 0 and sec_idx < len(sections):
            sections[sec_idx]["paragraphs"].append(table_text[:1500])
    
    for pre in main_soup.find_all('pre'):
        sec_idx = get_current_section_idx(pre)
        if sec_idx >= 0 and sec_idx < len(sections):
            text = clean_text(pre.get_text())
            if text:
                sections[sec_idx]["paragraphs"].append(text[:1500])
    
    final_sections = []
    intro_text = ""
    
    for i, sec in enumerate(sections):
        content = []
        
        sec_imgs = []
        seen_sec_imgs = set()
        for img in sec["images"]:
            if img["src"] not in seen_sec_imgs:
                seen_sec_imgs.add(img["src"])
                sec_imgs.append(img)
        
        if sec_imgs:
            content.append({"type": "images", "content": sec_imgs[:12]})
        if sec["paragraphs"]:
            content.append({"type": "paragraphs", "content": sec["paragraphs"]})
        if sec["quotes"]:
            content.append({"type": "quotes", "content": sec["quotes"]})
        if sec["lists"]:
            content.append({"type": "lists", "content": sec["lists"]})
        
        if i == 0:
            paras = sec["paragraphs"]
            if paras:
                intro_clean = []
                for p in paras:
                    p_clean = re.sub(r'^\s*\d+:\d+\s*(;|,|\|)?\s*(image by|by\s|Image by[^.]+\.?\s*)?', '', p)
                    p_clean = re.sub(r'^(image by|by\s|Image by[^.]+\.?\s*)', '', p_clean)
                    p_clean = re.sub(r'^(Flag of [^-]+ - Image by [^,]+,\s*\d+\s+\w+\s+\d+\s*)', '', p_clean)
                    p_clean = p_clean.strip()
                    if p_clean and len(p_clean) > 10:
                        intro_clean.append(p_clean)
                intro_text = " ".join(intro_clean)[:800]
        
        has_content = bool(content)
        if has_content or (i > 0 and re.search(r'(flag|history|symbol|design|color|colour|use|adopt|meaning|construction|vertical|ensign|national)', sec["title"].lower())):
            final_sections.append({
                "title": sec["title"],
                "anchor": sec["anchor"],
                "content": content
            })
    
    result["sections"] = final_sections
    result["intro"] = intro_text
    
    seen_see = set()
    unique_see = []
    for l in see_also_links:
        if l["code"] not in seen_see and l["code"] != code:
            seen_see.add(l["code"])
            unique_see.append(l)
    result["see_also"] = unique_see[:30]
    
    result["links"] = all_links[:60]
    
    return result


def parse_detail(code):
    html_path = FLAGS_DIR / f"{code}.html"
    if not html_path.exists():
        return None
    try:
        with open(html_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    except:
        return None
    
    try:
        if HAVE_BS4:
            result = parse_with_bs4(content, code)
        else:
            result = {
                "code": code, "title": code, "subtitle": "", "main_image": "",
                "flag_ratio": "", "images": [], "sections": [], "see_also": [],
                "links": [], "keywords": [], "last_modified": "", "intro": "", "editor": "",
            }
            title_m = re.search(r'<title>([^<]+)</title>', content, re.I)
            if title_m:
                result["title"] = clean_text(unescape(title_m.group(1)))
            letter = code[0].lower() if code else "a"
            result["main_image"] = f"images/{letter}/{code}.gif"
    except Exception as e:
        print(f"  Error parsing {code}: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    if result.get("title"):
        result["title"] = re.sub(r'\s*-\s*Flags of the World.*$', '', result["title"], flags=re.IGNORECASE).strip()
    
    result["images"] = result.get("images", [])[:30]
    
    return result


def parse_countries():
    """解析国家列表"""
    countries = []
    index_candidates = [FLAGS_DIR / "country.html", FLAGS_DIR / "index.html"]

    for idx_path in index_candidates:
        if idx_path.exists():
            with open(idx_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            pattern = r'<a\s+href="([a-z][a-z0-9_@!^~$)\(\'\-]*\.html)"[^>]*>([^<]+)</a>'
            matches = re.findall(pattern, content, re.IGNORECASE)
            seen = set()
            for href, name in matches:
                c = href.replace(".html", "").strip()
                name = unescape(name.strip())
                if c and c not in seen and len(c) <= 20:
                    skip_starts = ['keyword', 'search', 'disclaim', 'mailme', 'mirror', 
                                   'host', 'index', 'help', 'faq', 'about', 'contact',
                                   'whatsnew', 'fis', 'awards', 'colour', 'color',
                                   'flag[', 'flag_', 'update', 'us_', 'editor', 'xf-', 'bib-']
                    skip_exact = {'flag', 'flags', 'new', 'top', 'home', 'main'}
                    should_skip = False
                    for s in skip_starts:
                        if c.startswith(s):
                            should_skip = True
                            break
                    if c in skip_exact:
                        should_skip = True
                    if not should_skip and name and len(name) > 0:
                        seen.add(c)
                        letter = c[0].lower() if c else "a"
                        countries.append({"code": c, "title": name, "letter": letter})
            print(f"从 {idx_path.name} 找到 {len(countries)} 个链接")
            if countries:
                break

    if not countries:
        for html_file in sorted(FLAGS_DIR.glob("??.html")):
            code = html_file.stem
            if code.isalpha() and len(code) == 2:
                countries.append({"code": code, "title": code.upper(), "letter": code[0].lower()})
        print(f"扫描到 {len(countries)} 个两字母代码页面")

    return countries


def main():
    print("=== 解析国家列表 ===")
    countries = parse_countries()

    by_letter = {}
    for c in countries:
        l = c["letter"]
        if l not in by_letter:
            by_letter[l] = []
        by_letter[l].append(c)

    with open(DATA_DIR / "countries.json", 'w', encoding='utf-8') as f:
        json.dump({"total": len(countries), "by_letter": by_letter, "countries": countries},
                  f, ensure_ascii=False, indent=1)
    print(f"国家索引已保存: {len(countries)} 个条目")

    print("\n=== 解析详情页 ===")
    details = {}
    parsed = 0
    errors = 0
    for c in countries:
        code = c["code"]
        d = parse_detail(code)
        if d:
            d["title"] = c.get("title", d.get("title", code))
            details[code] = d
            parsed += 1
        else:
            errors += 1
        if parsed % 50 == 0 and parsed > 0:
            print(f"  已解析 {parsed}/{len(countries)} (错误: {errors})")

    with open(DATA_DIR / "flag_details.json", 'w', encoding='utf-8') as f:
        json.dump(details, f, ensure_ascii=False, indent=1)
    print(f"详情数据已保存: {parsed} 个页面 (错误: {errors})")
    
    test_codes = ['cn', 'us', 'jp', 'fr', 'de', 'gb']
    for code in test_codes:
        if code in details:
            d = details[code]
            print(f"\n示例 - {d['title']}:")
            print(f"  副标题: {d.get('subtitle', '')[:80]}")
            print(f"  比例: {d.get('flag_ratio', '')}")
            print(f"  图片数: {len(d.get('images', []))}")
            print(f"  章节数: {len(d.get('sections', []))}")
            for s in d.get('sections', []):
                n_paras = sum(len(c['content']) for c in s.get('content', []) if c['type'] == 'paragraphs')
                n_imgs = sum(len(c['content']) for c in s.get('content', []) if c['type'] == 'images')
                n_quotes = sum(len(c['content']) for c in s.get('content', []) if c['type'] == 'quotes')
                print(f"    - {s['title']}: {n_paras}段落, {n_imgs}图片, {n_quotes}引用")
            print(f"  链接数: {len(d.get('links', []))}")
            print(f"  相关链接: {len(d.get('see_also', []))}")
            print(f"  简介: {d.get('intro', '')[:200]}")
    
    print("\n完成!")


if __name__ == "__main__":
    main()
