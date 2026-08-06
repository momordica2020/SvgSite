#!/usr/bin/env python3
"""快速测试解析器"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from parse_data_v2 import parse_detail, FLAGS_DIR

def test_page(code):
    print(f"\n{'='*60}")
    print(f"测试页面: {code}")
    print(f"{'='*60}")
    
    d = parse_detail(code)
    if not d:
        print("解析失败!")
        return
    
    print(f"标题: {d.get('title', '')}")
    print(f"副标题: {d.get('subtitle', '')[:100]}")
    print(f"比例: {d.get('flag_ratio', '')}")
    print(f"主图: {d.get('main_image', '')}")
    print(f"图片数: {len(d.get('images', []))}")
    print(f"关键词: {d.get('keywords', [])}")
    print(f"更新时间: {d.get('last_modified', '')}")
    print(f"简介长度: {len(d.get('intro', ''))}")
    print(f"简介前300字: {d.get('intro', '')[:300]}")
    print(f"\n章节数: {len(d.get('sections', []))}")
    
    for i, s in enumerate(d.get('sections', [])):
        n_paras = sum(len(c['content']) for c in s.get('content', []) if c['type'] == 'paragraphs')
        n_imgs = sum(len(c['content']) for c in s.get('content', []) if c['type'] == 'images')
        n_quotes = sum(len(c['content']) for c in s.get('content', []) if c['type'] == 'quotes')
        n_lists = sum(len(c['content']) for c in s.get('content', []) if c['type'] == 'lists')
        level = s.get('level', 2)
        print(f"  [{i}][h{level}] {s['title']}: {n_paras}段, {n_imgs}图, {n_quotes}引用, {n_lists}列表")
    
    print(f"\n相关链接(See also): {len(d.get('see_also', []))}")
    for l in d.get('see_also', [])[:8]:
        print(f"  - {l['code']}: {l['title'][:50]}")
    
    print(f"\n内容链接: {len(d.get('links', []))}")
    for l in d.get('links', [])[:8]:
        print(f"  - {l['code']}: {l['title'][:50]}")

if __name__ == "__main__":
    for code in ['cn', 'us', 'jp', 'fr']:
        if (FLAGS_DIR / f"{code}.html").exists():
            test_page(code)
