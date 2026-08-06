import json
from collections import Counter
from pathlib import Path

DATA_DIR = Path('d:/Projects/SvgSite/fotw/data')
with open(DATA_DIR / 'countries.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

countries = data['countries']
print(f"总条目: {len(countries)}")
tag_counter = Counter()
for c in countries:
    for t in c.get('tags', []):
        tag_counter[t] += 1

print("\nTags分布:")
for tag, cnt in tag_counter.most_common(30):
    print(f"  {tag}: {cnt}")

# 检查军旗、政党、体育、公司的数量
for tag in ['military', 'political', 'sports', 'corporate', 'naval', 'national', 'government', 'historical', 'regional']:
    items = [c for c in countries if tag in c.get('tags', [])]
    print(f"\n'{tag}' 示例（前5个）:")
    for it in items[:5]:
        print(f"  {it['code']}: {it['title'][:60]}  tags={it.get('tags')}")
