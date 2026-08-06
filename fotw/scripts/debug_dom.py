#!/usr/bin/env python3
"""调试DOM结构"""
import sys
import re
from pathlib import Path
from html import unescape
from bs4 import BeautifulSoup, NavigableString, Tag

FLAGS_DIR = Path(__file__).parent.parent / "flags"

def debug_dom(code):
    html_path = FLAGS_DIR / f"{code}.html"
    with open(html_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    cut_idx = content.find('<!--CUT ABOVE-->')
    if cut_idx >= 0:
        main_html = content[cut_idx + len('<!--CUT ABOVE-->'):]
    else:
        main_html = content
    
    soup = BeautifulSoup(main_html, 'html.parser')
    body = soup.find('body') or soup
    
    print(f"=== {code} body direct children ===")
    children = list(body.children)
    print(f"Total children: {len(children)}")
    for i, child in enumerate(children):
        if isinstance(child, NavigableString):
            text = child.strip()
            if text:
                print(f"{i}: TEXT: {text[:80]}")
            continue
        if isinstance(child, Tag):
            tag = child.name
            text = child.get_text().strip()[:80]
            text = text.replace('\n', ' ')
            print(f"{i}: <{tag}>: {text}")
            if tag in ('h1', 'h2', 'h3', 'h4'):
                print(f"   *** HEADING <{tag}>: '{child.get_text().strip()}'")

if __name__ == "__main__":
    debug_dom('cn')
