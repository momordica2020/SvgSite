import sys, importlib
sys.path.insert(0, 'd:/Projects/SvgSite/fotw/scripts')
import parse_data_v4
importlib.reload(parse_data_v4)
from parse_data_v4 import parse_detail, VALID_CODES, parse_countries

# 临时加入ah作为合法code
VALID_CODES.add('ah')
d = parse_detail('ah')
if d:
    print(f"title: {d.get('title')}")
    print(f"main_image: {d.get('main_image')}")
    print(f"all_flags count: {len(d.get('all_flags',[]))}")
    for i, img in enumerate(d.get('all_flags', [])[:10]):
        print(f"  [{i}] {img.get('src')} alt={img.get('alt','')[:40]}")
    print(f"toc: {[(t['text'],t.get('anchor','')) for t in d.get('toc',[])]}")
    types = {}
    for b in d.get('content_blocks',[]):
        t = b['type']
        types[t] = types.get(t,0)+1
    print(f"blocks: {types}")
    print(f"intro: {d.get('intro','')[:200]}")
else:
    print("FAILED to parse ah")
