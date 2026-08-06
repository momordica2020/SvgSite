from bs4 import BeautifulSoup
from pathlib import Path

html_path = Path(r'd:\Projects\SvgSite\fotw\flags\cn.html')
with open(html_path, 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()

cut_idx = content.find('<!--CUT ABOVE-->')
if cut_idx >= 0:
    main_html = content[cut_idx + len('<!--CUT ABOVE-->'):]
else:
    soup = BeautifulSoup(content, 'html.parser')
    body_tag = soup.find('body')
    main_html = str(body_tag) if body_tag else content

main_soup = BeautifulSoup(main_html, 'html.parser')

relevant_tags = ['h1', 'h2', 'h3', 'h4', 'p', 'ul', 'ol', 'blockquote', 'pre', 'table']

print("所有找到的h2标签:")
for h in main_soup.find_all('h2'):
    print(f"  sourceline={h.sourceline}, text={h.get_text()[:50]}, parent={h.parent.name if h.parent else 'None'}")
    parent_relevant = h.find_parent(relevant_tags)
    print(f"    最近的相关父级: {parent_relevant.name if parent_relevant else 'None'}")

print("\n顶层元素（相关标签）:")
for el in main_soup.find_all(relevant_tags):
    nearest = el.find_parent(relevant_tags)
    if nearest is None:
        print(f"  {el.name} line={el.sourceline}: {el.get_text()[:60]}")
