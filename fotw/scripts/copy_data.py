import shutil
import json
from pathlib import Path

src = Path(r'd:\Projects\SvgSite\fotw\data')
dst = Path(r'd:\Projects\SvgSite\fotw\web\data')
commons_src = Path(r'd:\Projects\SvgSite\fotw\commons\data')
commons_svgs_src = Path(r'd:\Projects\SvgSite\fotw\commons\svgs')
commons_svgs_dst = Path(r'd:\Projects\SvgSite\fotw\web\commons-svgs')

dst.mkdir(parents=True, exist_ok=True)
commons_svgs_dst.mkdir(parents=True, exist_ok=True)

details = {}
details_path = src / 'flag_details.json'
if details_path.exists():
    with open(details_path, 'r', encoding='utf-8') as f:
        details = json.load(f)

countries_path = src / 'countries.json'
if countries_path.exists():
    with open(countries_path, 'r', encoding='utf-8') as f:
        countries_data = json.load(f)
    for c in countries_data.get('countries', []):
        code = c.get('code', '')
        if code in details:
            kw = details[code].get('keywords', [])
            intro = details[code].get('intro', '')
            main_image = details[code].get('main_image', '')
            if kw:
                c['keywords'] = kw
            if intro:
                c['intro'] = intro[:200]
            if main_image:
                c['main_image'] = main_image
    target = dst / 'countries.json'
    with open(target, 'w', encoding='utf-8') as f:
        json.dump(countries_data, f, ensure_ascii=False)
    print(f'处理并复制 countries.json')

for f in src.glob('*.json'):
    if f.name == 'countries.json':
        continue
    target = dst / f.name
    print(f'复制 {f.name}')
    shutil.copyfile(str(f), str(target))

# Copy Commons SVG data
if commons_src.exists():
    for f in commons_src.glob('*.json'):
        target = dst / f.name
        if f.name == 'commons_svgs.json':
            # Rewrite local_file paths for web (relative to root HTML)
            with open(f, 'r', encoding='utf-8') as fp:
                data = json.load(fp)
            for item in data.get('svgs', []):
                lf = item.get('local_file', '')
                if lf.startswith('svgs/'):
                    item['local_file'] = 'web/commons-svgs/' + lf[5:]
            with open(target, 'w', encoding='utf-8') as fp:
                json.dump(data, fp, ensure_ascii=False)
            print(f'处理并复制 {f.name} (commons)')
        else:
            shutil.copyfile(str(f), str(target))
            print(f'复制 {f.name} (commons)')

# Copy local SVG files to web/commons-svgs (if any)
if commons_svgs_src.exists():
    import os
    copied = 0
    for f in commons_svgs_src.glob('*.svg'):
        target = commons_svgs_dst / f.name
        if not target.exists() or target.stat().st_size != f.stat().st_size:
            shutil.copyfile(str(f), str(target))
            copied += 1
    if copied > 0:
        print(f'复制 {copied} 个本地SVG缓存')
    else:
        print(f'SVG缓存已是最新')

print('完成')
