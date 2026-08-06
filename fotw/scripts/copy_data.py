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

# 读取详情数据用于补充 countries（仅读取分片索引，避免加载188MB大文件）
details_index = {}
index_path = src / 'flag_details_index.json'
if index_path.exists():
    with open(index_path, 'r', encoding='utf-8') as f:
        details_index = json.load(f)

# 收集所有详情字段（仅从分片中读取 main_image/keywords/intro 用于补充 countries）
details_cache = {}
if details_index:
    # 按 code 首字母批量从对应分片读取
    from collections import defaultdict
    code_by_shard = defaultdict(list)
    for code, shard in details_index.items():
        code_by_shard[shard].append(code)
    for shard_name, codes in code_by_shard.items():
        shard_path = src / shard_name
        if not shard_path.exists():
            continue
        with open(shard_path, 'r', encoding='utf-8') as f:
            shard_data = json.load(f)
        for code in codes:
            if code in shard_data:
                details_cache[code] = shard_data[code]

# 处理并复制 countries.json
countries_path = src / 'countries.json'
if countries_path.exists():
    with open(countries_path, 'r', encoding='utf-8') as f:
        countries_data = json.load(f)
    for c in countries_data.get('countries', []):
        code = c.get('code', '')
        if code in details_cache:
            kw = details_cache[code].get('keywords', [])
            intro = details_cache[code].get('intro', '')
            main_image = details_cache[code].get('main_image', '')
            if kw:
                c['keywords'] = kw
            if intro:
                c['intro'] = intro[:200]
            if main_image:
                c['main_image'] = main_image
    target = dst / 'countries.json'
    with open(target, 'w', encoding='utf-8') as f:
        json.dump(countries_data, f, ensure_ascii=False, separators=(',', ':'))
    print(f'处理并复制 countries.json ({target.stat().st_size/1048576:.2f} MB)')

# 复制分片文件和索引（不再复制原始大文件 flag_details.json）
for f in src.glob('flag_details_*.json'):
    target = dst / f.name
    shutil.copyfile(str(f), str(target))
    print(f'复制 {f.name} ({f.stat().st_size/1048576:.2f} MB)')

# 复制其他小 JSON（categories.json 等）
for f in src.glob('*.json'):
    name = f.name
    if name == 'countries.json':
        continue
    if name.startswith('flag_details'):
        continue  # 已通过上面的分片逻辑处理
    target = dst / name
    print(f'复制 {name}')
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
