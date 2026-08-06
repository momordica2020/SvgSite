import sys, importlib
sys.path.insert(0, 'd:/Projects/SvgSite/fotw/scripts')
import parse_data_v4
importlib.reload(parse_data_v4)
from parse_data_v4 import parse_detail, VALID_CODES, parse_countries

countries = parse_countries()
VALID_CODES.clear()
VALID_CODES.update({c["code"] for c in countries})

for code in ['ax', 'gg', 'jp', 'us', 'cn', 'fr']:
    d = parse_detail(code)
    if d:
        types = {}
        for b in d.get('content_blocks',[]):
            t = b['type']
            types[t] = types.get(t,0)+1
        print(f"{code}: imgs={len(d.get('all_flags',[]))} blocks={len(d.get('content_blocks',[]))} types={types} toc={len(d.get('toc',[]))}")
    else:
        print(f"{code}: FAILED")
