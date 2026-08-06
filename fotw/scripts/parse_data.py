#!/usr/bin/env python3
"""快速解析FOTW数据生成JSON索引（不依赖图片下载）"""
import sys
import re
import json
from pathlib import Path
from html import unescape
from html.parser import HTMLParser

BASE_DIR = Path(__file__).resolve().parent.parent
FLAGS_DIR = BASE_DIR / "flags"
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def parse_countries():
    """解析国家列表"""
    countries = []
    index_candidates = [FLAGS_DIR / "country.html", FLAGS_DIR / "index.html"]

    for idx_path in index_candidates:
        if idx_path.exists():
            with open(idx_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            pattern = r'<a\s+href="([a-z]{2}[^"]*\.html)"[^>]*>([^<]+)</a>'
            matches = re.findall(pattern, content, re.IGNORECASE)
            seen = set()
            for href, name in matches:
                code = href.replace(".html", "").strip()
                name = unescape(name.strip())
                if code and code not in seen and len(code) <= 15:
                    seen.add(code)
                    letter = code[0].lower() if code else "a"
                    countries.append({"code": code, "title": name, "letter": letter})
            print(f"从 {idx_path.name} 找到 {len(countries)} 个链接")
            if countries:
                break

    if not countries:
        for html_file in sorted(FLAGS_DIR.glob("??.html")):
            code = html_file.stem
            if code.isalpha():
                countries.append({"code": code, "title": code.upper(), "letter": code[0].lower()})
        print(f"扫描到 {len(countries)} 个两字母代码页面")

    return countries


class FOTWParser(HTMLParser):
    """简化的FOTW页面解析器"""
    def __init__(self):
        super().__init__()
        self.title = ""
        self.images = []
        self.sections = []
        self.links = []
        self.in_title = False
        self.in_h2 = False
        self.current_heading = ""
        self.current_content = []
        self.in_anchor = False
        self.current_href = ""
        self.current_anchor_text = []
        self.skip_header = True
        self.found_main = False
        self.text_buf = []

    def handle_starttag(self, tag, attrs):
        ad = dict(attrs)
        if tag == "title":
            self.in_title = True
        elif tag == "h2":
            self._flush()
            self.in_h2 = True
            self.current_heading = ""
        elif tag == "img":
            src = ad.get("src", "")
            alt = ad.get("alt", "")
            if src and ("../images/" in src or "../misc/" in src):
                self.images.append((src.replace("../", ""), unescape(alt)))
        elif tag == "a":
            href = ad.get("href", "")
            if href and not href.startswith("http") and not href.startswith("mailto:"):
                self.in_anchor = True
                self.current_href = href
                self.current_anchor_text = []
        elif tag == "hr":
            if self.found_main:
                self._flush()
            self.found_main = True
            self.skip_header = False

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False
        elif tag == "h2":
            self.in_h2 = False
        elif tag == "a" and self.in_anchor:
            self.in_anchor = False
            text = "".join(self.current_anchor_text).strip()
            if text and (self.current_href.endswith(".html") or "#" in self.current_href):
                clean = self.current_href.replace("../flags/", "").replace(".html", "")
                if not clean.startswith("http") and not clean.startswith("keyword"):
                    self.links.append((clean, text))

    def handle_data(self, data):
        if self.in_title:
            self.title += data
        elif self.in_h2:
            self.current_heading += data
        elif self.in_anchor:
            self.current_anchor_text.append(data)
        elif not self.skip_header:
            text = data.strip()
            if text:
                self.current_content.append(text)

    def _flush(self):
        content = " ".join(self.current_content).strip()
        content = re.sub(r'\s+', ' ', content)
        if self.current_heading and content:
            self.sections.append((unescape(self.current_heading.strip()), content[:2000]))
        elif content and self.sections:
            h, c = self.sections[-1]
            self.sections[-1] = (h, (c + " " + content)[:2000])
        self.current_content = []


def parse_detail(code):
    """解析单个页面详情"""
    html_path = FLAGS_DIR / f"{code}.html"
    if not html_path.exists():
        return None
    try:
        with open(html_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    except:
        return None

    parser = FOTWParser()
    try:
        parser.feed(content)
    except:
        return None

    kw_match = re.search(r'Keywords:\s*(.*?)(?:\||\n|<br|</p)', content, re.IGNORECASE)
    keywords = []
    if kw_match:
        kws = re.findall(r'>([^<]+)</a>', kw_match.group(1))
        keywords = [k.strip() for k in kws if k.strip()][:10]

    mod_match = re.search(r'Last modified:\s*\*\*([^*]+)\*\*', content)
    last_mod = mod_match.group(1).strip() if mod_match else ""

    main_img = ""
    letter = code[0].lower() if code else "a"
    for s, a in parser.images:
        if s.startswith("images/"):
            main_img = s
            break
    if not main_img:
        main_img = f"images/{letter}/{code}.gif"

    title = parser.title.strip()
    title = re.sub(r'\s*-\s*Flags of the World.*$', '', title, flags=re.IGNORECASE).strip()

    intro = ""
    for h, c in parser.sections:
        if not h and c:
            intro = c[:300]
            break

    return {
        "code": code,
        "title": title or code,
        "main_image": main_img,
        "images": parser.images[:15],
        "sections": parser.sections[:20],
        "links": parser.links[:40],
        "keywords": keywords,
        "last_modified": last_mod,
        "intro": intro,
    }


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
    for c in countries:
        code = c["code"]
        d = parse_detail(code)
        if d:
            d["title"] = c.get("title", d["title"])
            details[code] = d
            parsed += 1
        if parsed % 100 == 0 and parsed > 0:
            print(f"  已解析 {parsed}/{len(countries)}")

    with open(DATA_DIR / "flag_details.json", 'w', encoding='utf-8') as f:
        json.dump(details, f, ensure_ascii=False, indent=1)
    print(f"详情数据已保存: {parsed} 个页面")
    print("\n完成!")


if __name__ == "__main__":
    main()
