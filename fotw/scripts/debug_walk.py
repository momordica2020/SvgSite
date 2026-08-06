import sys, importlib
sys.path.insert(0, 'd:/Projects/SvgSite/fotw/scripts')

from bs4 import BeautifulSoup, NavigableString, Tag
from pathlib import Path
import re
from html import unescape

html_path = Path(r'd:\Projects\SvgSite\fotw\flags\ax.html')
with open(html_path, 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()

cut_idx = content.find('<!--CUT ABOVE-->')
main_html = content[cut_idx + len('<!--CUT ABOVE-->'):] if cut_idx >= 0 else content
main_soup = BeautifulSoup(main_html, 'html.parser')

for bad in main_soup.find_all(['script', 'style', 'noscript']):
    bad.decompose()

elements_to_process = []

def walk(el, in_block=False, depth=0):
    for child in el.children:
        if isinstance(child, NavigableString):
            continue
        if not isinstance(child, Tag):
            continue
        cname = child.name.lower()
        if cname in ('h1', 'h2', 'h3', 'h4', 'ul', 'ol', 'blockquote', 'pre', 'table', 'hr'):
            elements_to_process.append(child)
            walk(child, in_block=True, depth=depth+1)
        elif cname == 'p' and not in_block:
            has_block_child = False
            for sub in child.children:
                if isinstance(sub, Tag):
                    sname = sub.name.lower()
                    if sname in ('h1','h2','h3','h4','ul','ol','blockquote','pre','table','p','div'):
                        has_block_child = True
                        break
            if has_block_child:
                walk(child, in_block=False, depth=depth+1)
            else:
                elements_to_process.append(child)
        elif cname == 'div':
            walk(child, in_block=in_block, depth=depth+1)
        elif cname in ('center', 'td', 'th', 'tr', 'body', 'html', 'font'):
            walk(child, in_block=in_block, depth=depth+1)

walk(main_soup)
elements_to_process.sort(key=lambda e: e.sourceline or 0)

print(f"Total elements collected: {len(elements_to_process)}")
for i, el in enumerate(elements_to_process):
    cname = el.name.lower()
    line = el.sourceline or 0
    txt = el.get_text().strip()[:80].replace('\n',' ')
    if cname in ('h1','h2','h3','h4','p'):
        print(f"  [{i}] L{line} <{cname}>: {txt}")
    elif cname in ('ul','ol'):
        items = el.find_all('li', recursive=False)
        print(f"  [{i}] L{line} <{cname}>: {len(items)} items")
    elif cname == 'hr':
        print(f"  [{i}] L{line} <hr>")
    else:
        print(f"  [{i}] L{line} <{cname}>: {txt[:60]}")
