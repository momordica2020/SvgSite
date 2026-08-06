import json

data = json.load(open(r'd:\Projects\SvgSite\fotw\data\flag_details.json', 'r', encoding='utf-8'))
cn = data['cn']

print('标题:', cn['title'])
print('副标题:', cn['subtitle'])
print('比例:', cn['flag_ratio'])
print('编辑:', cn['editor'])
print('简介:', cn['intro'][:300])
print()
print('章节:')
for s in cn['sections']:
    n_p = len([c for c in s['content'] if c['type'] == 'paragraphs'])
    n_q = len([c for c in s['content'] if c['type'] == 'quotes'])
    n_l = len([c for c in s['content'] if c['type'] == 'lists'])
    n_i = len([c for c in s['content'] if c['type'] == 'images'])
    print(f"  - {s['title']}(h{s.get('level',2)}): {n_p}段, {n_q}引用, {n_l}列表, {n_i}图")

print()
print('段落数量检查:')
for s in cn['sections']:
    for c in s['content']:
        if c['type'] == 'paragraphs':
            print(f"  {s['title']}: {len(c['content'])}段")
            for i, p in enumerate(c['content'][:2]):
                print(f"    段{i+1}长度: {len(p)}")
