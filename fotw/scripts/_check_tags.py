import json, re
from collections import Counter
d = json.load(open(r'd:\Projects\SvgSite\fotw\data\countries.json', 'r', encoding='utf-8'))
other = [c for c in d['countries'] if 'other' in c.get('tags', [])]

# Find codes with various patterns
patterns = Counter()
examples = {}
for c in other:
    code = c['code'].lower()
    if code.endswith('-'):
        patterns['trailing_dash'] += 1
        examples.setdefault('trailing_dash', []).append(code)
    elif '_index' in code:
        patterns['_index'] += 1
        examples.setdefault('_index', []).append(code)
    elif code.startswith('cou'):
        patterns['cou_*'] += 1
        examples.setdefault('cou_*', []).append(code)
    elif code.startswith('xa') or code.startswith('xg') or code.startswith('xh'):
        patterns['xa/xg/xh (indigenous)'] += 1
        examples.setdefault('xa/xg/xh', []).append(code)
    elif re.match(r'^[a-z]{3,}$', code):
        patterns['3+ letters pure'] += 1
        examples.setdefault('3+ letters pure', []).append(code)
    elif '~' in code or '^' in code or '}' in code or '@' in code or '$' in code or '!' in code:
        patterns['has_special_char_but_other'] += 1
        examples.setdefault('has_special_char', []).append(code)
    elif re.search(r'-\d+', code):
        patterns['has_dash_number'] += 1
        examples.setdefault('has_dash_number', []).append(code)
    else:
        patterns['unclassified'] += 1
        examples.setdefault('unclassified', []).append(code)

print('Pattern breakdown of "other" ({} total):'.format(len(other)))
for k, v in patterns.most_common():
    print(f'  {k}: {v}')
    for code in examples[k][:5]:
        c = next(x for x in other if x['code'].lower() == code)
        print(f'    - {code}: {c["title"]}')
