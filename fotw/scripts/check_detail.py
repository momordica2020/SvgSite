import json

with open('fotw/data/flag_details.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

cn = data.get('cn', {})
print('Keys:', list(cn.keys()))
print('Title:', cn.get('title'))
print('Subtitle:', cn.get('subtitle'))
print('Ratio:', cn.get('flag_ratio'))
print('Main image:', cn.get('main_image'))
print('Images count:', len(cn.get('images', [])))
for img in cn.get('images', []):
    print(f'  img: {img}')
print('Sections count:', len(cn.get('sections', [])))
for s in cn.get('sections', []):
    print(f'  Section: {s["title"]}')
    for c in s.get('content', []):
        print(f'    [{c["type"]}] {len(c["content"])} items')
        if c['type'] == 'paragraphs':
            for p in c['content'][:2]:
                preview = p[:120] + '...' if len(p) > 120 else p
                print(f'      > {preview}')
print('Links count:', len(cn.get('links', [])))
for l in cn.get('links', [])[:10]:
    print(f'  link: {l}')
print('See also count:', len(cn.get('see_also', [])))
for s in cn.get('see_also', [])[:5]:
    print(f'  seealso: {s}')
print('Intro:', cn.get('intro', '')[:300])
print('Keywords:', cn.get('keywords', []))
