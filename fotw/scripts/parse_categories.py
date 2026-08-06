#!/usr/bin/env python3
"""解析FOTW关键词/主题分类和地图索引页面，生成分类数据"""
from pathlib import Path
from html.parser import HTMLParser
import json
import re
import urllib.parse

BASE_DIR = Path(__file__).resolve().parent.parent
FLAGS_DIR = BASE_DIR / "flags"
DATA_DIR = BASE_DIR / "data"

class LinkExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.in_a = False
        self.current_href = None
        self.current_text = ""
        self.in_title = False
        self.title = ""
        self.skip_tags = {'script', 'style'}
        self.skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.skip_tags:
            self.skip_depth += 1
            return
        if self.skip_depth > 0:
            return
        attrs_dict = dict(attrs)
        if tag == 'a' and 'href' in attrs_dict:
            href = attrs_dict['href']
            # Skip anchors, external links, non-html links
            if href and not href.startswith('#') and not href.startswith('http') and not href.startswith('mailto'):
                if href.endswith('.html') or href.endswith('.htm'):
                    self.in_a = True
                    self.current_href = href
                    self.current_text = ""
        if tag == 'title':
            self.in_title = True

    def handle_endtag(self, tag):
        if tag in self.skip_tags and self.skip_depth > 0:
            self.skip_depth -= 1
            return
        if self.skip_depth > 0:
            return
        if tag == 'a' and self.in_a:
            text = self.current_text.strip()
            if text and self.current_href:
                self.links.append((self.current_href, text))
            self.in_a = False
            self.current_href = None
        if tag == 'title':
            self.in_title = False

    def handle_data(self, data):
        if self.skip_depth > 0:
            return
        if self.in_a:
            self.current_text += data
        if self.in_title:
            self.title += data

def code_from_href(href):
    """从href提取旗帜代码，如 cn.html -> cn"""
    name = href.split('/')[-1]
    # Remove query string
    name = name.split('?')[0]
    # Remove .html/.htm extension
    for ext in ['.html', '.htm']:
        if name.lower().endswith(ext):
            name = name[:-len(ext)]
    return name

def parse_keyword_index():
    """解析keyword.html和keywordA-Z.html，获取主题分类列表"""
    categories = []
    
    # First parse the main keyword page
    main_kw = FLAGS_DIR / "keyword.html"
    if not main_kw.exists():
        print("keyword.html not found!")
        return categories

    with open(main_kw, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    parser = LinkExtractor()
    parser.feed(content)
    
    # Extract links that look like keyword category pages (kw*.html)
    kw_links = []
    for href, text in parser.links:
        code = code_from_href(href)
        # FOTW keyword pages often start with kw or are the letter keyword pages
        if code.startswith('kw') or (len(code) <= 15 and not code.startswith('(')):
            kw_links.append((href, text, code))
    
    # Also parse each letter's keyword page
    for letter in 'abcdefghijklmnopqrstuvwxyz':
        kw_file = FLAGS_DIR / f"keyword{letter}.html"
        if kw_file.exists():
            try:
                with open(kw_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                p = LinkExtractor()
                p.feed(content)
                for href, text in p.links:
                    code = code_from_href(href)
                    if code and not code.startswith('#') and not code.startswith('http'):
                        if len(text) < 100 and len(code) < 30:
                            # Filter for sub-category links
                            if '_kw' in href or 'kw' in code.lower()[:3] or '_sub' in href:
                                kw_links.append((href, text, code))
            except Exception as e:
                pass

    # Deduplicate by code
    seen = set()
    for href, text, code in kw_links:
        if code not in seen and text and len(text) < 80:
            seen.add(code)
            categories.append({
                'code': code,
                'title': text,
                'href': href
            })
    
    return categories

def parse_map_index():
    """解析地图索引页面，获取按地区分类的国家列表"""
    regions = []
    
    # FOTW has continent/region pages
    region_files = []
    
    # Look for geographic/map index pages
    for f in FLAGS_DIR.glob("*.html"):
        name = f.name.lower()
        if any(k in name for k in ['geo', 'map', 'continent', 'region']) and not any(k in name for k in ['_kw', '_sub', '.html~']):
            # Exclude country-specific pages (e.g., dk-map.html)
            # Look for general index pages
            if name in ['geo.html', 'map.html', 'index.html']:
                region_files.append(f)
    
    # Parse the main flags directory index
    main_index = FLAGS_DIR / "index.html"
    
    # Build continent-based grouping from countries data
    # We'll create a reasonable continent mapping since we have country codes
    continent_map = {
        # Africa
        'a': ['ao', 'bj', 'bw', 'bf', 'bi', 'cv', 'cm', 'cf', 'td', 'km', 'cg', 'cd', 'ci', 'dj', 'eg', 'gq', 'er', 'sz', 'et', 'ga', 'gm', 'gh', 'gn', 'gw', 'ke', 'ls', 'lr', 'ly', 'mg', 'mw', 'ml', 'mr', 'mu', 'ma', 'mz', 'na', 'ne', 'ng', 'rw', 'st', 'sn', 'sc', 'sl', 'so', 'za', 'ss', 'sd', 'tz', 'tg', 'tn', 'ug', 'zm', 'zw'],
        'b': [],
        'c': ['cv', 'cm', 'cf', 'td', 'km', 'cg', 'cd', 'ci', 'td'],
        'd': ['dj'],
        'e': ['eg', 'er', 'et'],
        'g': ['ga', 'gm', 'gh', 'gn', 'gw', 'gq'],
        'k': ['ke', 'km'],
        'l': ['lr', 'ls', 'ly'],
        'm': ['mg', 'mw', 'ml', 'mr', 'mu', 'ma', 'mz'],
        'n': ['na', 'ne', 'ng'],
        'r': ['rw'],
        's': ['st', 'sn', 'sc', 'sl', 'so', 'za', 'ss', 'sd', 'sz'],
        't': ['tz', 'tg', 'tn', 'td'],
        'u': ['ug'],
        'z': ['zm', 'zw'],
        # Americas
        # Asia
        # Europe
        # Oceania
    }
    
    # Instead of complex parsing, let's create a practical geographic grouping
    # based on standard continent classifications
    continents = {
        'africa': {'name': '非洲', 'codes': []},
        'americas': {'name': '美洲', 'codes': []},
        'asia': {'name': '亚洲', 'codes': []},
        'europe': {'name': '欧洲', 'codes': []},
        'oceania': {'name': '大洋洲', 'codes': []},
        'international': {'name': '国际组织', 'codes': []},
        'historical': {'name': '历史旗帜', 'codes': []},
    }
    
    # ISO 3166-1 alpha-2 country code to continent mapping for known codes
    code_continent = {
        # Africa
        'ao': 'africa', 'bj': 'africa', 'bw': 'africa', 'bf': 'africa', 'bi': 'africa',
        'cv': 'africa', 'cm': 'africa', 'cf': 'africa', 'td': 'africa', 'km': 'africa',
        'cg': 'africa', 'cd': 'africa', 'ci': 'africa', 'dj': 'africa', 'eg': 'africa',
        'gq': 'africa', 'er': 'africa', 'sz': 'africa', 'et': 'africa', 'ga': 'africa',
        'gm': 'africa', 'gh': 'africa', 'gn': 'africa', 'gw': 'africa', 'ke': 'africa',
        'ls': 'africa', 'lr': 'africa', 'ly': 'africa', 'mg': 'africa', 'mw': 'africa',
        'ml': 'africa', 'mr': 'africa', 'mu': 'africa', 'ma': 'africa', 'mz': 'africa',
        'na': 'africa', 'ne': 'africa', 'ng': 'africa', 'rw': 'africa', 'st': 'africa',
        'sn': 'africa', 'sc': 'africa', 'sl': 'africa', 'so': 'africa', 'za': 'africa',
        'ss': 'africa', 'sd': 'africa', 'tz': 'africa', 'tg': 'africa', 'tn': 'africa',
        'ug': 'africa', 'zm': 'africa', 'zw': 'africa', 'eh': 'africa', 'so': 'africa',
        'dz': 'africa',
        # Americas
        'ai': 'americas', 'ag': 'americas', 'ar': 'americas', 'aw': 'americas', 'bs': 'americas',
        'bb': 'americas', 'bz': 'americas', 'bm': 'americas', 'bo': 'americas', 'bq': 'americas',
        'br': 'americas', 'vg': 'americas', 'ca': 'americas', 'ky': 'americas', 'cl': 'americas',
        'co': 'americas', 'cr': 'americas', 'cu': 'americas', 'cw': 'americas', 'dm': 'americas',
        'do': 'americas', 'ec': 'americas', 'sv': 'americas', 'fk': 'americas', 'gf': 'americas',
        'gl': 'americas', 'gd': 'americas', 'gp': 'americas', 'gt': 'americas', 'gy': 'americas',
        'ht': 'americas', 'hn': 'americas', 'jm': 'americas', 'mq': 'americas', 'mx': 'americas',
        'ms': 'americas', 'ni': 'americas', 'pa': 'americas', 'py': 'americas', 'pe': 'americas',
        'pr': 'americas', 'bl': 'americas', 'kn': 'americas', 'lc': 'americas', 'mf': 'americas',
        'pm': 'americas', 'vc': 'americas', 'sx': 'americas', 'sr': 'americas', 'tt': 'americas',
        'tc': 'americas', 'us': 'americas', 'uy': 'americas', 've': 'americas', 'vi': 'americas',
        'an': 'historical',
        # Asia
        'af': 'asia', 'am': 'asia', 'az': 'asia', 'bh': 'asia', 'bd': 'asia', 'bt': 'asia',
        'bn': 'asia', 'kh': 'asia', 'cn': 'asia', 'cx': 'asia', 'cc': 'asia', 'cy': 'asia',
        'ge': 'asia', 'in': 'asia', 'id': 'asia', 'ir': 'asia', 'iq': 'asia', 'il': 'asia',
        'jp': 'asia', 'jo': 'asia', 'kz': 'asia', 'kw': 'asia', 'kg': 'asia', 'la': 'asia',
        'lb': 'asia', 'my': 'asia', 'mv': 'asia', 'mn': 'asia', 'mm': 'asia', 'np': 'asia',
        'kp': 'asia', 'om': 'asia', 'pk': 'asia', 'ps': 'asia', 'ph': 'asia', 'qa': 'asia',
        'sa': 'asia', 'sg': 'asia', 'kr': 'asia', 'lk': 'asia', 'sy': 'asia', 'tw': 'asia',
        'tj': 'asia', 'th': 'asia', 'tl': 'asia', 'tr': 'asia', 'tm': 'asia', 'ae': 'asia',
        'uz': 'asia', 'vn': 'asia', 'ye': 'asia', 'hk': 'asia', 'mo': 'asia',
        # Europe
        'al': 'europe', 'ad': 'europe', 'at': 'europe', 'by': 'europe', 'be': 'europe',
        'ba': 'europe', 'bg': 'europe', 'hr': 'europe', 'cz': 'europe', 'dk': 'europe',
        'ee': 'europe', 'fo': 'europe', 'fi': 'europe', 'fr': 'europe', 'de': 'europe',
        'gi': 'europe', 'gr': 'europe', 'gg': 'europe', 'hu': 'europe', 'is': 'europe',
        'ie': 'europe', 'im': 'europe', 'it': 'europe', 'je': 'europe', 'lv': 'europe',
        'li': 'europe', 'lt': 'europe', 'lu': 'europe', 'mk': 'europe', 'mt': 'europe',
        'md': 'europe', 'mc': 'europe', 'me': 'europe', 'nl': 'europe', 'no': 'europe',
        'pl': 'europe', 'pt': 'europe', 'ro': 'europe', 'ru': 'europe', 'sm': 'europe',
        'rs': 'europe', 'sk': 'europe', 'si': 'europe', 'es': 'europe', 'se': 'europe',
        'ch': 'europe', 'ua': 'europe', 'gb': 'europe', 'uk': 'europe', 'va': 'europe',
        'ax': 'europe', 'sj': 'europe', 'xk': 'europe', 'cs': 'historical', 'dd': 'historical',
        'su': 'historical', 'yu': 'historical', 'ah': 'historical',
        # Oceania
        'as': 'oceania', 'au': 'oceania', 'ck': 'oceania', 'fj': 'oceania', 'pf': 'oceania',
        'gu': 'oceania', 'ki': 'oceania', 'mh': 'oceania', 'fm': 'oceania', 'nr': 'oceania',
        'nc': 'oceania', 'nz': 'oceania', 'nu': 'oceania', 'nf': 'oceania', 'mp': 'oceania',
        'pw': 'oceania', 'pg': 'oceania', 'pn': 'oceania', 'ws': 'oceania', 'sb': 'oceania',
        'tk': 'oceania', 'to': 'oceania', 'tv': 'oceania', 'vu': 'oceania', 'wf': 'oceania',
        'aq': 'oceania', 'bv': 'oceania', 'hm': 'oceania', 'gs': 'oceania', 'tf': 'oceania',
        'um': 'oceania',
        # International organizations
        'un': 'international', 'eu': 'international', 'nato': 'international', 'au_o': 'international',
        'arabis': 'international', 'cis': 'international', 'oas': 'international', 'au_o': 'international',
        'acp': 'international', 'afdb': 'international', 'ag': 'americas', 'apec': 'international',
        'asean': 'international', 'caricom': 'international', 'cea': 'international', 'c_e': 'international',
        'cefta': 'international', 'comesa': 'international', 'ecowas': 'international', 'efta': 'international',
        'eu_n': 'international', 'gcc': 'international', 'iac': 'international', 'igu': 'international',
        'mercosur': 'international', 'oau': 'international', 'oic': 'international', 'pif': 'international',
        'sadc': 'international', 'saarc': 'international', 'una': 'international', 'unpo': 'international',
        'wto': 'international', 'who': 'international', 'ilo': 'international', 'imf': 'international',
        'iso': 'international', 'ioc': 'international', 'fao': 'international', 'unesco': 'international',
        'icrc': 'international', 'ifrc': 'international', 'interpol': 'international', 'iom': 'international',
        'wipo': 'international', 'wmo': 'international', 'wfp': 'international', 'unicef': 'international',
        'unhcr': 'international', 'undp': 'international', 'unep': 'international',
    }
    
    # Load countries data and assign continents
    countries_file = DATA_DIR / "countries.json"
    if countries_file.exists():
        with open(countries_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        for c in data.get('countries', []):
            code = c.get('code', '').lower()
            continent = code_continent.get(code)
            if continent and continent in continents:
                continents[continent]['codes'].append(code)
            else:
                # Try to guess based on code patterns
                if len(code) == 2:
                    # Unknown 2-letter codes - put in a misc category
                    continents.setdefault('other', {'name': '其他', 'codes': []})
                    continents['other']['codes'].append(code)
                elif any(c.isdigit() for c in code) or len(code) > 3:
                    continents['historical']['codes'].append(code)
                else:
                    continents.setdefault('other', {'name': '其他', 'codes': []})
                    continents['other']['codes'].append(code)
    
    # Convert to list format
    for key, val in continents.items():
        if val['codes']:
            regions.append({
                'code': key,
                'name': val['name'],
                'count': len(val['codes']),
                'codes': sorted(val['codes'])
            })
    
    return regions

def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    print("解析关键词/主题分类...")
    categories = parse_keyword_index()
    print(f"  找到 {len(categories)} 个主题分类")
    
    print("构建地图/地区索引...")
    regions = parse_map_index()
    print(f"  找到 {len(regions)} 个地区分类")
    
    # Save
    output = {
        'categories': categories,
        'regions': regions
    }
    
    out_file = DATA_DIR / "categories.json"
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"分类数据已保存到 {out_file}")
    
    # Print region stats
    for r in regions:
        print(f"  {r['name']}: {r['count']} 个")

if __name__ == "__main__":
    main()
