import os, json
from pathlib import Path
f = Path('flags')
exi = set(p.stem for p in f.glob('*.html'))
print('flags/*.html count:', len(exi))
d = json.load(open('data/flag_details.json',encoding='utf-8'))
allcodes=set()
for code,det in d.items():
    for b in det.get('content_blocks',[]) or []:
        if b.get('type')=='sub_pages':
            for l in b.get('links',[]) or []:
                if l.get('code'): allcodes.add(l['code'])
miss = sorted([c for c in allcodes if c not in exi])
print('linked codes:', len(allcodes))
print('still missing codes:', len(miss))
print('first 40 missing:', miss[:40])
