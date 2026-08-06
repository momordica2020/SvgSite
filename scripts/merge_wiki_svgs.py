"""
将 fotw/web/commons-svgs（Wikimedia Commons 旗帜/国徽 SVG 图库）合并进主站。

功能：
  1. 将 166 个 SVG 复制到主站 svg/ 目录（按中文名生成文件名）；
  2. 翻译英文名为中文名；
  3. 按五类标签体系（style/color/element/region/usage）自动归类：
     - color:  解析 SVG 内的 fill/stroke 颜色；
     - region: 根据英文名/描述匹配地区/组织词表；
     - usage:  根据旗/徽类型匹配用途词表；
     - element/style: 根据名称与描述中的关键词匹配。
  4. 追加到 data/metadata.json。

用法：python scripts/merge_wiki_svgs.py
"""

import json
import os
import re
import shutil

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WIKI_SVG_DIR = os.path.join(PROJECT_ROOT, 'fotw', 'commons', 'svgs')
WIKI_DATA = os.path.join(PROJECT_ROOT, 'fotw', 'commons', 'data', 'commons_svgs.json')
SVG_DIR = os.path.join(PROJECT_ROOT, 'svg')
METADATA_FILE = os.path.join(PROJECT_ROOT, 'data', 'metadata.json')

from wiki_subjects_cn import translate_title, subject_cn

CATEGORY_ORDER = ['style', 'color', 'element', 'region', 'usage']


# 次级行政区/地区的主体 -> 所属国家（用于补充地区标签）
SUBJECT_PARENT = {
    'Maryland': '美国', 'Mississippi': '美国', 'Washington': '美国',
    'Maine': '美国', 'Georgia': '美国', 'California': '美国', 'Texas': '美国',
    'Nova Scotia': '加拿大', 'Quebec': '加拿大', 'Ontario': '加拿大',
    'Vienna': '奥地利', 'Carinthia': '奥地利', 'Tyrol': '奥地利',
    'Kachin State': '缅甸', 'Kayah State': '缅甸', 'Shan State': '缅甸',
    'Adjara': '格鲁吉亚', 'Abkhazia': '格鲁吉亚', 'South Ossetia': '格鲁吉亚',
    'Galicia': '西班牙', 'Catalonia': '西班牙', 'Basque Country': '西班牙',
    'La Guaira State': '委内瑞拉', 'Nueva Esparta State': '委内瑞拉',
    'Sarawak': '马来西亚', 'Labuan': '马来西亚', 'North Borneo': '马来西亚',
    'Alsace': '法国', 'Brittany': '法国', 'Normandy': '法国',
    'Lower Saxony': '德国', 'Baden-Württemberg': '德国', 'Saar': '德国',
    'Dagestan': '俄罗斯', 'Tatarstan': '俄罗斯', 'Chechnya': '俄罗斯',
    'Jersey': '英国', 'Guernsey': '英国', 'Wales': '英国', 'Scotland': '英国',
    'England': '英国', 'Northern Ireland': '英国',
    'Hong Kong': '中国', 'Macau': '中国', 'Tibet': '中国',
    'Fujian People\'s Government': '中国',
    'Kurdistan Regional Government': '伊拉克',
    'Herat Government': '阿富汗', 'Hejaz': '沙特阿拉伯',
    'Siam': '泰国', 'Persia': '伊朗', 'Ceylon': '斯里兰卡',
    'East Prussia': '德国', 'Hanover': '德国', 'Poznań': '波兰',
    'Congress Poland': '波兰', 'Duchy of Warsaw': '波兰',
    'Rhodesia and Nyasaland': '英国', 'British Guiana': '英国',
    'British Somaliland': '英国', 'British Straits Settlements': '英国',
    'Khanat of Crimea': '乌克兰', 'Novorussia': '乌克兰',
    'Gagauzia': '摩尔多瓦', 'Transnistria': '摩尔多瓦',
    'Kosova': '塞尔维亚', 'Macedonia': '北马其顿',
}


def norm(s):
    """归一化用于文件/条目匹配（JSON 中部分全角破折号被存成了“每”）"""
    return (s or '').replace('每', '–').strip()


# ============ 中文译名表（键为磁盘上的 SVG 文件名） ============
TRANSLATIONS = {
    'Air Force Ensign of Bangladesh.svg': '孟加拉国空军旗',
    'Air Force Ensign of Ghana.svg': '加纳空军旗',
    'Air Force Ensign of Ghana (1964–1966).svg': '加纳空军旗（1964–1966）',
    'Air Force Ensign of Malaysia.svg': '马来西亚空军旗',
    'Air Force Ensign of Pakistan.svg': '巴基斯坦空军旗',
    'Air Force Ensign of Sri Lanka.svg': '斯里兰卡空军旗',
    'American Revolutionary War regimental flag - the Monmouth Flag.svg': '美国独立战争孟茅斯团旗',
    'Armed forces flag day.svg': '印度武装部队节徽章',
    'Armed Forces of Pakistan Flag.svg': '巴基斯坦武装部队旗',
    'Austria Bundesadler.svg': '奥地利联邦之鹰徽章',
    'Bandera de Gandia.svg': '甘迪亚市旗',
    'Banner of the Armed Forces of the Russian Federation (obverse).svg': '俄罗斯联邦武装力量旗帜（正面）',
    'Banner of the Armed Forces of the Russian Federation (reverse).svg': '俄罗斯联邦武装力量旗帜（背面）',
    'Belarusian national-anarchist flag.svg': '白俄罗斯民族无政府主义旗帜',
    'British Army car flag - military member of the Army Board.svg': '英国陆军委员会成员乘车旗',
    'Civil Air Ensign of Ghana (1964–1966).svg': '加纳民用航空旗（1964–1966）',
    'Civil Ensign of Australia (1903–1908).svg': '澳大利亚民用船旗（1903–1908）',
    'Civil Ensign of British Somaliland (1903–1950).svg': '英属索马里兰民用船旗（1903–1950）',
    'Civil Ensign of Ceylon (1875–1948).svg': '锡兰民用船旗（1875–1948）',
    'Civil Ensign of Ghana (1964–1966).svg': '加纳民用船旗（1964–1966）',
    'Civil Ensign of Luxembourg.svg': '卢森堡民用船旗',
    'Civil Ensign of Mauritius (1906–1968).svg': '毛里求斯民用船旗（1906–1968）',
    'Civil ensign of Singapore.svg': '新加坡民用船旗',
    'Civil Ensign of the British Straits Settlements (1904–1946).svg': '英国海峡殖民地民用船旗（1904–1946）',
    'Civil ensign of the United Kingdom.svg': '英国民用船旗',
    'Civil Flag and Civil Ensign of the Kingdom of Sardinia (1816-1848).svg': '撒丁王国民用旗与民用船旗（1816–1848）',
    'Civil flag of Serbia.svg': '塞尔维亚民用旗',
    'Coat of arms of Brazil.svg': '巴西国徽',
    'Coat of arms of Croatia.svg': '克罗地亚国徽',
    'Coat of arms of Eswatini.svg': '斯威士兰国徽',
    'Coat of Arms of Georgian Orthodox Church.svg': '格鲁吉亚正教会徽章',
    'Coat of arms of Guatemala.svg': '危地马拉国徽',
    'Coat of arms of Ireland.svg': '爱尔兰国徽',
    'Coat of arms of Mexico.svg': '墨西哥国徽',
    'Coat of arms of Nigeria.svg': '尼日利亚国徽',
    'Coat of Arms of Odesa.svg': '敖德萨市徽',
    'Coat of arms of Palestine.svg': '巴勒斯坦国徽',
    'Coat of arms of Panama.svg': '巴拿马国徽',
    'Coat of Arms of Ramla.svg': '拉姆拉市徽',
    'Coat of arms of Siam (greater).svg': '暹罗大纹章',
    'Coat of arms of Singapore.svg': '新加坡国徽',
    'Coat of arms of Slovakia.svg': '斯洛伐克国徽',
    'Coat of arms of Slovenia.svg': '斯洛文尼亚国徽',
    'Coat of arms of Uganda.svg': '乌干达国徽',
    'Commander-in-Chief Flag of the Republic of China (Beiyang Government).svg': '中华民国（北洋政府）大元帅旗',
    'Ensign of Austro-Hungarian civil fleet (1869-1918).svg': '奥匈帝国民用船队旗（1869–1918）',
    'Fictitious Austria-Hungary civil flag 1869-1918.svg': '虚构奥匈帝国民用旗（1869–1918）',
    'Flag of Adjara.svg': '阿扎尔自治共和国旗帜',
    'Flag of Albanian Provisional Government (1912-1914).svg': '阿尔巴尼亚临时政府旗（1912–1914）',
    'Flag of Austria (Empire Total War).svg': '奥地利国旗（《全面战争：帝国》版）',
    'Flag of Belgium (civil).svg': '比利时民用旗',
    'Flag of Bermuda (1875–1910).svg': '百慕大旗（1875–1910）',
    'Flag of Bhutan (1949–1956).svg': '不丹国旗（1949–1956）',
    'Flag of Bolivia (state).svg': '玻利维亚国旗（国家版）',
    'Flag of China (1912–1928).svg': '中华民国五色旗（1912–1928）',
    'Flag of Costa Rica.svg': '哥斯达黎加国旗',
    'Flag of Croatia (1941–1945).svg': '克罗地亚国旗（1941–1945）',
    'Flag of Denmark (state).svg': '丹麦国旗（国家版）',
    'Flag of Egypt (1922-1958).svg': '埃及国旗（1922–1958）',
    'Flag of Egypt (1952–1958).svg': '埃及国旗（1952–1958）',
    'Flag of Galicia (civil).svg': '加利西亚民用旗',
    'Flag of Georgia.svg': '格鲁吉亚国旗',
    'Flag of Germany (1935–1945).svg': '纳粹德国国旗（1935–1945）',
    'Flag of Guatemala.svg': '危地马拉国旗',
    'Flag of Haiti (1964–1986, civil).svg': '海地民用旗（1964–1986）',
    'Flag of Iran.svg': '伊朗国旗',
    'Flag of Japan.svg': '日本国旗',
    'Flag of Kachin State (1945–1974).svg': '克钦邦旗（1945–1974）',
    'Flag of Korea (1884).svg': '朝鲜王朝国旗（1884）',
    'Flag of Kyrgyzstan.svg': '吉尔吉斯斯坦国旗（维基版）',
    'Flag of La Guaira State.svg': '拉瓜伊拉州州旗',
    'Flag of Latvia.svg': '拉脱维亚国旗',
    'Flag of Libya (1977–2011).svg': '利比亚国旗（1977–2011）',
    'Flag of Lithuania (state).svg': '立陶宛国旗（国家版）',
    'Flag of Malawi.svg': '马拉维国旗',
    'Flag of Mali (1959–1961).svg': '马里国旗（1959–1961）',
    'Flag of Maryland.svg': '马里兰州州旗',
    'Flag of Mauritania.svg': '毛里塔尼亚国旗',
    'Flag of Mexico.svg': '墨西哥国旗',
    'Flag of Mississippi.svg': '密西西比州州旗',
    'Flag of Mississippi (1996–2020).svg': '密西西比州州旗（1996–2020）',
    'Flag of Mongol Military Government (1936-1937).svg': '蒙古军政府旗（1936–1937）',
    'Flag of Morocco (1666–1915).svg': '摩洛哥国旗（1666–1915）',
    'Flag of National Socialist Movement (United States).svg': '美国国家社会主义运动旗帜',
    'Flag of Ogaden National Liberation Front(2).svg': '欧加登民族解放阵线旗帜',
    'Flag of Romania.svg': '罗马尼亚国旗',
    'Flag of Russia (1991–1993).svg': '俄罗斯国旗（1991–1993）',
    'Flag of Rwanda.svg': '卢旺达国旗',
    'Flag of Saudi Arabia.svg': '沙特阿拉伯国旗',
    'Flag of Serbia.svg': '塞尔维亚国旗',
    'Flag of Singapore.svg': '新加坡国旗',
    'Flag of South Africa.svg': '南非国旗',
    'Flag of Spain (civil).svg': '西班牙民用旗',
    'Flag of Spain (Civil) alternate colours.svg': '西班牙民用旗（变体配色）',
    'Flag of Suriname (1959–1975).svg': '苏里南国旗（1959–1975）',
    'Flag of the Afghan interim government-in-exile (1988–1992).svg': '阿富汗临时流亡政府旗（1988–1992）',
    'Flag of the Armed Forces of Johor.svg': '柔佛武装部队旗',
    'Flag of the German Confederation (war).svg': '德意志邦联战旗',
    'Flag of the Government of Portuguese Macau (1976–1999).svg': '葡属澳门政府旗（1976–1999）',
    'Flag of the Indian Armed Forces.svg': '印度武装部队旗',
    'Flag of the Islamic State of Iraq and the Levant2.svg': '伊斯兰国旗帜（伊拉克和黎凡特）',
    'Flag of the President of Bangladesh.svg': '孟加拉国总统旗',
    'Flag of the Republic of Korea Armed Forces.svg': '韩国武装部队旗',
    'Flag of the Republic of the Rio Grande (historical).svg': '里奥格兰德共和国旗帜（历史）',
    'Flag of the Royal Laos Armed Forces (1952-1975).svg': '老挝皇家军队旗（1952–1975）',
    'Flag of the State of Georgia.svg': '美国佐治亚州州旗',
    'Flag of the State of Maine.svg': '缅因州州旗',
    'Flag of the Syrian Armed Forces 2025.svg': '叙利亚武装部队旗（2025）',
    'Flag of the Syrian Salvation Government.svg': '叙利亚救国政府旗帜',
    'Flag of the Syrian transitional government (Shahada).svg': '叙利亚过渡政府旗帜（清真言版）',
    'Flag of the United States.svg': '美国国旗',
    'Flag of Transnistria (state).svg': '德涅斯特河沿岸国旗（国家版）',
    'Flag of Turkey.svg': '土耳其国旗',
    'Flag of Tuvalu (state).svg': '图瓦卢国旗（国家版）',
    'Flag of Ukraine (1917–1921).svg': '乌克兰国旗（1917–1921）',
    'Flag of Venezuela (state).svg': '委内瑞拉国旗（国家版）',
    'Flag of Vienna (state).svg': '维也纳州旗',
    'Flag of Wales.svg': '威尔士旗帜',
    'Flag of Washington.svg': '华盛顿州州旗',
    'Lesser coat of arms of the Russian Empire.svg': '俄罗斯帝国小国徽',
    'Lesser Coat of Arms of Ukraine.svg': '乌克兰小国徽',
    'Military flag of Finland.svg': '芬兰军旗',
    'National emblem of Bangladesh.svg': '孟加拉国国徽',
    'National emblem of Indonesia Garuda Pancasila.svg': '印度尼西亚国徽（迦楼罗潘查希拉）',
    'Naval ensign of Bulgaria (1878–1944).svg': '保加利亚海军旗（1878–1944）',
    'Naval ensign of Estonia.svg': '爱沙尼亚海军旗',
    'Naval Ensign of India.svg': '印度海军旗',
    'Naval Ensign of Japan.svg': '日本海军旗',
    'Naval ensign of Japan (1889–1945).svg': '日本海军旗（1889–1945）',
    'Naval Ensign of Nigeria (1960–1998).svg': '尼日利亚海军旗（1960–1998）',
    'Naval ensign of Russia.svg': '俄罗斯海军旗',
    'Naval ensign of Sweden.svg': '瑞典海军旗',
    'Naval Ensign of the Soviet Union (1950–1991).svg': '苏联海军旗（1950–1991）',
    'Naval ensign of the United Kingdom.svg': '英国海军旗',
    'Presidential Standard of Algeria.svg': '阿尔及利亚总统旗',
    'Presidential Standard of Austria (-1984).svg': '奥地利总统旗（1984 年以前）',
    'Presidential Standard of Guyana (1980-1985) under President LFS Burnham.svg': '圭亚那总统旗（1980–1985，伯纳姆总统时期）',
    'Presidential Standard of Nigeria (1963).svg': '尼日利亚总统旗（1963）',
    'Presidential Standard of Palau.svg': '帕劳总统旗',
    'Presidential Standard of Togo.svg': '多哥总统旗',
    'Red ensign of Great Britain (1707–1800).svg': '英国红船旗（1707–1800）',
    'Red ensign of Great Britain (1707–1800, square canton).svg': '英国红船旗（1707–1800，方形上角）',
    'Royal Coat of Arms of Hawaii.svg': '夏威夷王国皇家徽章',
    'Royal Coat of Arms of the Kingdom of Scotland.svg': '苏格兰王国皇家徽章',
    'Royal standard of England (1406–1603).svg': '英格兰王旗（1406–1603）',
    'Royal Standard of Saudi Arabia.svg': '沙特阿拉伯王旗',
    'Sample 09-F9 protest art, Free Speech Flag by John Marcotte.svg': '09-F9 言论自由抗议旗帜',
    'State Flag and War Ensign of the Kingdom of Sardinia (1816-1848).svg': '撒丁王国国家旗与战旗（1816–1848）',
    'State flag of Persia (1907–1933).svg': '波斯国国旗（1907–1933）',
    'State flag of Venezuela (1954–2006).svg': '委内瑞拉国旗（1954–2006）',
    'War Ensign of Ethiopia (1974–1975).svg': '埃塞俄比亚战旗（1974–1975）',
    'War Ensign of Germany (1903–1919).svg': '德国战旗（1903–1919）',
    'War Ensign of Germany (1919–1921).svg': '德国战旗（1919–1921）',
    'War Ensign of Germany (1935–1938).svg': '德国战旗（1935–1938）',
    'War ensign of Germany (1938–1945).svg': '德国战旗（1938–1945）',
    'War Ensign of Manchukuo.svg': '满洲国海军战旗',
    'War Ensign of Prussia (1816).svg': '普鲁士战旗（1816）',
    'War ensign of the First Slovak Republic.svg': '斯洛伐克第一共和国战旗',
    'War Ensign of the Kingdom of Sardinia (1816-1848) aspect ratio 31-76.svg': '撒丁王国战旗（1816–1848，31:76 比例）',
    'War flag of Peru.svg': '秘鲁战旗',
    'War flag of Spain (proposal).svg': '西班牙战旗（提案）',
    'War flag of the Imperial Japanese Army.svg': '大日本帝国陆军军旗',
    'War flag of the Imperial Japanese Army (1868–1945).svg': '大日本帝国陆军军旗（1868–1945）',
    'War flag of the Italian Social Republic.svg': '意大利社会共和国战旗',
    'War Flag of the Philippines.svg': '菲律宾战旗',
    'War Flag of the Philippines (1936–1985, 1986–1998).svg': '菲律宾战旗（1936–1985、1986–1998）',
}


# ============ 地区/组织关键词（按顺序匹配英文名+描述，取首个命中） ============
REGION_KEYWORDS = [
    ('Republic of Korea', ['韩国']),
    ('British Somaliland', ['英属索马里兰']),
    ('British Straits Settlements', ['英国海峡殖民地']),
    ('Soviet Union', ['苏联']),
    ('United Kingdom', ['英国']),
    ('Great Britain', ['英国']),
    ('United States', ['美国']),
    ('Republic of China', ['中华民国']),
    ('Russian Federation', ['俄罗斯']),
    ('Russian Empire', ['俄罗斯帝国']),
    ('National Socialist', ['纳粹', '美国']),
    ('Islamic State', ['伊斯兰国', '伊拉克']),
    ('Imperial Japanese', ['大日本帝国', '日本']),
    ('Austro-Hungarian', ['奥匈帝国']),
    ('Austria-Hungary', ['奥匈帝国']),
    ('Kingdom of Sardinia', ['撒丁王国']),
    ('Kingdom of Scotland', ['苏格兰']),
    ('Italian Social Republic', ['意大利']),
    ('German Confederation', ['德意志邦联']),
    ('First Slovak Republic', ['斯洛伐克第一共和国']),
    ('Mongol Military Government', ['蒙古']),
    ('Royal Laos', ['老挝']),
    ('Albanian', ['阿尔巴尼亚']),
    ('Afghan', ['阿富汗']),
    ('Syrian', ['叙利亚']),
    ('Bangladesh', ['孟加拉国']),
    ('Ghana', ['加纳']),
    ('Kyrgyzstan', ['吉尔吉斯斯坦']),
    ('Kazakhstan', ['哈萨克斯坦']),
    ('Turkmenistan', ['土库曼斯坦']),
    ('Saudi Arabia', ['沙特阿拉伯']),
    ('South Africa', ['南非']),
    ('Costa Rica', ['哥斯达黎加']),
    ('Sri Lanka', ['斯里兰卡']),
    ('Ceylon', ['锡兰']),
    ('Mauritius', ['毛里求斯']),
    ('Malaysia', ['马来西亚']),
    ('Pakistan', ['巴基斯坦']),
    ('Australia', ['澳大利亚']),
    ('Luxembourg', ['卢森堡']),
    ('Singapore', ['新加坡']),
    ('Finland', ['芬兰']),
    ('Bulgaria', ['保加利亚']),
    ('Estonia', ['爱沙尼亚']),
    ('Sweden', ['瑞典']),
    ('Norway', ['挪威']),
    ('Denmark', ['丹麦']),
    ('Algeria', ['阿尔及利亚']),
    ('Austria', ['奥地利']),
    ('Belgium', ['比利时']),
    ('Bermuda', ['百慕大']),
    ('Bhutan', ['不丹']),
    ('Bolivia', ['玻利维亚']),
    ('Brazil', ['巴西']),
    ('Croatia', ['克罗地亚']),
    ('Egypt', ['埃及']),
    ('Eswatini', ['斯威士兰']),
    ('Ethiopia', ['埃塞俄比亚']),
    ('Germany', ['德国']),
    ('Greece', ['希腊']),
    ('Guatemala', ['危地马拉']),
    ('Guyana', ['圭亚那']),
    ('Haiti', ['海地']),
    ('India', ['印度']),
    ('Indonesia', ['印度尼西亚']),
    ('Iran', ['伊朗']),
    ('Ireland', ['爱尔兰']),
    ('Japan', ['日本']),
    ('Korea', ['朝鲜王朝']),
    ('Latvia', ['拉脱维亚']),
    ('Libya', ['利比亚']),
    ('Lithuania', ['立陶宛']),
    ('Malawi', ['马拉维']),
    ('Mali', ['马里']),
    ('Mauritania', ['毛里塔尼亚']),
    ('Mexico', ['墨西哥']),
    ('Morocco', ['摩洛哥']),
    ('Nigeria', ['尼日利亚']),
    ('Palau', ['帕劳']),
    ('Palestine', ['巴勒斯坦']),
    ('Panama', ['巴拿马']),
    ('Peru', ['秘鲁']),
    ('Philippines', ['菲律宾']),
    ('Romania', ['罗马尼亚']),
    ('Russia', ['俄罗斯']),
    ('Rwanda', ['卢旺达']),
    ('Serbia', ['塞尔维亚']),
    ('Slovakia', ['斯洛伐克']),
    ('Slovenia', ['斯洛文尼亚']),
    ('Spain', ['西班牙']),
    ('Suriname', ['苏里南']),
    ('Togo', ['多哥']),
    ('Turkey', ['土耳其']),
    ('Tuvalu', ['图瓦卢']),
    ('Uganda', ['乌干达']),
    ('Ukraine', ['乌克兰']),
    ('Venezuela', ['委内瑞拉']),
    ('Wales', ['威尔士']),
    ('Transnistria', ['德涅斯特河沿岸']),
    ('Manchukuo', ['满洲国']),
    ('Prussia', ['普鲁士']),
    ('Persia', ['波斯']),
    ('Siam', ['暹罗']),
    ('Hawaii', ['夏威夷']),
    ('England', ['英格兰']),
    ('Scotland', ['苏格兰']),
    ('Georgia', ['格鲁吉亚']),
    ('Adjara', ['阿扎尔']),
    ('Galicia', ['加利西亚']),
    ('Kachin', ['克钦邦']),
    ('Ogaden', ['欧加登']),
    ('Rio Grande', ['里奥格兰德']),
    ('Johor', ['柔佛']),
    ('Gandia', ['甘迪亚']),
    ('Odesa', ['敖德萨']),
    ('Ramla', ['拉姆拉']),
    ('Vienna', ['维也纳']),
    ('Maryland', ['马里兰州']),
    ('Mississippi', ['密西西比州']),
    ('Maine', ['缅因州']),
    ('Washington', ['华盛顿州']),
    ('Georgian Orthodox', ['格鲁吉亚']),
    ('Macau', ['澳门']),
    ('Anarchist', ['无政府主义']),
]


# ============ 用途关键词（按顺序匹配英文名） ============
USAGE_KEYWORDS = [
    ('Presidential Standard', ['总统旗']),
    ('Royal standard', ['王旗']),
    ('Air Force Ensign', ['空军']),
    ('Civil Air Ensign', ['民用旗', '空军']),
    ('Naval Ensign', ['海军', '船旗']),
    ('Civil Ensign', ['船旗']),
    ('Red ensign', ['船旗']),
    ('War Ensign', ['军旗', '海军']),
    ('War flag', ['军旗']),
    ('Military flag', ['军旗']),
    ('National emblem', ['国徽']),
    ('Coat of Arms', ['徽章']),
    ('Royal Coat of Arms', ['徽章']),
    ('Banner of the Armed Forces', ['军旗']),
    ('Armed Forces', ['军旗']),
    ('Commander-in-Chief', ['军旗']),
    ('Civil flag', ['民用旗']),
    ('State flag', ['国旗']),
    ('Flag of', ['国旗']),
    ('Car flag', ['军旗']),
    ('Bandera', ['市旗']),
    ('emblem', ['徽章']),
    ('protest', ['民运']),
    ('flag day', ['徽章']),
    ('fictitious', ['虚构']),
    ('Fictitious', ['虚构']),
    ('proposal', ['草案']),
    ('Proposal', ['草案']),
    ('Ensign', ['船旗']),
]


# ============ 图案要素关键词 ============
ELEMENT_KEYWORDS = [
    ('six-pointed', '六角星'), ('hexagram', '六角星'),
    ('seven-pointed', '七角星'),
    ('eagle', '鹰'), ('garuda', '神兽'),
    ('lion', '狮子'), ('dragon', '龙'),
    ('crescent', '月'), ('moon', '月'),
    ('sun', '太阳'), ('crown', '王冠'),
    ('tree', '树'), ('wheat', '麦穗'), ('sheaf', '麦穗'), ('rice', '麦穗'),
    ('sword', '武器'), ('shield', '盾徽'), ('escutcheon', '盾徽'),
    ('anchor', '船锚'), ('ship', '船'),
    ('hammer and sickle', '镰锤'), ('sickle', '镰锤'), ('hammer', '镰锤'),
    ('allah', '阿拉伯语'), ('arabic', '阿拉伯语'), ('shahada', '阿拉伯语'),
    ('flame', '火焰'), ('fire', '火焰'),
    ('gear', '齿轮'), ('wheel', '齿轮'), ('torch', '火炬'),
    ('hand', '肢体'), ('bird', '鸟类'),
    ('wreath', '植物'), ('olive', '植物'), ('flower', '花'),
    ('star', '五角星'),
]


# ============ 旗帜学样式关键词 ============
STYLE_KEYWORDS = [
    ('tricolour', '三色旗'), ('tricolor', '三色旗'),
    ('canton', '上角'),
    ('cross', '十字'),
    ('horizontal stripe', '横条'), ('horizontal', '横条'),
    ('vertical stripe', '竖条'), ('vertical', '竖条'),
    ('diagonal', '斜切'),
    ('triangle', '三角'),
    ('circle', '圆环'), ('round', '圆环'),
]


# ============ 手动补充/修正（键为磁盘文件名） ============
TAG_OVERRIDES = {
    'Flag of the United States.svg': {'region': ['美国'], 'usage': ['国旗'], 'style': ['上角', '横条'], 'element': ['五角星']},
    'Flag of Japan.svg': {'region': ['日本'], 'usage': ['国旗'], 'style': ['中心'], 'element': ['太阳']},
    'Flag of Washington.svg': {'region': ['美国', '华盛顿州'], 'usage': ['州旗'], 'style': ['中心']},
    'Flag of Mississippi (1996–2020).svg': {'region': ['美国', '密西西比州'], 'usage': ['州旗'], 'style': ['上角']},
    'Red ensign of Great Britain (1707–1800, square canton).svg': {'style': ['上角']},
    'Flag of the State of Georgia.svg': {'region': ['美国', '佐治亚州'], 'usage': ['州旗'], 'style': ['上角']},
    'Flag of Wales.svg': {'region': ['英国', '威尔士'], 'element': ['龙']},
    'Flag of Bhutan (1949–1956).svg': {'region': ['不丹'], 'element': ['龙']},
    'Flag of Saudi Arabia.svg': {'element': ['阿拉伯语', '武器']},
    'Flag of Iran.svg': {'element': ['阿拉伯语']},
    'Flag of Singapore.svg': {'element': ['月', '五角星']},
    'Flag of Turkey.svg': {'element': ['月', '五角星']},
    'Flag of Mauritania.svg': {'element': ['月', '五角星']},
    'Air Force Ensign of Malaysia.svg': {'element': ['月', '五角星']},
    'Air Force Ensign of Pakistan.svg': {'element': ['月', '五角星']},
    'Flag of Mexico.svg': {'element': ['盾徽']},
    'War flag of the Imperial Japanese Army.svg': {'region': ['大日本帝国', '日本'], 'usage': ['军旗'], 'element': ['太阳']},
    'War flag of the Imperial Japanese Army (1868–1945).svg': {'region': ['大日本帝国', '日本'], 'usage': ['军旗'], 'element': ['太阳']},
    'Naval Ensign of Japan.svg': {'region': ['日本'], 'usage': ['海军', '船旗'], 'element': ['太阳']},
    'Naval ensign of Japan (1889–1945).svg': {'region': ['日本'], 'usage': ['海军', '船旗'], 'element': ['太阳']},
    'Flag of China (1912–1928).svg': {'region': ['中华民国'], 'style': ['横条']},
    'Commander-in-Chief Flag of the Republic of China (Beiyang Government).svg': {'region': ['中华民国', '北洋']},
    'Flag of Korea (1884).svg': {'region': ['朝鲜王朝']},
    'Flag of Germany (1935–1945).svg': {'region': ['纳粹', '德国']},
    'Flag of National Socialist Movement (United States).svg': {'region': ['纳粹', '美国']},
    'Flag of the Islamic State of Iraq and the Levant2.svg': {'region': ['伊斯兰国', '邪教'], 'usage': ['党旗'], 'element': ['阿拉伯语', '月']},
    'Belarusian national-anarchist flag.svg': {'region': ['白俄罗斯', '无政府主义'], 'usage': ['会旗']},
    'Armed Forces of Pakistan Flag.svg': {'color': ['绿色', '白色'], 'element': ['月', '五角星']},
    'Armed forces flag day.svg': {'region': ['印度'], 'usage': ['徽章']},
    'Sample 09-F9 protest art, Free Speech Flag by John Marcotte.svg': {'region': ['美国'], 'usage': ['民运']},
    'Austria Bundesadler.svg': {'usage': ['徽章']},
    'Bandera de Gandia.svg': {'region': ['西班牙'], 'usage': ['市旗']},
    'Flag of Ogaden National Liberation Front(2).svg': {'region': ['埃塞俄比亚', '欧加登'], 'usage': ['会旗']},
    'Flag of the Syrian transitional government (Shahada).svg': {'region': ['叙利亚'], 'usage': ['国旗'], 'element': ['阿拉伯语']},
    'Flag of the Afghan interim government-in-exile (1988–1992).svg': {'region': ['阿富汗']},
    'Flag of Austria (Empire Total War).svg': {'region': ['奥地利'], 'usage': ['国旗', '虚构']},
    'Fictitious Austria-Hungary civil flag 1869-1918.svg': {'usage': ['民用旗', '虚构']},
    'Flag of Galicia (civil).svg': {'region': ['西班牙', '加利西亚'], 'usage': ['民用旗', '区旗']},
    'Flag of Adjara.svg': {'region': ['格鲁吉亚', '阿扎尔'], 'usage': ['区旗']},
    'Flag of Kachin State (1945–1974).svg': {'region': ['缅甸', '克钦邦'], 'usage': ['区旗']},
    'Flag of La Guaira State.svg': {'region': ['委内瑞拉', '拉瓜伊拉州'], 'usage': ['州旗']},
    'Flag of Vienna (state).svg': {'region': ['奥地利', '维也纳'], 'usage': ['州旗']},
    'Flag of the State of Maine.svg': {'region': ['美国', '缅因州'], 'usage': ['州旗']},
    'Flag of Maryland.svg': {'region': ['美国', '马里兰州'], 'usage': ['州旗']},
    'Flag of Mississippi.svg': {'region': ['美国', '密西西比州'], 'usage': ['州旗']},
    'Flag of the President of Bangladesh.svg': {'region': ['孟加拉国']},
    'Flag of the Republic of Korea Armed Forces.svg': {'region': ['韩国']},
    'Flag of the Republic of the Rio Grande (historical).svg': {'region': ['里奥格兰德']},
    'Flag of the Royal Laos Armed Forces (1952-1975).svg': {'region': ['老挝']},
    'Flag of the Syrian Salvation Government.svg': {'region': ['叙利亚'], 'usage': ['国旗']},
    'Flag of the Syrian Armed Forces 2025.svg': {'region': ['叙利亚']},
    'Flag of Transnistria (state).svg': {'region': ['德涅斯特河沿岸']},
    'Flag of Mongol Military Government (1936-1937).svg': {'region': ['蒙古']},
    'Flag of the Government of Portuguese Macau (1976–1999).svg': {'region': ['澳门']},
    'Coat of Arms of Odesa.svg': {'region': ['乌克兰', '敖德萨'], 'usage': ['徽章']},
    'Coat of Arms of Ramla.svg': {'region': ['以色列', '拉姆拉'], 'usage': ['徽章']},
    'Coat of Arms of Georgian Orthodox Church.svg': {'region': ['格鲁吉亚'], 'usage': ['徽章']},
    'Royal Coat of Arms of Hawaii.svg': {'region': ['夏威夷'], 'usage': ['徽章']},
    'Royal Coat of Arms of the Kingdom of Scotland.svg': {'region': ['苏格兰'], 'usage': ['徽章']},
    'Lesser coat of arms of the Russian Empire.svg': {'region': ['俄罗斯帝国'], 'usage': ['国徽']},
    'Lesser Coat of Arms of Ukraine.svg': {'region': ['乌克兰'], 'usage': ['国徽']},
    'Coat of arms of Siam (greater).svg': {'region': ['暹罗'], 'usage': ['国徽']},
    'State flag of Persia (1907–1933).svg': {'region': ['波斯'], 'usage': ['国旗']},
    'War Ensign of Manchukuo.svg': {'region': ['满洲国']},
    'Royal standard of England (1406–1603).svg': {'region': ['英格兰']},
    'Royal Standard of Saudi Arabia.svg': {'region': ['沙特阿拉伯']},
    'War flag of Spain (proposal).svg': {'usage': ['军旗']},
    'American Revolutionary War regimental flag - the Monmouth Flag.svg': {'region': ['美国'], 'usage': ['军旗']},
    'War Ensign of Ethiopia (1974–1975).svg': {'region': ['埃塞俄比亚']},
    'War Ensign of Germany (1903–1919).svg': {'region': ['德国']},
    'War Ensign of Germany (1919–1921).svg': {'region': ['德国']},
    'War Ensign of Germany (1935–1938).svg': {'region': ['德国']},
    'War ensign of Germany (1938–1945).svg': {'region': ['德国']},
    'War Ensign of Prussia (1816).svg': {'region': ['普鲁士']},
    'War ensign of the First Slovak Republic.svg': {'region': ['斯洛伐克第一共和国']},
    'War Ensign of the Kingdom of Sardinia (1816-1848) aspect ratio 31-76.svg': {'region': ['撒丁王国']},
    'War flag of Peru.svg': {'region': ['秘鲁']},
    'War flag of the Italian Social Republic.svg': {'region': ['意大利']},
    'War Flag of the Philippines.svg': {'region': ['菲律宾'], 'element': ['太阳', '五角星']},
    'War Flag of the Philippines (1936–1985, 1986–1998).svg': {'region': ['菲律宾'], 'element': ['太阳', '五角星']},
    'Civil Flag and Civil Ensign of the Kingdom of Sardinia (1816-1848).svg': {'region': ['撒丁王国']},
    'State Flag and War Ensign of the Kingdom of Sardinia (1816-1848).svg': {'region': ['撒丁王国']},
    'Ensign of Austro-Hungarian civil fleet (1869-1918).svg': {'region': ['奥匈帝国']},
    'Flag of Albanian Provisional Government (1912-1914).svg': {'region': ['阿尔巴尼亚']},
    'Flag of Austria (Empire Total War).svg': {'region': ['奥地利']},
    'British Army car flag - military member of the Army Board.svg': {'region': ['英国']},
    'Coat of arms of Brazil.svg': {'region': ['巴西'], 'usage': ['国徽']},
    'Coat of arms of Croatia.svg': {'region': ['克罗地亚'], 'usage': ['国徽']},
    'Coat of arms of Eswatini.svg': {'region': ['斯威士兰'], 'usage': ['国徽']},
    'Coat of arms of Guatemala.svg': {'region': ['危地马拉'], 'usage': ['国徽']},
    'Coat of arms of Ireland.svg': {'region': ['爱尔兰'], 'usage': ['国徽']},
    'Coat of arms of Mexico.svg': {'region': ['墨西哥'], 'usage': ['国徽'], 'element': ['盾徽']},
    'Coat of arms of Nigeria.svg': {'region': ['尼日利亚'], 'usage': ['国徽']},
    'Coat of arms of Palestine.svg': {'region': ['巴勒斯坦'], 'usage': ['国徽']},
    'Coat of arms of Panama.svg': {'region': ['巴拿马'], 'usage': ['国徽']},
    'Coat of arms of Singapore.svg': {'region': ['新加坡'], 'usage': ['国徽']},
    'Coat of arms of Slovakia.svg': {'region': ['斯洛伐克'], 'usage': ['国徽']},
    'Coat of arms of Slovenia.svg': {'region': ['斯洛文尼亚'], 'usage': ['国徽']},
    'Coat of arms of Uganda.svg': {'region': ['乌干达'], 'usage': ['国徽']},
}

# 常见 SVG 命名颜色
NAMED_COLORS = {
    'white': '#ffffff', 'black': '#000000', 'red': '#ff0000', 'green': '#008000',
    'blue': '#0000ff', 'yellow': '#ffff00', 'orange': '#ffa500', 'purple': '#800080',
    'gray': '#808080', 'grey': '#808080', 'pink': '#ffc0cb', 'brown': '#a52a2a',
    'gold': '#ffd700', 'silver': '#c0c0c0', 'navy': '#000080',
}

COLOR_CENTERS = {
    '红色': (230, 25, 25), '白色': (250, 250, 250), '黄色': (250, 210, 20),
    '蓝色': (30, 80, 200), '黑色': (20, 20, 20), '绿色': (30, 150, 60),
    '橙色': (240, 130, 30), '紫色': (140, 60, 160), '灰色': (140, 140, 140),
    '粉色': (245, 180, 190), '棕色': (140, 90, 50),
}


def nearest_color(hex_color):
    """将 #rrggbb 映射到最近的 11 种中文颜色名"""
    h = hex_color.strip().lstrip('#')
    if len(h) == 3:
        h = ''.join(c * 2 for c in h)
    if len(h) != 6:
        return None
    try:
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    except ValueError:
        return None

    # 计算饱和度与明度，避免深蓝/藏青被误判为黑色
    rn, gn, bn = r / 255.0, g / 255.0, b / 255.0
    mx, mn = max(rn, gn, bn), min(rn, gn, bn)
    diff = mx - mn
    sat = 0.0 if mx == 0 else diff / mx
    light = (mx + mn) / 2.0

    if sat < 0.18:
        if light >= 0.85:
            return '白色'
        if light <= 0.22:
            return '黑色'
        return '灰色'

    # 有彩色：只在彩色中按 RGB 距离匹配（排除黑/白/灰）
    candidates = {k: v for k, v in COLOR_CENTERS.items() if k not in ('黑色', '白色', '灰色')}
    best, best_d = None, 1e9
    for name, (cr, cg, cb) in candidates.items():
        d = (r - cr) ** 2 + (g - cg) ** 2 + (b - cb) ** 2
        if d < best_d:
            best, best_d = name, d
    return best


def extract_colors(svg_text):
    """从 SVG 中提取使用到的颜色（fill/stroke/style），映射为中文颜色名"""
    colors = set()
    for m in re.finditer(r'#([0-9a-fA-F]{3,8})\b', svg_text):
        name = nearest_color(m.group(1))
        if name:
            colors.add(name)
    # rgb(100%,100%,100%) / rgb(255,255,255)
    for m in re.finditer(r'rgba?\(\s*([0-9.]+)%?\s*,\s*([0-9.]+)%?\s*,\s*([0-9.]+)%?\s*\)', svg_text, re.I):
        try:
            if '%' in m.group(0):
                r, g, b = int(float(m.group(1)) * 2.55), int(float(m.group(2)) * 2.55), int(float(m.group(3)) * 2.55)
            else:
                r, g, b = int(float(m.group(1))), int(float(m.group(2))), int(float(m.group(3)))
        except ValueError:
            continue
        name = nearest_color('#%02x%02x%02x' % (r, g, b))
        if name:
            colors.add(name)
    for name, hexv in NAMED_COLORS.items():
        if re.search(r'\b' + re.escape(name) + r'\b', svg_text, re.I):
            cn = nearest_color(hexv)
            if cn:
                colors.add(cn)
    return colors


def match_keywords(text, table):
    """按词表顺序匹配文本，返回命中的标签列表（去重）"""
    low = text.lower()
    hits = []
    for kw, tags in table:
        if kw.lower() in low:
            tag_list = tags if isinstance(tags, list) else [tags]
            for t in tag_list:
                if t not in hits:
                    hits.append(t)
    return hits


def sanitize_id(name):
    """与 admin 端一致：保留中文/字母/数字，其余替换为 -"""
    s = re.sub(r'[^\u4e00-\u9fffa-zA-Z0-9]', '-', name)
    s = re.sub(r'-+', '-', s).strip('-')
    return s or 'item'


def main():
    with open(WIKI_DATA, encoding='utf-8') as f:
        wiki_data = json.load(f)
    wiki_entries = {}
    for s in wiki_data['svgs']:
        if s.get('local_file'):
            wiki_entries[norm(os.path.basename(s['local_file']))] = s

    with open(METADATA_FILE, encoding='utf-8') as f:
        metadata = json.load(f)

    # 幂等：先移除此前由本脚本合并的条目（含其生成的 SVG 文件）
    old_wiki = [m for m in metadata if 'source_wiki' in m]
    metadata = [m for m in metadata if 'source_wiki' not in m]
    old_files = {m['svgFile'] for m in old_wiki}

    existing_names = {m['name'] for m in metadata}
    existing_ids = {m['id'] for m in metadata}

    files = sorted(os.listdir(WIKI_SVG_DIR))
    svg_files = [fn for fn in files if fn.lower().endswith('.svg')]

    new_items = []
    new_svg_files = set()
    missing_translation = []
    not_in_wiki_data = []

    for fn in svg_files:
        entry = wiki_entries.get(norm(fn))
        if entry is None:
            not_in_wiki_data.append(fn)
            entry = {}

        if fn in TRANSLATIONS:
            name = TRANSLATIONS[fn]
            subject_cn_name, subject_en = None, None
        else:
            obj = entry.get('object_name') or fn[:-4]
            # 个别条目的 object_name 被多语言 label 污染，改用标题翻译
            if 'label QS:' in obj or len(obj) > 300:
                obj = (entry.get('title') or '').replace('File:', '').replace('.svg', '')
            translated, subject_cn_name, subject_en = translate_title(obj)
            if not translated:
                missing_translation.append(fn)
                continue
            name = translated

        # 修正 JSON 中被破坏的破折号（“每” -> “–”），并统一数字区间连字符
        name = name.replace('每', '–')
        name = re.sub(r'(?<=\d)\s*-\s*(?=\d)', '–', name)

        # 名称冲突处理
        while name in existing_names or any(nm['name'] == name for nm in new_items):
            name += '（维基版）'

        raw = (entry.get('object_name') or fn[:-4]) + ' ' + (entry.get('description') or '') + ' ' + ' '.join(entry.get('keywords') or [])

        tags = {}
        tags['usage'] = match_keywords(raw, USAGE_KEYWORDS)
        tags['region'] = match_keywords(raw, REGION_KEYWORDS)
        tags['element'] = match_keywords(raw, ELEMENT_KEYWORDS)
        tags['style'] = match_keywords(raw, STYLE_KEYWORDS)

        # 自动翻译得到的主体直接作为地区/组织标签（含父级国家）
        if subject_cn_name:
            if subject_cn_name not in tags['region']:
                tags['region'].append(subject_cn_name)
            if subject_en and subject_en in SUBJECT_PARENT:
                parent_cn = SUBJECT_PARENT[subject_en]
                if parent_cn not in tags['region']:
                    tags['region'].append(parent_cn)

        # 颜色：优先取 SVG 内实际颜色，兜底用描述中的颜色词
        with open(os.path.join(WIKI_SVG_DIR, fn), encoding='utf-8', errors='replace') as sf:
            svg_text = sf.read()
        colors = extract_colors(svg_text)
        if not colors:
            for c in ['red', 'white', 'yellow', 'blue', 'black', 'green', 'orange', 'purple', 'grey', 'gray', 'pink', 'brown']:
                if c in raw.lower():
                    colors.add({'red': '红色', 'white': '白色', 'yellow': '黄色', 'blue': '蓝色',
                                'black': '黑色', 'green': '绿色', 'orange': '橙色', 'purple': '紫色',
                                'grey': '灰色', 'gray': '灰色', 'pink': '粉色', 'brown': '棕色'}[c])
        tags['color'] = sorted(colors, key=lambda c: list(COLOR_CENTERS).index(c))

        # 手动覆盖/补充
        ov = TAG_OVERRIDES.get(fn, {})
        for cat, extra in ov.items():
            if cat == 'usage':
                # 用途为手工完整清单，整体替换，避免与规则结果叠加（如州旗不应同时为国旗）
                tags['usage'] = list(extra)
            else:
                cur = tags.setdefault(cat, [])
                for t in extra:
                    if t not in cur:
                        cur.append(t)

        # 去掉空分类
        for cat in list(tags):
            if not tags[cat]:
                del tags[cat]

        tags_flat = []
        for cat in CATEGORY_ORDER:
            tags_flat.extend(tags.get(cat, []))

        item_id = sanitize_id(name)
        while item_id in existing_ids or any(it['id'] == item_id for it in new_items):
            item_id += '-2'

        orig_name = entry.get('object_name') or fn[:-4]
        description = f'来自 Wikimedia Commons 的 SVG 矢量图（旗帜/徽章）。原始名称：{orig_name}。'

        new_items.append({
            'id': item_id,
            'name': name,
            'tags': tags,
            'tags_flat': tags_flat,
            'svgFile': f'{item_id}.svg',
            'originalImage': None,
            'description': description,
            'source_wiki': 'fotw/web/commons-svgs/' + fn,
        })

        new_svg_files.add(f'{item_id}.svg')
        shutil.copy2(os.path.join(WIKI_SVG_DIR, fn), os.path.join(SVG_DIR, f'{item_id}.svg'))

    if missing_translation:
        print('缺少译名的文件：')
        for fn in missing_translation:
            print('  ', fn)
    if not_in_wiki_data:
        print('未在 commons_svgs.json 中找到条目的文件：')
        for fn in not_in_wiki_data:
            print('  ', fn)

    if missing_translation:
        print(f'共 {len(missing_translation)} 个文件缺少译名，已中止合并，未写入 metadata.json')
        return

    metadata.extend(new_items)
    with open(METADATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    # 清理旧批次生成的 SVG 文件（已不再被任何元数据引用）
    removed = []
    for old_fn in sorted(old_files - new_svg_files):
        p = os.path.join(SVG_DIR, old_fn)
        if os.path.exists(p):
            os.remove(p)
            removed.append(old_fn)
    if removed:
        print(f'已清理旧批次的 SVG 文件：{len(removed)} 个')

    print(f'合并完成：新增 {len(new_items)} 条，metadata.json 现有 {len(metadata)} 条。')

    # 输出新标签统计，便于同步 tag-categories.js / admin
    from collections import Counter
    new_tags = Counter()
    for it in new_items:
        for cat, tags in it['tags'].items():
            for t in tags:
                new_tags[(cat, t)] += 1
    print('\n新增条目涉及的标签：')
    for (cat, t), n in sorted(new_tags.items()):
        print(f'  {cat}: {t} ({n})')


if __name__ == '__main__':
    main()
