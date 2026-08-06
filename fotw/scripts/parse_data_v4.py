#!/usr/bin/env python3
"""改进的FOTW页面解析器 v4 - 线性顺序遍历，保留图片位置和内链"""
import sys
import os
import re
import json
from pathlib import Path
from html import unescape

try:
    from bs4 import BeautifulSoup, NavigableString, Tag, Comment
    HAVE_BS4 = True
except ImportError:
    HAVE_BS4 = False

BASE_DIR = Path(__file__).resolve().parent.parent
FLAGS_DIR = BASE_DIR / "flags"
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

VALID_CODES = set()


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
        return None
    anchor = ""
    if '#' in href and not href.startswith('#'):
        href, anchor = href.split('#', 1)
    elif href.startswith('#'):
        return {"type": "anchor", "href": href}
    original_href = href
    href = href.replace("../flags/", "").replace("../", "")
    if href.startswith("http") or href.startswith("mailto:"):
        return None
    if href.startswith("misc/"):
        return None
    if href.startswith("images/"):
        return None
    if href.endswith(".pdf") or href.endswith(".gif") or href.endswith(".jpg") or href.endswith(".png"):
        return None
    if href.endswith(".html") or href.endswith(".htm"):
        href = href.rsplit(".", 1)[0]
    if not href:
        if anchor:
            return {"type": "anchor", "href": "#" + anchor}
        return None
    return {"type": "flag", "code": href, "anchor": anchor}


def extract_custom_tags(html):
    info = {"subtitle": "", "keywords": [], "editor": ""}

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
    if src_lower.startswith('misc/'):
        return True
    skip_patterns = ['linea', 'fotwbckg', 'spacer', 'dot.', 'bullet', 'icon_',
                     'arrow', 'button', 'fissumry']
    for p in skip_patterns:
        if p in src_lower:
            return True
    return False

def find_existing_image(code, letter, preferred=None):
    base_dir = Path(__file__).parent.parent
    candidates = []
    if preferred:
        candidates.append(preferred)
    candidates.append(f"images/{letter}/{code}.gif")
    candidates.append(f"images/{letter}/{code}.jpg")
    candidates.append(f"images/{letter}/{code}.png")
    for cand in candidates:
        if (base_dir / cand).exists():
            return cand
        if cand.endswith(".gif") or cand.endswith(".jpg"):
            png_cand = cand.replace("images/", "images-png/").rsplit(".", 1)[0] + ".png"
            if (base_dir / png_cand).exists():
                return cand
    img_dir = base_dir / "images" / letter
    if img_dir.exists():
        code_lower = code.lower()
        gifs = sorted([f for f in os.listdir(img_dir)
                       if f.lower().startswith(code_lower) and f.lower().endswith(".gif")
                       and not is_image_skippable(f"images/{letter}/{f}")])
        if gifs:
            return f"images/{letter}/{gifs[0]}"
        jpgs = sorted([f for f in os.listdir(img_dir)
                       if f.lower().startswith(code_lower) and f.lower().endswith((".jpg", ".png"))
                       and not is_image_skippable(f"images/{letter}/{f}")])
        if jpgs:
            return f"images/{letter}/{jpgs[0]}"
    return candidates[0]


def infer_tags_from_code(code):
    """根据FOTW的code命名规则推断旗帜类型标签"""
    tags = set()
    if not code:
        return []
    cl = code.lower()

    # 已知的国际组织/非国家2字母代码（不应标记为national/civil）
    INTL_ORGS_2 = {'un', 'eu', 'ac', 'an'}
    # 已知的3+字母国际组织代码
    INTL_ORGS_3PLUS = {'nato', 'uno', 'unesco', 'unicef', 'who', 'imf', 'wto', 'asean',
                       'oas', 'oau', 'coe', 'cis', 'comecon', 'efta', 'gcc', 'nafta',
                       'oecd', 'opec', 'ifrc', 'ioc', 'fifa', 'uefa', 'irc', 'smom',
                       'scout', 'commonwealth', 'acp'}

    # 主国旗：纯2字母代码（如cn, us, jp, gg, ax, ah），但排除国际组织
    if re.match(r'^[a-z]{2}$', cl):
        if cl not in INTL_ORGS_2:
            tags.add('national')
            tags.add('civil')
            return sorted(tags)
        else:
            tags.add('international')
            tags.add('organization')
            return sorted(tags)

    # 特殊字符后缀（FOTW标准符号体系）
    if '^' in cl:
        tags.add('military')
        tags.add('armed_forces')
        if 'af' in cl or 'air' in cl:
            tags.add('air_force')
        if 'army' in cl or cl.endswith('^') or 'rank' in cl or 'war' in cl:
            tags.add('army')
            tags.add('war_flag')
    if '~' in cl:
        tags.add('naval')
        tags.add('maritime')
        tags.add('ensign')
        if 'yacht' in cl or 'yc' in cl or 'yct' in cl:
            tags.add('yacht')
        if 'hf' in cl or 'ship' in cl or 'merchant' in cl:
            tags.add('merchant')
            tags.add('corporate')
        if 'jack' in cl:
            tags.add('jack')
        if 'coast' in cl or 'cust' in cl:
            tags.add('coast_guard')
        if 'war' in cl or 'ensnn' in cl or 'ens' in cl:
            tags.add('war_ensign')
    if '}' in cl:
        tags.add('political')
        tags.add('political_party')
    if '@' in cl:
        tags.add('sports')
        if 'oly' in cl:
            tags.add('olympic')
        if 'foot' in cl or 'rugby' in cl or 'crick' in cl or 'fifa' in cl or 'football' in cl:
            tags.add('football')
    if '$' in cl:
        tags.add('corporate')
        if 'air' in cl or 'airline' in cl:
            tags.add('airline')
        if 'ship' in cl or 'hf' in cl:
            tags.add('shipping')
        if 'bank' in cl:
            tags.add('financial')
    if '!' in cl:
        tags.add('historical')
        tags.add('proposal')
    if '-' in cl:
        after = cl.split('-', 1)[1] if '-' in cl else ''
        if after.startswith('hist'):
            tags.add('historical')
        elif re.match(r'^[a-z]{1,4}-?$', after) or after == '':
            # -a-, -ag-, -ab- 等省份/州/市镇下的区划索引页
            tags.add('regional')
            tags.add('subdivision')
        # -gov, -pres 等政府相关
        if re.match(r'^(gov|pres|royal|minister)', after):
            tags.add('government')
            tags.add('official')
        # 历史
        if 'imper' in cl or 'empire' in cl or 'king' in cl or 'land' in cl or 'fiii' in cl or 'republic' in cl:
            tags.add('historical')
    # 下划线后缀
    if '_' in cl:
        parts = cl.split('_')
        for p in parts[1:]:
            if p in ('hist', 'his'):
                tags.add('historical')
            elif p == 'sub':
                tags.add('regional')
                tags.add('subdivision')
            elif p in ('pres', 'gov', 'government', 'emir', 'king', 'royal', 'queen', 'prince', 'min'):
                tags.add('government')
                tags.add('official')
            elif p in ('civ', 'civil'):
                tags.add('civil')
            elif p in ('mil', 'army', 'af', 'navy', 'def'):
                tags.add('military')
            elif p in ('oly', 'sport'):
                tags.add('sports')
            elif p in ('party',):
                tags.add('political')
            elif p in ('fire', 'police', 'cust', 'coast', 'pol'):
                tags.add('service')
            elif p in ('post', 'mail'):
                tags.add('postal')
            elif p.startswith('u') or 'univ' in p:
                tags.add('university')
            elif 'ethnic' in p:
                tags.add('ethnic')
                tags.add('cultural')
            elif p == 'fact' or p == 'laws' or p == 'stamp':
                pass  # 信息页，非旗帜
    # 单引号、圆括号
    if "'" in cl or '(' in cl or ')' in cl:
        tags.add('reported')
        tags.add('unofficial')

    # 常见关键词（在code任意位置）
    if re.search(r'hist|empire|kingdom|republic-\d|mon|habsburg|mandate|protectorate|colony|soviet|prussia|ottoman|byzantine|yugo|czech|us[sr]', cl):
        tags.add('historical')
    if re.search(r'(^|[-_])(nato|uno|unicef|unesco|who|imf|wto|asean|oas|oau|olympic|ioc|fifa|uefa|international|scout|smom|red[-_]cross|red[-_]crescent|arab[-_]league|commonwealth|coe|opec|oecd|efta|cis|comecon|nafta|gcc|acp|ifrc|irc)([-_]|$)', cl):
        tags.add('international')
        tags.add('organization')
    # eu/un/nato/uno 开头的代码（国际组织子页面）
    if cl == 'eu' or cl.startswith('eu_') or cl == 'un' or cl.startswith('un_') or \
       cl.startswith('uno') or cl.startswith('nato') or cl.startswith('unesco') or \
       cl.startswith('unicef') or cl.startswith('who') or cl.startswith('nato') or \
       cl.startswith('asean') or cl.startswith('coe') or cl.startswith('opec'):
        tags.add('international')
        tags.add('organization')
    if re.search(r'president|government|gov|royal|standard$|_emir|sultan|_pres|police|post|customs|coast|border', cl):
        tags.add('government')
    if re.search(r'city|municipal|capital|province|state|region|commune|district|county|canton|parish|town|village|municip', cl):
        tags.add('regional')
    # _index 索引页
    if '_index' in cl:
        if cl.startswith('xa') or cl.startswith('xg') or cl.startswith('xh') or 'indigen' in cl:
            tags.add('cultural')
            tags.add('ethnic')
        tags.add('regional')
    # cou_* 国家总览
    if cl.startswith('cou'):
        tags.add('national')
    # 3-5 个纯字母代码：判断是国际组织还是历史实体
    if re.match(r'^[a-z]{3,5}$', cl):
        intl_orgs = {'nato', 'uno', 'smom', 'unesco', 'unicef', 'who', 'imf', 'wto',
                     'asean', 'oas', 'oau', 'coe', 'cis', 'efta', 'gcc', 'oecd', 'opec',
                     'ifrc', 'ioc', 'fifa', 'uefa', 'irc', 'acp'}
        hist_entities = {'mpe', 'kos', 'nto', 'yug', 'su', 'rus', 'gdr', 'frg'}
        if cl in intl_orgs:
            tags.add('international')
            tags.add('organization')
        elif cl in hist_entities:
            tags.add('historical')
        elif not tags:
            tags.add('historical')

    # 如果没有任何tag，默认标记为other
    if not tags:
        tags.add('other')

    return sorted(tags)


def is_flag_page_code(code):
    """判断code是否是一个旗帜页面（而非index/search等功能页）"""
    if not code or len(code) > 30:
        return False
    cl = code.lower()
    skip_exact = {'index', 'search', 'disclaim', 'mailme', 'mirror', 'host',
                  'help', 'faq', 'about', 'contact', 'whatsnew', 'fis', 'awards',
                  'flag', 'flags', 'new', 'top', 'home', 'main', 'country',
                  'colour', 'color', 'update', 'editor', 'xf-fis', 'bib'}
    if cl in skip_exact:
        return False
    skip_starts = ['keyword', 'search', 'disclaim', 'mailme', 'mirror',
                   'host', 'help', 'faq', 'about', 'contact', 'whatsnew',
                   'fis', 'awards', 'colour', 'color', 'flag[', 'flag_',
                   'update', 'editor', 'xf-', 'bib-']
    for s in skip_starts:
        if cl.startswith(s):
            return False
    # 必须以字母开头
    if not cl[0].isalpha():
        return False
    return True


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
    return False


def render_inline_content(element):
    """递归渲染内联内容，保留链接和文本结构"""
    parts = []
    if isinstance(element, NavigableString):
        if isinstance(element, Comment):
            return ""
        text = str(element)
        if text.strip():
            return clean_text(unescape(text))
        return ""
    if not isinstance(element, Tag):
        return ""

    tag = element.name.lower()

    if tag == 'br':
        return " "
    if tag in ('script', 'style', 'noscript', 'hr'):
        return ""
    if tag == 'img':
        src = normalize_img_src(element.get('src', ''))
        alt = clean_text(unescape(element.get('alt', '')))
        if src and not is_image_skippable(src):
            return f"{{IMG:{src}|{alt}}}"
        return ""
    if tag == 'a':
        href = element.get('href', '')
        link_info = normalize_href(href)
        inner = ''.join(render_inline_content(child) for child in element.children)
        inner = inner.strip()
        if not inner:
            return ""
        if link_info is None:
            return inner
        if link_info["type"] == "anchor":
            return f"{{A:{link_info['href']}|{inner}}}"
        if link_info["type"] == "flag":
            code = link_info["code"]
            anchor = link_info.get("anchor", "")
            if is_link_navigational(code, inner):
                return inner
            if code not in VALID_CODES:
                return inner
            if anchor:
                return f"{{L:{code}#{anchor}|{inner}}}"
            return f"{{L:{code}|{inner}}}"
        return inner
    if tag in ('strong', 'b'):
        inner = ''.join(render_inline_content(child) for child in element.children)
        return f"**{inner.strip()}**" if inner.strip() else ""
    if tag in ('em', 'i'):
        inner = ''.join(render_inline_content(child) for child in element.children)
        return f"*{inner.strip()}*" if inner.strip() else ""
    if tag == 'small':
        return ""

    inner = ''.join(render_inline_content(child) for child in element.children)
    return inner


def process_element(element, img_counter, all_images, toc_items, see_also_links):
    """处理单个元素，返回内容块列表"""
    blocks = []
    if isinstance(element, NavigableString):
        return blocks
    if not isinstance(element, Tag):
        return blocks

    tag = element.name.lower()

    if tag in ('script', 'style', 'noscript', 'hr', 'br', 'small', 'sup'):
        return blocks

    if tag in ('h1', 'h2', 'h3', 'h4'):
        text = clean_text(element.get_text())
        if not text or len(text) > 200:
            return blocks
        text_lower = text.lower().strip(':').strip()
        if text_lower in ('navigation', 'nav'):
            return blocks
        a_tag = element.find('a')
        anchor = ""
        if a_tag:
            anchor = a_tag.get('name', '') or a_tag.get('id', '')
        if not anchor:
            anchor = element.get('id', '')
        if text_lower == 'see also':
            see_also_links["active"] = True
        else:
            see_also_links["active"] = False
        level = int(tag[1])
        blocks.append({
            "type": "heading",
            "level": level,
            "text": text,
            "anchor": anchor
        })
        if level <= 2 and anchor and text_lower not in ('see also',):
            existing_anchors = {t["anchor"] for t in toc_items}
            if anchor not in existing_anchors:
                toc_items.append({"text": text, "anchor": anchor})
        return blocks

    if tag == 'ul' or tag == 'ol':
        items = []
        list_links = []
        is_see_also = see_also_links.get("active", False)

        for li in element.find_all('li', recursive=False):
            li_text = ''.join(render_inline_content(c) for c in li.children)
            li_text = clean_text(li_text)
            if li_text and len(li_text) < 500:
                items.append(li_text)
            for a in li.find_all('a'):
                href = a.get('href', '')
                t = clean_text(a.get_text())
                link_info = normalize_href(href)
                if link_info and link_info["type"] == "flag" and t:
                    if link_info["code"] in VALID_CODES and not is_link_navigational(link_info["code"], t):
                        list_links.append({"code": link_info["code"], "title": t})
                        if is_see_also:
                            see_also_links["links"].append({"code": link_info["code"], "title": t})

        is_toc = False
        if not see_also_links.get("active", False):
            anchor_links = 0
            for li in element.find_all('li', recursive=False):
                for a in li.find_all('a'):
                    href = a.get('href', '')
                    if href.startswith('#'):
                        anchor_links += 1
            if anchor_links >= 2 and len(items) <= 15:
                is_toc = True
                for li in element.find_all('li', recursive=False):
                    for a in li.find_all('a'):
                        href = a.get('href', '')
                        t = clean_text(a.get_text())
                        if href.startswith('#') and t:
                            toc_items.append({"text": t, "anchor": href[1:]})
                return blocks

        if is_see_also:
            for l in list_links:
                if l not in see_also_links["links"]:
                    see_also_links["links"].append(l)
            return blocks

        is_nav = False
        if items and len(items) <= 10:
            all_nav = all(len(i) < 80 for i in items)
            link_ratio = len(list_links) / max(len(items), 1)
            if all_nav and link_ratio > 0.5:
                is_nav = True
        if len(items) <= 10 and all(len(i) < 60 for i in items):
            for i in items:
                if re.search(r'(construction|vertical|anniversary|use of|history|symbol|colour|color|origin|law)', i.lower()):
                    is_nav = False
                    break

        if not is_nav and items:
            blocks.append({
                "type": "list",
                "items": items[:25]
            })
        elif list_links:
            pass
        return blocks

    if tag == 'blockquote':
        text = ''.join(render_inline_content(c) for c in element.children)
        text = clean_text(text)
        if text and len(text) > 10:
            blocks.append({
                "type": "quote",
                "text": text[:2000]
            })
        return blocks

    if tag == 'pre':
        text = clean_text(element.get_text())
        if text:
            blocks.append({
                "type": "paragraph",
                "text": text[:2000]
            })
        return blocks

    if tag == 'table':
        table_text = clean_text(element.get_text())
        table_links = []
        table_imgs = []
        for a in element.find_all('a'):
            href = a.get('href', '')
            t = clean_text(a.get_text())
            link_info = normalize_href(href)
            if link_info and link_info["type"] == "flag" and t:
                if not is_link_navigational(link_info["code"], t):
                    table_links.append({"code": link_info["code"], "title": t})
        for img in element.find_all('img'):
            src = normalize_img_src(img.get('src', ''))
            alt = clean_text(unescape(img.get('alt', '')))
            if src and not is_image_skippable(src):
                table_imgs.append({"src": src, "alt": alt})

        is_nav = len(table_links) > 3 and len(table_text) < len(table_links) * 40
        if is_nav:
            return blocks

        for img_info in table_imgs:
            img_id = f"img{img_counter['count']}"
            img_counter['count'] += 1
            all_images.append({
                "id": img_id,
                "src": img_info["src"],
                "alt": img_info["alt"]
            })
            blocks.append({
                "type": "image",
                "id": img_id,
                "src": img_info["src"],
                "alt": img_info["alt"]
            })

        if table_text and len(table_text) > 50:
            blocks.append({
                "type": "paragraph",
                "text": table_text[:2000]
            })
        return blocks

    if tag == 'p' or tag == 'div':
        text = ''.join(render_inline_content(c) for c in element.children)
        text = clean_text(text)

        p_images = []
        for img in element.find_all('img'):
            src = normalize_img_src(img.get('src', ''))
            alt = clean_text(unescape(img.get('alt', '')))
            if src and not is_image_skippable(src):
                p_images.append({"src": src, "alt": alt})

        is_only_image = len(p_images) > 0 and len(re.sub(r'\{IMG:[^}]+\}', '', text).strip()) < 30

        for img_info in p_images:
            img_id = f"img{img_counter['count']}"
            img_counter['count'] += 1
            all_images.append({
                "id": img_id,
                "src": img_info["src"],
                "alt": img_info["alt"]
            })
            blocks.append({
                "type": "image",
                "id": img_id,
                "src": img_info["src"],
                "alt": img_info["alt"]
            })

        if not is_only_image and text and len(re.sub(r'\{IMG:[^}]+\}', '', text).strip()) > 10:
            cleaned_text = text
            cleaned_text = re.sub(r'^\s*\d+:\d+\s*(;|,|\|)?\s*(image by|by\s|Image by[^.]+\.?\s*)?', '', cleaned_text, flags=re.I)
            cleaned_text = re.sub(r'^(image by|by\s|Image by[^.]+\.?\s*)', '', cleaned_text, flags=re.I)
            cleaned_text = re.sub(r'^\{L:[^}]+\}\s*', '', cleaned_text)
            cleaned_text = cleaned_text.strip()
            if cleaned_text and len(cleaned_text) > 10:
                blocks.append({
                    "type": "paragraph",
                    "text": cleaned_text[:2000]
                })

        for a in element.find_all('a'):
            href = a.get('href', '')
            t = clean_text(a.get_text())
            link_info = normalize_href(href)
            if link_info and link_info["type"] == "flag" and t:
                if see_also_links.get("active", False):
                    see_also_links["links"].append({"code": link_info["code"], "title": t})
        return blocks

    for child in element.children:
        blocks.extend(process_element(child, img_counter, all_images, toc_items, see_also_links))

    return blocks


def extract_intro(blocks):
    paras = []
    for b in blocks:
        if b["type"] == "paragraph":
            t = b["text"]
            t = re.sub(r'\{IMG:[^}]+\}', '', t)
            t = re.sub(r'\d+\s*:\s*\d+\s*', '', t)
            t = re.sub(r'image\s+by\s+[^,.|]+(?:,\s*\d+\s+\w+\s+\d+)?\.?\s*', '', t, flags=re.I)
            t = re.sub(r'^\s*(by\s+)', '', t, flags=re.I)
            t = re.sub(r'^\{L:[^}]+\}\s*', '', t)
            t = re.sub(r'\*[^*]+\*,\s*\d+\s+\w+\s+\d+', '', t)
            t = t.strip()
            if t and len(t) > 40:
                paras.append(t)
            if len(paras) >= 2:
                break
    if not paras:
        return ""
    intro = " ".join(paras)[:600]
    intro = re.sub(r'\{L:([^|]+)\|([^}]+)\}', r'\2', intro)
    intro = re.sub(r'\{A:([^|]+)\|([^}]+)\}', r'\2', intro)
    intro = re.sub(r'\*\*([^*]+)\*\*', r'\1', intro)
    intro = re.sub(r'\*([^*]+)\*', r'\1', intro)
    intro = re.sub(r'\s+', ' ', intro).strip()
    if intro and len(intro) < 40:
        return ""
    return intro


def is_duplicate_paragraph(text, existing):
    if not text or len(text) < 30:
        return True
    t_lower = text.lower()[:100]
    for old in existing:
        if t_lower == old.lower()[:100]:
            return True
        if len(text) > 50 and len(old) > 50:
            if text in old or old in text:
                overlap = min(len(text), len(old)) / max(len(text), len(old))
                if overlap > 0.7:
                    return True
    return False


def parse_with_bs4(html_content, code):
    soup = BeautifulSoup(html_content, 'html.parser')

    result = {
        "code": code,
        "title": "",
        "subtitle": "",
        "main_image": "",
        "flag_ratio": "",
        "toc": [],
        "all_flags": [],
        "content_blocks": [],
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
        h1_text = clean_text(h1_tag.get_text())
        if h1_text and len(h1_text) > 2:
            result["title"] = h1_text

    mod_match = re.search(r'Last modified:\s*(?:<strong>|<b>)?([^<\n|*]+)', html_content, re.IGNORECASE)
    if mod_match:
        result["last_modified"] = clean_text(unescape(mod_match.group(1)))

    cut_idx = html_content.find('<!--CUT ABOVE-->')
    if cut_idx >= 0:
        main_html = html_content[cut_idx + len('<!--CUT ABOVE-->'):]
    else:
        body_tag = soup.find('body')
        if body_tag:
            main_html = str(body_tag)
        else:
            main_html = html_content

    main_soup = BeautifulSoup(main_html, 'html.parser')

    for bad in main_soup.find_all(['script', 'style', 'noscript']):
        bad.decompose()

    ratio_match = re.search(r'(\d+)\s*:\s*(\d+)', main_html[:2000])
    if ratio_match:
        result["flag_ratio"] = ratio_match.group(0)

    img_counter = {"count": 0}
    all_images = []
    toc_items = []
    see_also_links = {"active": False, "links": []}
    content_blocks = []

    elements_to_process = []

    def walk(el, in_block=False):
        escaped_block = False
        for child in el.children:
            if isinstance(child, NavigableString):
                continue
            if not isinstance(child, Tag):
                continue
            cname = child.name.lower()
            effective_in_block = in_block and not escaped_block

            if cname == 'hr' and effective_in_block:
                # hr是章节分隔符，不应该出现在列表/引用内。遇到hr说明后续内容是因HTML未闭合被错误嵌套的正文
                elements_to_process.append(child)
                escaped_block = True
                walk(child, in_block=False)
                continue
            if cname == 'a':
                walk(child, in_block=effective_in_block)
            elif cname in ('h1', 'h2', 'h3', 'h4', 'p') and effective_in_block:
                # 错误嵌套：在in_block状态下遇到block元素，且之前已遇到hr逃生，说明是被错误吞并的正文
                if escaped_block or cname in ('h1','h2','h3','h4'):
                    elements_to_process.append(child)
                    walk(child, in_block=False)
                else:
                    walk(child, in_block=True)
            elif cname in ('h1', 'h2', 'h3', 'h4', 'ul', 'ol', 'blockquote', 'pre', 'table', 'hr'):
                elements_to_process.append(child)
                walk(child, in_block=True)
            elif cname == 'p' and not effective_in_block:
                has_block_child = False
                for sub in child.children:
                    if isinstance(sub, Tag):
                        sname = sub.name.lower()
                        if sname in ('h1','h2','h3','h4','ul','ol','blockquote','pre','table','p','div'):
                            has_block_child = True
                            break
                if has_block_child:
                    walk(child, in_block=False)
                else:
                    elements_to_process.append(child)
            elif cname == 'div':
                walk(child, in_block=effective_in_block)
            elif cname in ('center', 'td', 'th', 'tr', 'li', 'body', 'html', 'font', 'dl', 'dd', 'dt'):
                walk(child, in_block=effective_in_block)
            else:
                pass

    walk(main_soup)

    # 收集游离在block外的独立img（直接在body/td/div/center下、不在任何block里的图片）
    # 这些图片在FOTW中很常见（如ah页面的主图直接在body下），需要作为独立image block处理
    BLOCK_TAGS_SET = {'h1','h2','h3','h4','p','ul','ol','blockquote','pre','table'}
    for img in main_soup.find_all('img'):
        src = normalize_img_src(img.get('src', ''))
        if not src or is_image_skippable(src):
            continue
        # 检查这个img是否已经在某个待处理的block中
        already_in_block = False
        for parent in img.parents:
            if parent is main_soup:
                break
            pname = parent.name.lower() if parent.name else ''
            if pname in BLOCK_TAGS_SET:
                already_in_block = True
                break
        if not already_in_block:
            # 创建一个wrapper span作为标记，用于后续处理
            wrapper = main_soup.new_tag('div', attrs={'data-loose-img': '1'})
            img.wrap(wrapper)
            elements_to_process.append(wrapper)

    elements_to_process.sort(key=lambda e: e.sourceline or 0)

    # 收集所有锚点<a name="xxx">，绑定到在它之后最近的heading
    anchor_map = {}
    all_anchors = []
    for a in main_soup.find_all('a'):
        aname = a.get('name', '') or a.get('id', '')
        href = a.get('href', '')
        if aname and not href:
            line = a.sourceline or 0
            all_anchors.append((line, aname))
    all_anchors.sort(key=lambda x: x[0])

    all_headings = []
    for h in elements_to_process:
        if h.name.lower() in ('h1','h2','h3','h4'):
            line = h.sourceline or 0
            all_headings.append((line, h))
    all_headings.sort(key=lambda x: x[0])

    anchor_idx = 0
    for hline, hel in all_headings:
        while anchor_idx < len(all_anchors) and all_anchors[anchor_idx][0] <= hline:
            anchor_map[id(hel)] = all_anchors[anchor_idx][1]
            anchor_idx += 1

    seen_elements = set()
    unique_elements = []
    for el in elements_to_process:
        if id(el) not in seen_elements:
            seen_elements.add(id(el))
            unique_elements.append(el)
    elements_to_process = unique_elements

    for element in elements_to_process:
        blocks = process_element(element, img_counter, all_images, toc_items, see_also_links)
        if element.name.lower() in ('h1','h2','h3','h4') and id(element) in anchor_map:
            for b in blocks:
                if b["type"] == "heading" and not b.get("anchor"):
                    b["anchor"] = anchor_map[id(element)]
                    existing_anchors = {t["anchor"] for t in toc_items}
                    if anchor_map[id(element)] not in existing_anchors:
                        toc_items.append({"text": b["text"], "anchor": anchor_map[id(element)]})
        content_blocks.extend(blocks)

    result["all_flags"] = all_images

    main_img = ""
    for img in all_images:
        s = img["src"].lower()
        if s.startswith("images/"):
            fname = s.split('/')[-1]
            if fname == f"{code.lower()}.gif" or fname == f"{code.lower()}.png":
                main_img = img["src"]
                break
    if not main_img and all_images:
        for img in all_images:
            if img["src"].startswith("images/"):
                main_img = img["src"]
                break
    if not main_img:
        letter = code[0].lower() if code else "a"
        main_img = f"images/{letter}/{code}.gif"
    letter_dp = code[0].lower() if code else "a"
    base_dir_dp = Path(__file__).parent.parent
    main_img_path = base_dir_dp / main_img if main_img else None
    if not main_img or not main_img_path.exists():
        main_img = find_existing_image(code, letter_dp, main_img)
    result["main_image"] = main_img
    # 验证main_img是否存在，否则找存在的替代
    _letter = code[0].lower() if code else "a"
    _base = Path(__file__).parent.parent
    if main_img and not (_base / main_img).exists():
        _png = main_img.replace("images/", "images-png/").rsplit(".", 1)[0] + ".png"
        if not (_base / _png).exists():
            main_img = find_existing_image(code, _letter, main_img)
            result["main_image"] = main_img

    final_blocks = []
    seen_paras = set()
    for block in content_blocks:
        if block["type"] == "paragraph":
            t = block["text"]
            key = t[:80].lower()
            if key in seen_paras:
                continue
            if is_duplicate_paragraph(t, [b["text"] for b in final_blocks if b["type"] == "paragraph"]):
                continue
            seen_paras.add(key)
        final_blocks.append(block)

    result["content_blocks"] = final_blocks
    result["toc"] = toc_items[:15]

    seen_see = set()
    unique_see = []
    for l in see_also_links["links"]:
        if l["code"] == code:
            continue
        if l["code"] not in seen_see:
            seen_see.add(l["code"])
            unique_see.append(l)
    result["see_also"] = unique_see[:30]

    all_links_set = set()
    all_links = []
    for block in final_blocks:
        if block["type"] == "paragraph":
            for m in re.finditer(r'\{L:([^|]+)\|([^}]+)\}', block["text"]):
                l_code, l_text = m.group(1), m.group(2)
                if l_code not in all_links_set and l_code != code:
                    if not is_link_navigational(l_code, l_text):
                        all_links_set.add(l_code)
                        all_links.append({"code": l_code, "title": l_text})
    result["links"] = all_links[:60]

    result["intro"] = extract_intro(final_blocks)

    return result


def parse_detail(code, deep=True):
    """解析详情页。deep=True时使用BS4完整解析，False时仅提取头部信息"""
    html_path = FLAGS_DIR / f"{code}.html"
    if not html_path.exists():
        return None
    try:
        with open(html_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    except:
        return None

    if not deep:
        return quick_parse_header(html_path, code)

    try:
        if HAVE_BS4:
            result = parse_with_bs4(content, code)
        else:
            result = quick_parse_header(html_path, code)
    except Exception as e:
        print(f"  Error parsing {code}: {e}")
        import traceback
        traceback.print_exc()
        return None

    if result.get("title"):
        result["title"] = re.sub(r'\s*-\s*Flags of the World.*$', '', result["title"], flags=re.IGNORECASE).strip()

    return result


def quick_parse_header(html_path, code):
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
        result["title"] = re.sub(r"\s*-\s*Flags of the World.*$", "", result["title"], flags=re.IGNORECASE).strip()

    info = extract_custom_tags(html_content)
    result["keywords"] = info["keywords"]
    result["editor"] = info["editor"]
    result["subtitle"] = info["subtitle"]

    letter = code[0].lower() if code else "a"
    default_path = f"images/{letter}/{code}.gif"
    all_found_imgs = []
    first_img = ""

    # 同时支持带引号和无引号的src属性
    img_tag_pattern = r'<img\b[^>]*>'
    for tag_m in re.finditer(img_tag_pattern, html_content, re.I):
        tag = tag_m.group(0)
        # 提取 src（优先带引号，回退无引号）
        src = ""
        src_quoted = re.search(r'\bsrc=(["\'])([^\'"]+)\1', tag, re.I)
        if src_quoted:
            src = normalize_img_src(src_quoted.group(2))
        else:
            src_unquoted = re.search(r'\bsrc=([^\s\'">]+)', tag, re.I)
            if src_unquoted:
                src = normalize_img_src(src_unquoted.group(1))
        # 提取 alt
        alt_text = ""
        alt_quoted = re.search(r'\balt=(["\'])([^\'"]*)\1', tag, re.I)
        if alt_quoted:
            alt_text = clean_text(unescape(alt_quoted.group(2)))
        else:
            alt_unquoted = re.search(r'\balt=([^\s\'">]+)', tag, re.I)
            if alt_unquoted:
                alt_text = clean_text(unescape(alt_unquoted.group(1)))
        if src and not is_image_skippable(src):
            all_found_imgs.append({"src": src, "alt": alt_text})
            if not first_img:
                first_img = src

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

    sub_pages = []
    code_prefix = code[:2].lower()
    SQ = chr(39)
    DQ = chr(34)
    # 支持带引号和无引号的href
    a_tag_pattern = r'<a\b[^>]*href\s*=\s*(["\'])([^"\']+\.html)\1[^>]*>(.*?)</a>|<a\b[^>]*href\s*=\s*([^\s\'"><]+\.html)[^>]*>(.*?)</a>'
    for m in re.finditer(a_tag_pattern, html_content, re.I | re.DOTALL):
        if m.group(1):
            href = m.group(2)
            text_inner = m.group(3)
        else:
            href = m.group(4)
            text_inner = m.group(5)
        text = clean_text(unescape(re.sub(r'<[^>]+>', '', text_inner or '')))
        if not href: continue
        if href.startswith('http'): continue
        if href.startswith('#') or href.startswith('mailto:') or href.startswith('javascript:'): continue
        href_clean = href.replace('../', '').rsplit('.', 1)[0]
        if href_clean.lower() == code.lower(): continue
        if not href_clean or not href_clean[0].isalnum(): continue
        # 关联到子页面：code_prefix匹配（比如il页匹配il-*），或者2字母+特殊字符的分类页匹配同2字母前缀
        cond = False
        if href_clean.lower().startswith(code_prefix):
            cond = True
        # 分类页（如 il^ ）也接受不含特殊后缀但字母匹配的子页面 il-xxx
        elif len(code) >= 2 and code[:2].isalpha() and href_clean.lower().startswith(code[:2].lower()):
            cond = True
        if cond and len(text) > 0 and len(href_clean) <= 30:
            sub_pages.append({"code": href_clean, "title": text})

    content_blocks = []
    # 先添加子页面链接（放在最前面）
    if sub_pages:
        content_blocks.append({
            "type": "sub_pages",
            "title": f"相关旗帜（{len(sub_pages)}个）",
            "links": sub_pages
        })

    # 提取段落文本，过滤模板内容
    boilerplate_patterns = [
        r'last\s+modified', r'keywords?:', r'^return\s+to', r'anything below this line',
        r'was not added by the editor', r'please report any errors',
        r'form for reporting errors', r'generated by'
    ]
    boilerplate_re = re.compile('|'.join(boilerplate_patterns), re.I)

    p_pattern = r'<p[^>]*>(.*?)</p>'
    para_count = 0
    for m in re.finditer(p_pattern, html_content, re.I | re.DOTALL):
        p_text = clean_text(unescape(re.sub(r'<[^>]+>', '', m.group(1))))
        if len(p_text) > 30 and not boilerplate_re.search(p_text):
            content_blocks.append({"type": "paragraph", "text": p_text})
            para_count += 1
            if para_count >= 5:
                break

    if not sub_pages and para_count == 0 and result.get("title"):
        content_blocks.append({
            "type": "paragraph",
            "text": f"这是「{result['title']}」的分类索引页面。"
        })

    result["content_blocks"] = content_blocks

    lm = re.search(r'Last modified:\s*<strong>([^<]+)</strong>', html_content, re.I)
    if lm:
        result["last_modified"] = clean_text(lm.group(1))

    return result


def parse_countries():
    """构建旗帜索引：主国旗 + 类型索引页 + 子页面"""
    countries = []
    seen = set()

    # 1. 从country.html加载主国旗列表（2字母）
    index_candidates = [FLAGS_DIR / "country.html", FLAGS_DIR / "index.html"]
    for idx_path in index_candidates:
        if idx_path.exists():
            with open(idx_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            pattern = r'<a\s+href="([a-z][a-z0-9_@!^~$)\(\'\-]*\.html)"[^>]*>([^<]+)</a>'
            matches = re.findall(pattern, content, re.IGNORECASE)
            for href, name in matches:
                c = href.replace(".html", "").strip()
                name = unescape(name.strip())
                if c and c not in seen and is_flag_page_code(c) and name and len(name) > 0:
                    if len(c) <= 30:
                        seen.add(c)
                        letter = c[0].lower() if c else "a"
                        tags = infer_tags_from_code(c)
                        countries.append({"code": c, "title": name, "letter": letter, "tags": tags,
                                          "is_main": len(c) == 2 and c.isalpha() and c not in {'un', 'eu', 'ac', 'an'}})
            print(f"从 {idx_path.name} 找到 {len(countries)} 个链接")
            if countries:
                break

    # 2. 扫描flags目录，添加所有代码形态合理的文件
    index_suffixes = ['^', '~', '}', '@', '$', '!', '-', "'", '(', ')']
    extra_suffixes = ['_hist', '_sub', '_pres', '_gov', '_civ', '_mil', '_oly', '_pol']
    added_from_scan = 0
    for html_file in sorted(FLAGS_DIR.glob("*.html")):
        code = html_file.stem
        if code in seen:
            continue
        if not is_flag_page_code(code):
            continue
        cl = code.lower()
        should_add = False
        # 两字母代码（兜底）
        if re.match(r'^[a-z]{2}$', cl):
            should_add = True
        # 3-5字母国际组织代码
        elif re.match(r'^[a-z]{3,5}$', cl):
            intl_orgs_3plus = {'nato', 'uno', 'unesco', 'unicef', 'who', 'imf', 'wto', 'asean',
                               'oas', 'oau', 'coe', 'cis', 'comecon', 'efta', 'gcc', 'nafta',
                               'oecd', 'opec', 'ifrc', 'ioc', 'fifa', 'uefa', 'irc', 'smom',
                               'scout', 'commonwealth', 'acp'}
            if cl in intl_orgs_3plus:
                should_add = True
        # 国际组织子页面
        elif re.match(r'^(eu|un|uno|nato|unesco|unicef|who|imf|wto|asean|coe|opec)[-_^~@$!]', cl):
            should_add = True
        # 单个特殊字符结尾（类型总页）
        elif len(cl) >= 2 and cl[-1] in index_suffixes and cl[-2].isalpha():
            should_add = True
        # 下划线后缀的关键类型
        else:
            for suf in extra_suffixes:
                if cl.endswith(suf):
                    should_add = True
                    break
        # 2字母前缀 + 分隔符(连字符/下划线/特殊字符) + 任意内容：地方/军事/子旗帜
        # 如 il-acre, il!1947, il_bname
        if not should_add and len(cl) >= 4:
            if re.match(r'^[a-z]{2}[_~\-\^@$!\'(][\w\-\^@$!\'\(\)~]{1,28}$', cl):
                should_add = True

        if should_add and len(cl) <= 30:
            header = quick_parse_header(html_file, code)
            if header and header["title"]:
                title_lower = header["title"].lower()
                code_lower = code.lower()
                is_meaningful_title = (title_lower != code_lower) or \
                    (header["title"] == header["title"].upper() and len(code) >= 3) or \
                    bool(header.get("main_image"))
                if is_meaningful_title:
                    seen.add(code)
                    letter = code[0].lower() if code else "a"
                    tags = infer_tags_from_code(code)
                    is_main = bool(re.match(r'^[a-z]{2}$', cl)) and cl not in {'un', 'eu', 'ac', 'an'}
                    countries.append({"code": code, "title": header["title"], "letter": letter,
                                      "tags": tags, "is_main": is_main})
                    added_from_scan += 1

    print(f"扫描目录新增 {added_from_scan} 个条目，总计 {len(countries)} 个（准备扩展子页面）")

    # 3. 从每个分类/主页面的子页面链接再扩充一轮（解决 il^ 提到但没在目录扫描匹配到的）
    pending_checks = [c for c in countries if not c.get("is_main") or len(c["code"]) <= 3]
    extra_added = 0
    for c in pending_checks:
        code = c["code"]
        html_path = FLAGS_DIR / f"{code}.html"
        if not html_path.exists():
            continue
        try:
            with open(html_path, 'r', encoding='utf-8', errors='ignore') as f:
                html_content = f.read()
        except Exception:
            continue
        # 提取子页面链接（同2字母前缀）
        code2 = code[:2].lower()
        SQ, DQ = chr(39), chr(34)
        a_pat = r'<a\b[^>]*href\s*=\s*(["\'])([^"\']+\.html)\1[^>]*>(.*?)</a>|<a\b[^>]*href\s*=\s*([^\s\'"><]+\.html)[^>]*>(.*?)</a>'
        for m in re.finditer(a_pat, html_content, re.I | re.DOTALL):
            if m.group(1):
                href = m.group(2); tinner = m.group(3)
            else:
                href = m.group(4); tinner = m.group(5)
            if not href or href.startswith('http') or href.startswith('#') or href.startswith('mailto'):
                continue
            sub_code = href.replace('../', '').rsplit('.', 1)[0]
            if sub_code in seen:
                continue
            if not is_flag_page_code(sub_code):
                continue
            if not sub_code.lower().startswith(code2):
                continue
            ttext = clean_text(unescape(re.sub(r'<[^>]+>', '', tinner or '')))
            if len(ttext) < 2:
                continue
            sub_path = FLAGS_DIR / f"{sub_code}.html"
            if not sub_path.exists():
                continue
            sub_header = quick_parse_header(sub_path, sub_code)
            if not sub_header:
                continue
            stitle = sub_header.get("title") or ttext
            seen.add(sub_code)
            letter = sub_code[0].lower() if sub_code else 'a'
            tags = infer_tags_from_code(sub_code)
            # 从父页面继承部分标签
            parent_tags = c.get("tags", [])
            tags = list(dict.fromkeys(tags + [t for t in parent_tags if t not in tags]))
            countries.append({"code": sub_code, "title": stitle, "letter": letter,
                              "tags": tags, "is_main": False})
            extra_added += 1
    print(f"从分类页子链接扩展新增 {extra_added} 个条目，总计 {len(countries)} 个")
    return countries


def main():
    print("=== 解析国家列表 ===")
    countries = parse_countries()
    
    global VALID_CODES
    VALID_CODES = {c["code"] for c in countries}

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
    light_parsed = 0
    errors = 0
    for c in countries:
        code = c["code"]
        is_main = c.get("is_main", False)
        # 主国旗(is_main)和所有is_main页做深度解析，其他轻量解析
        deep = is_main
        d = parse_detail(code, deep=deep)
        if d:
            d["title"] = c.get("title", d.get("title", code))
            d["tags"] = c.get("tags", infer_tags_from_code(code))
            d["is_main"] = is_main
            # 合并keywords（从页面KEYWORDS标签获取）
            page_kws = d.get("keywords", [])
            code_tags = c.get("tags", [])
            all_kws = list(dict.fromkeys(page_kws + code_tags))
            d["keywords"] = all_kws[:20]
            details[code] = d
            if deep:
                parsed += 1
            else:
                light_parsed += 1
        else:
            errors += 1
        total_done = parsed + light_parsed
        if total_done % 100 == 0 and total_done > 0:
            print(f"  已处理 {total_done}/{len(countries)} (深度:{parsed}, 轻量:{light_parsed}, 错误:{errors})")

    with open(DATA_DIR / "flag_details.json", 'w', encoding='utf-8') as f:
        json.dump(details, f, ensure_ascii=False, indent=1)
    print(f"详情数据已保存: 深度解析 {parsed} 个，轻量解析 {light_parsed} 个 (错误: {errors})")

    # 同步详情字段回countries并重写countries.json
    for c in countries:
        code = c["code"]
        if code in details:
            det = details[code]
            if det.get("main_image"):
                c["main_image"] = det["main_image"]
            if det.get("intro"):
                c["intro"] = det["intro"][:200]
            page_kws = det.get("keywords", []) or []
            if page_kws:
                ex = c.get("keywords", []) or []
                merged = list(dict.fromkeys(ex + page_kws))
                c["keywords"] = merged[:20]

    with open(DATA_DIR / "countries.json", 'w', encoding='utf-8') as f:
        json.dump({"total": len(countries), "by_letter": by_letter, "countries": countries},
                  f, ensure_ascii=False, indent=1)
    print(f"已同步详情字段回国家索引: {len(countries)} 个条目")

    test_codes = ['cn', 'us', 'jp', 'fr']
    for code in test_codes:
        if code in details:
            d = details[code]
            print(f"\n示例 - {d['title']}:")
            print(f"  副标题: {d.get('subtitle', '')[:60]}")
            print(f"  比例: {d.get('flag_ratio', '')}")
            print(f"  图片数: {len(d.get('all_flags', []))}")
            print(f"  目录项: {len(d.get('toc', []))}")
            print(f"  内容块: {len(d.get('content_blocks', []))}")
            type_counts = {}
            for b in d.get('content_blocks', []):
                t = b['type']
                type_counts[t] = type_counts.get(t, 0) + 1
            print(f"    块类型: {type_counts}")
            print(f"  简介: {d.get('intro', '')[:150]}")

    print("\n完成!")


if __name__ == "__main__":
    main()
