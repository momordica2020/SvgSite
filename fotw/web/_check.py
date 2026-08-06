import json
d = json.load(open('data/countries.json', encoding='utf-8'))
countries = d['countries']
total = len(countries)
with_img = sum(1 for c in countries if c.get('main_image'))
without_img = total - with_img
print(f'Total: {total}')
print(f'With main_image: {with_img}')
print(f'Without main_image: {without_img}')

no_img = [c for c in countries if not c.get('main_image')]
print(f'\nSample of entries without main_image (first 20):')
for c in no_img[:20]:
    print(f'  {c["code"]}: {c["title"]} is_main={c.get("is_main")}')

# Check ah specifically
for c in countries:
    if c['code'] == 'ah':
        print(f'\nah entry: {c}')
