#!/usr/bin/env python3
"""
FOTW (Flags of the World) 下载和解析脚本
从官方源下载完整数据集，解析HTML提取结构化数据，将GIF转为PNG
"""

import os
import sys
import zipfile
import urllib.request
import re
import json
import shutil
from pathlib import Path
from html.parser import HTMLParser
from html import unescape

# 路径配置
BASE_DIR = Path(__file__).resolve().parent.parent
ZIPS_DIR = BASE_DIR / "zips"
FLAGS_DIR = BASE_DIR / "flags"
IMAGES_DIR = BASE_DIR / "images"
MISC_DIR = BASE_DIR / "misc"
DATA_DIR = BASE_DIR / "data"
IMAGES_PNG_DIR = BASE_DIR / "images-png"

# 官方下载URL
BASE_URL = "https://www.acadiau.ca/~raeside/fotw/mirrors/monthlys"
ZIP_FILES = {
    "allflags.zip": f"{BASE_URL}/allflags.zip",
    "allimages.zip": f"{BASE_URL}/allimages.zip",
    "allmisc.zip": f"{BASE_URL}/allmisc.zip",
}


def download_file(url, dest_path, desc=""):
    """下载文件，显示进度"""
    if dest_path.exists():
        size_mb = dest_path.stat().st_size / (1024 * 1024)
        print(f"  [跳过] {desc} 已存在 ({size_mb:.1f} MB)")
        return True

    print(f"  [下载] {desc} ...")
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    def report_progress(block_num, block_size, total_size):
        downloaded = block_num * block_size
        if total_size > 0:
            pct = min(100, downloaded * 100 // total_size)
            mb = downloaded / (1024 * 1024)
            total_mb = total_size / (1024 * 1024)
            print(f"\r    {mb:.1f}/{total_mb:.1f} MB ({pct}%)", end="", flush=True)

    try:
        urllib.request.urlretrieve(url, str(dest_path), reporthook=report_progress)
        print()
        return True
    except Exception as e:
        print(f"\n  [错误] 下载失败: {e}")
        return False


def extract_zip(zip_path, extract_to, desc=""):
    """解压zip文件"""
    print(f"  [解压] {desc} ...")
    extract_to.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(str(zip_path), 'r') as zf:
            zf.extractall(str(extract_to))
        print(f"    完成")
        return True
    except Exception as e:
        print(f"  [错误] 解压失败: {e}")
        return False


class FOTWPageParser(HTMLParser):
    """解析FOTW HTML页面，提取旗帜信息"""

    def __init__(self):
        super().__init__()
        self.title = ""
        self.images = []  # [(src, alt_text)]
        self.sections = []  # [(heading, content)]
        self.links = []  # [(href, text)]
        self.keywords = []
        self.last_modified = ""
        self.in_title = False
        self.in_h2 = False
        self.current_heading = ""
        self.current_content = []
        self.in_anchor = False
        self.current_href = ""
        self.current_anchor_text = []
        self.skip_header = True  # 跳过FOTW标准头部
        self.in_italics = False
        self.text_buffer = []
        self.found_main_content = False

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag == "title":
            self.in_title = True
        elif tag == "h2":
            self._flush_section()
            self.in_h2 = True
            self.current_heading = ""
        elif tag == "img":
            src = attrs_dict.get("src", "")
            alt = attrs_dict.get("alt", "")
            if src and ("../images/" in src or "../misc/" in src):
                # 规范化图片路径
                clean_src = src.replace("../", "")
                self.images.append((clean_src, unescape(alt)))
        elif tag == "a":
            href = attrs_dict.get("href", "")
            if href and not href.startswith("http") and not href.startswith("mailto:"):
                self.in_anchor = True
                self.current_href = href
                self.current_anchor_text = []
        elif tag == "i" or tag == "em":
            self.in_italics = True
        elif tag == "br":
            self.text_buffer.append("\n")
        elif tag == "p":
            self.text_buffer.append("\n")
        elif tag == "hr":
            if self.found_main_content:
                self._flush_section()
            self.found_main_content = True
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
                clean_href = self.current_href.replace("../flags/", "").replace(".html", "")
                self.links.append((clean_href, text))
        elif tag in ("i", "em"):
            self.in_italics = False

    def handle_data(self, data):
        text = data.strip()
        if self.in_title:
            self.title += data
        elif self.in_h2:
            self.current_heading += data
        elif self.in_anchor:
            self.current_anchor_text.append(data)
        elif not self.skip_header:
            self.text_buffer.append(data)
            if self.in_italics:
                self.current_content.append(f"_{text}_")
            else:
                self.current_content.append(text)

    def _flush_section(self):
        content = " ".join(self.current_content).strip()
        content = re.sub(r'\s+', ' ', content)
        if self.current_heading and content:
            self.sections.append((unescape(self.current_heading.strip()), content))
        elif content and not self.current_heading and self.sections:
            # 追加到上一个section
            prev_heading, prev_content = self.sections[-1]
            self.sections[-1] = (prev_heading, prev_content + " " + content)
        self.current_content = []


def parse_country_page(html_path):
    """解析单个国家/旗帜页面"""
    try:
        with open(html_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    except:
        return None

    parser = FOTWPageParser()
    try:
        parser.feed(content)
    except:
        return None

    # 提取国家代码（从文件名）
    code = html_path.stem
    if code.endswith('.html'):
        code = code[:-5]

    # 提取关键词
    kw_match = re.search(r'Keywords:\s*(.*?)(?:\||\n|<br|</p)', content, re.IGNORECASE)
    keywords = []
    if kw_match:
        kw_text = kw_match.group(1)
        kw_links = re.findall(r'>([^<]+)</a>', kw_text)
        keywords = [k.strip() for k in kw_links if k.strip()]

    # 提取修改日期
    mod_match = re.search(r'Last modified:\s*\*\*([^*]+)\*\*', content)
    last_modified = mod_match.group(1).strip() if mod_match else ""

    # 提取国旗主图（第一个images路径）
    main_image = ""
    for img_src, img_alt in parser.images:
        if img_src.startswith("images/"):
            main_image = img_src
            break

    # 提取页面标题（国家名称）
    title = parser.title.strip()
    # 清理标题
    title = re.sub(r'\s*-\s*Flags of the World.*$', '', title, flags=re.IGNORECASE)
    title = title.strip()

    # 提取正文简介（第一个非空section之前的文本）
    intro = ""
    for heading, section_content in parser.sections:
        if not heading and section_content:
            intro = section_content[:500]
            break

    return {
        "code": code,
        "title": title or code,
        "main_image": main_image,
        "images": parser.images[:20],  # 限制图片数量
        "sections": parser.sections[:30],  # 限制段落数量
        "links": parser.links[:50],  # 限制链接数量
        "keywords": keywords,
        "last_modified": last_modified,
        "intro": intro[:300] if intro else "",
    }


def parse_index_pages():
    """解析索引页面，构建国家列表和分类"""
    countries = []

    # 解析国家索引页面（country.html 或 index.html）
    index_candidates = [
        FLAGS_DIR / "country.html",
        FLAGS_DIR / "index.html",
    ]

    for idx_path in index_candidates:
        if idx_path.exists():
            countries = _parse_country_index(idx_path)
            if countries:
                break

    # 如果没找到索引，扫描所有HTML文件
    if not countries:
        print("  [扫描] 未找到索引页，扫描所有HTML文件...")
        for html_file in sorted(FLAGS_DIR.glob("*.html")):
            code = html_file.stem
            # 跳过非国家页面（索引页、特殊页面等）
            if code.startswith("x-") or code.startswith("xf-") or code.startswith("g_"):
                continue
            if code in ("index", "country", "keyword", "title", "search",
                       "disclaim", "mirror", "host", "int", "mailme"):
                continue
            countries.append({"code": code, "title": code, "letter": code[0].lower() if code else "a"})

    return countries


def _parse_country_index(html_path):
    """解析国家索引页"""
    countries = []
    try:
        with open(html_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    except:
        return countries

    # 找所有指向国家页面的链接
    # 格式通常是 <a href="xx.html">Country Name</a>
    pattern = r'<a\s+href="([a-z]{2}[^"]*\.html)"[^>]*>([^<]+)</a>'
    matches = re.findall(pattern, content, re.IGNORECASE)

    seen = set()
    for href, name in matches:
        code = href.replace(".html", "").strip()
        name = unescape(name.strip())
        if code and code not in seen and len(code) <= 10:
            seen.add(code)
            letter = code[0].lower() if code else "a"
            countries.append({"code": code, "title": name, "letter": letter})

    return countries


def convert_gif_to_png():
    """将GIF图片转换为PNG格式"""
    print("\n[步骤3] 转换GIF为PNG...")
    IMAGES_PNG_DIR.mkdir(parents=True, exist_ok=True)

    try:
        from PIL import Image
    except ImportError:
        print("  [安装] Pillow 库用于图片转换...")
        os.system(f"{sys.executable} -m pip install Pillow")
        from PIL import Image

    count = 0
    errors = 0
    gif_files = list(IMAGES_DIR.rglob("*.gif"))
    total = len(gif_files)
    print(f"  共 {total} 个GIF文件待转换")

    for gif_path in gif_files:
        try:
            # 保持目录结构
            rel_path = gif_path.relative_to(IMAGES_DIR)
            png_path = IMAGES_PNG_DIR / rel_path.with_suffix('.png')
            png_path.parent.mkdir(parents=True, exist_ok=True)

            if png_path.exists():
                count += 1
                continue

            img = Image.open(str(gif_path))
            # 转换为RGBA以支持透明
            if img.mode in ('P', 'L'):
                img = img.convert('RGBA')
            elif img.mode == 'RGB':
                img = img.convert('RGBA')
            img.save(str(png_path), 'PNG')
            count += 1

            if count % 5000 == 0:
                print(f"    已转换 {count}/{total}")
        except Exception as e:
            errors += 1
            if errors <= 5:
                print(f"    [警告] {gif_path.name}: {e}")

    print(f"  完成: {count} 个转换, {errors} 个错误")


def generate_json_index(countries):
    """生成JSON索引文件供前端使用"""
    print("\n[步骤4] 生成JSON索引...")
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # 按字母分组
    by_letter = {}
    for c in countries:
        letter = c.get("letter", c["code"][0].lower() if c["code"] else "a")
        if letter not in by_letter:
            by_letter[letter] = []
        by_letter[letter].append(c)

    # 写入国家列表索引
    index_data = {
        "total": len(countries),
        "by_letter": by_letter,
        "countries": countries,
    }

    with open(DATA_DIR / "countries.json", 'w', encoding='utf-8') as f:
        json.dump(index_data, f, ensure_ascii=False, indent=1)
    print(f"  国家索引: {len(countries)} 个国家/地区")

    # 解析每个国家页面的详细数据
    print("  解析国家页面详情（这可能需要几分钟）...")
    details = {}
    parsed = 0
    for c in countries:
        code = c["code"]
        html_path = FLAGS_DIR / f"{code}.html"
        if html_path.exists():
            detail = parse_country_page(html_path)
            if detail:
                # 合并基本信息
                detail["title"] = c.get("title", detail["title"])
                details[code] = detail
                parsed += 1
                if parsed % 100 == 0:
                    print(f"    已解析 {parsed}/{len(countries)}")

    with open(DATA_DIR / "flag_details.json", 'w', encoding='utf-8') as f:
        json.dump(details, f, ensure_ascii=False, indent=1)
    print(f"  详情数据: {parsed} 个页面")

    # 统计图片数量
    img_count = sum(1 for _ in IMAGES_DIR.rglob("*.gif")) if IMAGES_DIR.exists() else 0
    print(f"  旗帜图片: {img_count} 个GIF")


def main():
    print("=" * 60)
    print("FOTW (Flags of the World) 数据下载和解析工具")
    print("=" * 60)

    # 步骤1: 下载zip文件
    print("\n[步骤1] 下载FOTW官方数据包...")
    print("  注意: 全部文件约2.5GB，下载可能需要较长时间")
    ZIPS_DIR.mkdir(parents=True, exist_ok=True)

    for filename, url in ZIP_FILES.items():
        zip_path = ZIPS_DIR / filename
        desc_map = {
            "allflags.zip": "页面文件 (allflags.zip, ~166MB)",
            "allimages.zip": "旗帜图片 (allimages.zip, ~2.3GB)",
            "allmisc.zip": "杂项文件 (allmisc.zip, ~76MB)",
        }
        success = download_file(url, zip_path, desc_map.get(filename, filename))
        if not success:
            print(f"  [警告] {filename} 下载失败，继续处理其他文件...")

    # 步骤2: 解压
    print("\n[步骤2] 解压文件...")
    for zip_name in ["allmisc.zip", "allflags.zip", "allimages.zip"]:
        zip_path = ZIPS_DIR / zip_name
        if not zip_path.exists():
            print(f"  [跳过] {zip_name} 不存在")
            continue

        if zip_name == "allflags.zip":
            target = BASE_DIR  # 解压到fotw/，自动创建flags/子目录
        elif zip_name == "allimages.zip":
            target = BASE_DIR  # 解压到fotw/，自动创建images/子目录
        else:
            target = BASE_DIR  # 解压到fotw/，自动创建misc/子目录

        # 检查是否已经解压
        if zip_name == "allflags.zip" and FLAGS_DIR.exists() and any(FLAGS_DIR.iterdir()):
            print(f"  [跳过] {zip_name} 已解压")
        elif zip_name == "allimages.zip" and IMAGES_DIR.exists() and any(IMAGES_DIR.iterdir()):
            print(f"  [跳过] {zip_name} 已解压")
        elif zip_name == "allmisc.zip" and MISC_DIR.exists() and any(MISC_DIR.iterdir()):
            print(f"  [跳过] {zip_name} 已解压")
        else:
            extract_zip(zip_path, target, zip_name)

    # 步骤3: GIF转PNG
    if IMAGES_DIR.exists() and any(IMAGES_DIR.rglob("*.gif")):
        convert_gif_to_png()
    else:
        print("\n[跳过] 未找到图片目录，跳过GIF转换")

    # 步骤4: 解析HTML生成JSON索引
    if FLAGS_DIR.exists() and any(FLAGS_DIR.glob("*.html")):
        countries = parse_index_pages()
        generate_json_index(countries)
    else:
        print("\n[跳过] 未找到页面目录，跳过解析")
        countries = []

    print("\n" + "=" * 60)
    print("处理完成！")
    print(f"  数据目录: {DATA_DIR}")
    print(f"  图片目录: {IMAGES_DIR} (GIF) / {IMAGES_PNG_DIR} (PNG)")
    print("=" * 60)


if __name__ == "__main__":
    main()
