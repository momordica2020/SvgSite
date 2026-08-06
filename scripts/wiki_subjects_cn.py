"""
Wikimedia Commons 标题自动翻译模块。
供 scripts/merge_wiki_svgs.py 使用：把英文标题翻译成中文并生成主站条目名。
"""

import re


# ============ 主体（国家/地区/组织/人物）中文译名 ============
SUBJECT_CN = {
    # 国家/地区
    'Afghanistan': '阿富汗', 'Albania': '阿尔巴尼亚', 'Algeria': '阿尔及利亚',
    'Andorra': '安道尔', 'Angola': '安哥拉', 'Anguilla': '安圭拉',
    'Argentina': '阿根廷', 'Australia': '澳大利亚', 'Austria': '奥地利',
    'Bahrain': '巴林', 'Bangladesh': '孟加拉国', 'Barbados': '巴巴多斯',
    'Belarus': '白俄罗斯', 'Belgium': '比利时', 'Bermuda': '百慕大',
    'Bhutan': '不丹', 'Bolivia': '玻利维亚', 'Bosnia and Herzegovina': '波斯尼亚和黑塞哥维那',
    'Brazil': '巴西', 'Brunei': '文莱', 'Bulgaria': '保加利亚',
    'Burma': '缅甸', 'Burundi': '布隆迪', 'Cambodia': '柬埔寨',
    'Canada': '加拿大', 'Ceylon': '锡兰', 'Chile': '智利',
    'China': '中国', 'Colombia': '哥伦比亚', 'Costa Rica': '哥斯达黎加',
    'Croatia': '克罗地亚', 'Cuba': '古巴', 'Cyprus': '塞浦路斯',
    'Czechoslovakia': '捷克斯洛伐克', 'Denmark': '丹麦', 'Egypt': '埃及',
    'El Salvador': '萨尔瓦多', 'Estonia': '爱沙尼亚', 'Eswatini': '斯威士兰',
    'Ethiopia': '埃塞俄比亚', 'Finland': '芬兰', 'France': '法国',
    'Georgia': '格鲁吉亚', 'Germany': '德国', 'Ghana': '加纳',
    'Greece': '希腊', 'Grenada': '格林纳达', 'Guatemala': '危地马拉',
    'Guinea': '几内亚', 'Guyana': '圭亚那', 'Haiti': '海地',
    'Hong Kong': '香港', 'Hungary': '匈牙利', 'Iceland': '冰岛',
    'India': '印度', 'Indonesia': '印度尼西亚', 'Iran': '伊朗',
    'Ireland': '爱尔兰', 'Israel': '以色列', 'Italy': '意大利',
    'Jamaica': '牙买加', 'Japan': '日本', 'Jordan': '约旦',
    'Kenya': '肯尼亚', 'Korea': '朝鲜', 'Kosova': '科索沃',
    'Kyrgyzstan': '吉尔吉斯斯坦', 'Kazakhstan': '哈萨克斯坦', 'Latvia': '拉脱维亚',
    'Lesotho': '莱索托', 'Libya': '利比亚', 'Liechtenstein': '列支敦士登',
    'Lithuania': '立陶宛', 'Luxembourg': '卢森堡', 'Macedonia': '马其顿',
    'Madagascar': '马达加斯加', 'Malawi': '马拉维', 'Malaysia': '马来西亚',
    'Mali': '马里', 'Manchukuo': '满洲国', 'Mauritania': '毛里塔尼亚',
    'Mauritius': '毛里求斯', 'Mexico': '墨西哥', 'Monaco': '摩纳哥',
    'Montenegro': '黑山', 'Morocco': '摩洛哥', 'Myanmar': '缅甸',
    'Nauru': '瑙鲁', 'Nepal': '尼泊尔', 'New Zealand': '新西兰',
    'Nicaragua': '尼加拉瓜', 'Nigeria': '尼日利亚', 'North Korea': '朝鲜',
    'Oman': '阿曼', 'Pakistan': '巴基斯坦', 'Palau': '帕劳',
    'Palestine': '巴勒斯坦', 'Panama': '巴拿马', 'Persia': '波斯',
    'Peru': '秘鲁', 'Poland': '波兰', 'Portugal': '葡萄牙',
    'Prussia': '普鲁士', 'Qatar': '卡塔尔', 'Rhodesia': '罗德西亚',
    'Romania': '罗马尼亚', 'Russia': '俄罗斯', 'Rwanda': '卢旺达',
    'Saar': '萨尔', 'Saint Lucia': '圣卢西亚', 'San Marino': '圣马力诺',
    'Saudi Arabia': '沙特阿拉伯', 'Senegal': '塞内加尔', 'Serbia': '塞尔维亚',
    'Seychelles': '塞舌尔', 'Siam': '暹罗', 'Singapore': '新加坡',
    'Slovakia': '斯洛伐克', 'Slovenia': '斯洛文尼亚', 'South Africa': '南非',
    'South Vietnam': '南越', 'Spain': '西班牙', 'Sri Lanka': '斯里兰卡',
    'Sudan': '苏丹', 'Suriname': '苏里南', 'Sweden': '瑞典',
    'Switzerland': '瑞士', 'Syria': '叙利亚', 'The Gambia': '冈比亚',
    'Togo': '多哥', 'Transnistria': '德涅斯特河沿岸', 'Trinidad and Tobago': '特立尼达和多巴哥',
    'Tunisia': '突尼斯', 'Turkey': '土耳其', 'Tuvalu': '图瓦卢',
    'Uganda': '乌干达', 'Ukraine': '乌克兰', 'United Kingdom': '英国',
    'United States': '美国', 'Uzbekistan': '乌兹别克斯坦', 'Venezuela': '委内瑞拉',
    'Wales': '威尔士', 'Yugoslavia': '南斯拉夫', 'Zaire': '扎伊尔',
    'Zambia': '赞比亚', 'Zimbabwe': '津巴布韦',
    # 历史政权/地区
    'Adjara': '阿扎尔', 'Alsace': '阿尔萨斯', 'Austria-Hungary': '奥匈帝国',
    'Baden-Württemberg': '巴登-符腾堡', 'British Guiana': '英属圭亚那',
    'British Somaliland': '英属索马里兰', 'Dagestan': '达吉斯坦',
    'Deseret': '德塞雷特', 'East Prussia': '东普鲁士', 'England': '英格兰',
    'Fujian People\'s Government': '福建人民政府', 'Gagauzia': '加告兹',
    'Galicia': '加利西亚', 'Gibraltar': '直布罗陀', 'Hanover': '汉诺威',
    'Hawaii': '夏威夷', 'Hejaz': '汉志', 'Khanat of Crimea': '克里米亚汗国',
    'Kingdom of Sardinia': '撒丁王国', 'Labuan': '纳闽', 'Leeward Islands': '背风群岛',
    'Lower Saxony': '下萨克森', 'Nova Scotia': '新斯科舍', 'Novorussia': '新俄罗斯',
    'North Borneo': '北婆罗洲', 'Rhodesia and Nyasaland': '罗德西亚与尼亚萨兰',
    'Sarawak': '砂拉越', 'Scotland': '苏格兰', 'South Vietnam': '南越',
    'Yugoslavia': '南斯拉夫', 'Macedonia': '马其顿', 'Kurdistan Regional Government': '库尔德斯坦地区政府',
    'Mongol Military Government': '蒙古军政府', 'Mongol United Autonomous Government': '蒙古联合自治政府',
    'Nueva Esparta State': '新埃斯帕塔州', 'La Guaira State': '拉瓜伊拉州',
    'Kachin State': '克钦邦', 'Kayah State': '克耶邦', 'Odesa': '敖德萨',
    'Ramla': '拉姆拉', 'Vienna': '维也纳', 'Washington': '华盛顿州',
    'Maryland': '马里兰州', 'Mississippi': '密西西比州', 'San Luis Potosi': '圣路易斯波托西',
    'Guadalajara': '瓜达拉哈拉', 'Caracas': '加拉加斯', 'Magas': '马加斯',
    'Nazran': '纳兹兰', 'Yeniseysk': '叶尼塞斯克', 'Konotop Raion': '科诺托普区',
    'Beaumont-Village': '博蒙村', 'Pápa': '帕波', 'Arad': '阿拉德',
    'Chicago, Illinois': '伊利诺伊州芝加哥', 'Municipality of Athens': '雅典市',
    'Saar': '萨尔', 'Zaire': '扎伊尔', 'Jersey': '泽西',
    # 组织/机构
    'Albanian Provisional Government': '阿尔巴尼亚临时政府',
    'Armed Forces of the Republic of Kazakhstan': '哈萨克斯坦共和国武装力量',
    'Benin Armed Forces': '贝宁武装力量', 'Cento': '中央条约组织',
    'Civil Defense and Exceptional Situations of Moldova': '摩尔多瓦民防与紧急情况部',
    'Georgian Orthodox Church': '格鲁吉亚正教会', 'Herat Government': '赫拉特政府',
    'Kazakh Naval Forces': '哈萨克斯坦海军', 'Kazakhstan Armed Forces': '哈萨克斯坦武装力量',
    'Kazakhstan Border Service': '哈萨克斯坦边防军', 'Kazakhstan Internal Troops': '哈萨克斯坦内卫部队',
    'Kazakhstan National Guard': '哈萨克斯坦国民卫队',
    'Kazakhstan, Ministry of Extraordinary Situations': '哈萨克斯坦紧急情况部',
    'Mauritanian armed forces and security forces': '毛里塔尼亚武装力量与安全部队',
    'National Socialist Movement': '国家社会主义运动', 'Ogaden National Liberation Front': '欧加登民族解放阵线',
    'Russian National Unity': '俄罗斯民族团结运动', 'Taliban': '塔利班',
    'Turkish Naval Forces Command': '土耳其海军司令部', 'National Police of Colombia': '哥伦比亚国家警察',
    'National Geographical Organization of Iranian Armed Forces': '伊朗武装力量国家地理组织',
    'Military Band Service of the Russian Armed Forces': '俄罗斯武装力量军乐队',
    # 人物
    'Alexander Jagiellonczyk': '亚历山大·雅盖隆', 'Amanullah Khan': '阿曼努拉汗',
    'Andrzej Czaja': '安杰伊·恰亚', 'Archbishop Marcel Lefebvre': '马塞尔·勒斐伏尔大主教',
    'Benedictus XVI': '本笃十六世', 'Benno Walter Gut': '本诺·瓦尔特·古特',
    'Caroline of Brunswick-Wolfenbüttel': '不伦瑞克-沃尔芬比特尔的卡罗琳',
    'François Hollande': '弗朗索瓦·奥朗德',
    'Frederick Augustus I of Saxony': '萨克森选侯腓特烈·奥古斯特一世',
    'Gérard Calvet': '热拉尔·卡尔韦', 'Henri de Valois as lifelong king of Poland': '瓦卢瓦的亨利（波兰国王）',
    'Jadwiga of Poland': '波兰女王雅德维加', 'Jan Sobieski as king of Poland': '扬·索别斯基（波兰国王）',
    'Jean-Louis Tauran': '让-路易·托朗', 'John Henry Newman': '约翰·亨利·纽曼',
    'Lode Aerts': '洛德·阿尔茨', 'Mgr François Touvet': '弗朗索瓦·图韦主教',
    'Michal Korybut Wisniowiecki as king of Poland': '米哈乌·科雷布特·维希尼奥维茨基（波兰国王）',
    'Paul Henri Delatte': '保罗·亨利·德拉特', 'Prince William': '威廉王子',
    'Prince William in Scotland': '威廉王子（苏格兰）', 'Princess Anne, Princess Royal': '安妮长公主',
    'Queen Adelaide': '阿德莱德王后', 'Queen Charlotte': '夏洛特王后',
    'Sigismund I of Poland': '波兰国王齐格蒙特一世',
    'Stanislaus Augustus as king of Poland': '斯坦尼斯瓦夫·奥古斯特（波兰国王）',
    'Stanislaus Leszczynski as king of Poland': '斯坦尼斯瓦夫·莱什琴斯基（波兰国王）',
    'Vasa kings of Poland': '波兰瓦萨王朝诸王', 'Vladislav Jagiello': '瓦迪斯瓦夫·雅盖沃',
    # 补充国家/地区
    'Zimbabwe Rhodesia': '津巴布韦罗德西亚', 'Dominican Republic': '多米尼加共和国',
    'Kelantan': '吉兰丹', 'Gambia': '冈比亚', 'Solomon Islands': '所罗门群岛',
    'Turks and Caicos Islands': '特克斯和凯科斯群岛', 'Gold Coast': '黄金海岸',
    'Ecuador': '厄瓜多尔', 'Yakutia': '雅库特', 'Prussia': '普鲁士',
    'Venice': '威尼斯', 'Republic of China': '中华民国', 'Kingdom of Hawaii': '夏威夷王国',
    'West Indies Federation': '西印度群岛联邦', 'Serbia and Montenegro': '塞尔维亚和黑山',
    'Grand Duchy of Lithuania': '立陶宛大公国', 'Duchy of Warsaw': '华沙公国',
    'Grand Duchy of Poznań': '波兹南大公国', 'Congress Poland': '波兰会议王国',
    'Empire of Austria': '奥地利帝国', 'Kingdom of Galicia and Lodomeria': '加利西亚和洛多梅里亚王国',
    'Polish-Lithuanian Commonwealth': '波兰立陶宛联邦', 'Crown of the Polish Kingdom': '波兰王国',
    'British Antarctic Territory': '英属南极领地', 'Free City of Danzig': '但泽自由市',
    'Republic of Vietnam': '越南共和国', 'Pridnestrovian Moldavian Republic': '德涅斯特河沿岸摩尔达维亚共和国',
    'Democratic Republic of the Sudan': '苏丹民主共和国', 'Republic of the Congo': '刚果共和国',
    'Russian Soviet Federative Socialist Republic': '俄罗斯苏维埃联邦社会主义共和国',
    'United Provinces': '荷兰联合省', 'Fiume': '阜姆', 'Urals': '乌拉尔',
    'Nile State': '尼罗州', 'Wassoulou Empire': '瓦苏鲁帝国', 'Black Country': '英国黑乡',
    'Anabarsky national rayon': '阿纳巴尔民族区', 'Punjab': '旁遮普',
    'Mongolian Armed Forces': '蒙古武装力量', 'Ukrainian Armed Forces': '乌克兰武装力量',
    'Islamic Republic of Iran': '伊朗伊斯兰共和国', 'Paraguay': '巴拉圭',
    'Vanuatu': '瓦努阿图', 'South Korea': '韩国', 'Albania': '阿尔巴尼亚',
    'Croatia': '克罗地亚', 'Netherlands': '荷兰', 'Swiss Armed Forces': '瑞士武装部队',
    'Myanmar': '缅甸', 'Mozambique': '莫桑比克', 'Peru': '秘鲁',
    'Malta': '马耳他', 'Greece': '希腊', 'Portugal': '葡萄牙',
    'Ukraine': '乌克兰', 'Cambodia': '柬埔寨', 'Thailand': '泰国',
    # 补充组织/机构
    'Karen National Liberation Army': '克伦民族解放军', 'National Bolshevik Party': '民族布尔什维克党',
    'Historical and Philosophical Society of Ohio at Cincinnati': '辛辛那提俄亥俄历史与哲学学会',
    'Esercito Italiano': '意大利陆军', 'House of Gelmini': '杰尔米尼家族',
    'January Uprising': '一月起义', 'Kraków Uprising': '克拉科夫起义',
    'Polish Government in exile': '波兰流亡政府', 'd\'Udekem d\'Acoz': '于德凯姆·达科兹家族',
    'National Science Foundation': '美国国家科学基金会',
    'National Aeronautics and Space Administration': '美国国家航空航天局',
    'United States Civil Air Patrol': '美国民用航空巡逻队', 'National Guard Bureau': '美国国民警卫队局',
    'Dutch National Police': '荷兰国家警察', 'Crimean Regional Government': '克里米亚地区政府',
    'Great Way Municipal Government of Shanghai': '上海大道市政府', 'Hoxha I Government': '霍查第一届政府',
    'People\'s Provisional Government of Vanuatu': '瓦努阿图人民临时政府',
    'Provisional Government of India': '印度临时政府',
    'Provisional Government of the Republic of Korea': '大韩民国临时政府',
    'Provisional Regional Government of the Urals': '乌拉尔临时地区政府',
    'Azerbaijan People\'s Government': '阿塞拜疆人民政府', 'United Wa State Party': '佤邦联合党',
    'Chairman of the Joint Chiefs (Philippines)': '菲律宾参谋长联席会议主席',
    'Commander in Chief of the Paraguay Armed Forces': '巴拉圭武装部队总司令',
    'Civil Freedom of Argentina': '阿根廷公民自由',
    'General Staff of the Armed Forces of the Islamic Republic of Iran': '伊朗伊斯兰共和国武装力量总参谋部',
    'General Staff of the Mongolian Armed Forces': '蒙古武装力量总参谋部',
    'General Staff of the Ukrainian Armed Forces': '乌克兰武装力量总参谋部',
    'Georgian Armed Forces': '格鲁吉亚武装部队', 'Government of National Salvation': '救国政府',
    'Indian National Congress': '印度国民大会党', 'Joint Command of the Armed Forces of Peru': '秘鲁武装部队联合司令部',
    'Lebanese Armed Forces': '黎巴嫩武装部队', 'Logistical Support of the Russian Armed Forces': '俄罗斯武装力量后勤支援',
    'Minister of the Armed Forces of the Independent State of Croatia': '克罗地亚独立国武装部队部长',
    'Minister of the Revolutionary Armed Forces of Cuba': '古巴革命武装部队部长',
    'Ministry of Defence and Armed Forces Logistics of Iran': '伊朗国防与武装力量后勤部',
    'Mozambique Defence Armed Forces': '莫桑比克国防武装部队',
    'National Guard of the Republic of Georgia': '格鲁吉亚共和国国民警卫队',
    'Nigerian Armed Forces': '尼日利亚武装部队', 'Royal Cambodian Armed Forces': '柬埔寨皇家武装部队',
    'Royal Thai Armed Forces': '泰国皇家武装部队', 'Serbian Armed Forces': '塞尔维亚武装部队',
    'Siamese Expeditionary Force': '暹罗远征军', 'Syrian Arab Armed Forces': '叙利亚阿拉伯武装部队',
    'Yemen Armed Forces': '也门武装部队', 'Armed Forces of Liberia': '利比里亚武装部队',
    'Armed Forces of Moldova': '摩尔多瓦武装部队', 'Armed Forces of the Philippines': '菲律宾武装部队',
    'Armed Forces of the Republic of the Congo': '刚果共和国武装部队',
    'Armed Forces (Tatmadaw) of Myanmar': '缅甸国防军', 'Afghan National Police': '阿富汗国家警察',
    'Armed Forces Bishop of Belgium': '比利时武装部队主教', 'National Alliance 01': '全国联盟',
    'Nuestra Libertad Civil': '我们的公民自由', 'Civil Position (Ukraine)': '乌克兰公民地位',
    'Commander of Civil Aviation (Greece)': '希腊民航司令', 'Armed Forces Day (UK)': '英国武装部队日',
    'Bao Dai': '保大', 'National Guard of Georgia': '格鲁吉亚国民警卫队',
    'Turkish Naval Forces Command': '土耳其海军司令部',
    'Kyrgyz Armed Forces': '吉尔吉斯武装力量', 'Royal Malaysian Air Force': '马来西亚皇家空军',
    'Royal Brunei Armed Forces': '文莱皇家武装部队', 'Regent of Kelantan': '吉兰丹摄政王',
    'Sultan of Kedah': '吉打苏丹', 'Sultan of Kelantan': '吉兰丹苏丹', 'Sultan of Perak': '霹雳苏丹',
    'King of Saudi Arabia': '沙特阿拉伯国王', 'President of Syria': '叙利亚总统',
    'Minister of Internal Affairs, Kazakhstan': '哈萨克斯坦内务部',
    'Ministry of Internal Affairs, Kazakhstan': '哈萨克斯坦内务部',
    'Kazakh Naval Forces': '哈萨克斯坦海军', 'Chief of Staff of the Armed Forces of Portugal': '葡萄牙武装力量总参谋长',
    '50º Stormo of the Italian Air Force': '意大利空军第50联队', 'Belgian Section of the Royal Air Force': '英国皇家空军比利时分队',
    'Imperial House of Japan': '日本皇室', 'USS Alliance': '美国海军“联盟号”',
    'Grand Duchy of Lithuania from the Statute 1588': '1588 年法规中的立陶宛大公国',
    'Crown of the Polish Kingdom': '波兰王国', 'Civic Crown': '公民桂冠',
    'Armed Forces of the Russian Federation': '俄罗斯联邦武装力量',
    'Military Academy of the General Staff of the Armed Forces of Russia': '俄罗斯武装力量总参谋部军事学院',
    'military unit of the Armed Forces of Ukraine': '乌克兰武装力量部队',
    'Free City of Danzig': '但泽自由市',
}


# 国家主体集合（“Flag of X”译为“X国旗”，其余按“X旗帜”）
COUNTRIES = {
    'Afghanistan', 'Albania', 'Algeria', 'Andorra', 'Angola', 'Anguilla',
    'Argentina', 'Australia', 'Austria', 'Bahrain', 'Bangladesh', 'Barbados',
    'Belarus', 'Belgium', 'Bermuda', 'Bhutan', 'Bolivia', 'Bosnia and Herzegovina',
    'Brazil', 'Brunei', 'Bulgaria', 'Burma', 'Burundi', 'Cambodia', 'Canada',
    'Chile', 'China', 'Colombia', 'Costa Rica', 'Croatia', 'Cuba', 'Cyprus',
    'Czechoslovakia', 'Denmark', 'Egypt', 'El Salvador', 'Estonia', 'Eswatini',
    'Ethiopia', 'Finland', 'France', 'Georgia', 'Germany', 'Ghana', 'Greece',
    'Grenada', 'Guatemala', 'Guinea', 'Guyana', 'Haiti', 'Hong Kong', 'Hungary',
    'Iceland', 'India', 'Indonesia', 'Iran', 'Ireland', 'Israel', 'Italy',
    'Jamaica', 'Japan', 'Jordan', 'Kenya', 'Kosova', 'Kyrgyzstan', 'Kazakhstan',
    'Latvia', 'Lesotho', 'Libya', 'Liechtenstein', 'Lithuania', 'Luxembourg',
    'Macedonia', 'Madagascar', 'Malawi', 'Malaysia', 'Mali', 'Mauritania',
    'Mauritius', 'Mexico', 'Monaco', 'Montenegro', 'Morocco', 'Myanmar', 'Nauru',
    'Nepal', 'New Zealand', 'Nicaragua', 'Nigeria', 'Oman', 'Pakistan', 'Palau',
    'Palestine', 'Panama', 'Peru', 'Poland', 'Portugal', 'Qatar', 'Romania',
    'Russia', 'Rwanda', 'Saint Lucia', 'San Marino', 'Saudi Arabia', 'Senegal',
    'Serbia', 'Seychelles', 'Singapore', 'Slovakia', 'Slovenia', 'South Africa',
    'South Vietnam', 'Spain', 'Sri Lanka', 'Sudan', 'Suriname', 'Sweden',
    'Switzerland', 'Syria', 'The Gambia', 'Togo', 'Transnistria',
    'Trinidad and Tobago', 'Tunisia', 'Turkey', 'Tuvalu', 'Uganda', 'Ukraine',
    'United Kingdom', 'United States', 'Uzbekistan', 'Venezuela', 'Yugoslavia',
    'Zambia', 'Zimbabwe', 'Korea', 'Persia', 'Siam', 'Ceylon', 'Manchukuo',
    'Rhodesia', 'Rhodesia and Nyasaland', 'South Vietnam', 'Zaire',
    'Liberia', 'Moldova', 'Philippines', 'Bahamas', 'Great Britain',
}


def subject_cn(subject):
    """把英文主体翻译成中文；带日期括号的先取基名再拼接。"""
    if not subject:
        return None
    s = subject.strip()
    if s in SUBJECT_CN:
        return SUBJECT_CN[s]
    s2 = re.sub(r'^the\s+', '', s, flags=re.I).strip()
    if s2 in SUBJECT_CN:
        return SUBJECT_CN[s2]
    m = re.match(r'^(.*?)\s*\(([^)]*)\)$', s)
    if m:
        base = subject_cn(m.group(1).strip())
        if base:
            return f'{base}（{m.group(2)}）'
    m2 = re.match(r'^(.*?)\s*\(([^)]*)\)$', s2)
    if m2:
        base = subject_cn(m2.group(1).strip())
        if base:
            return f'{base}（{m2.group(2)}）'
    return None


def exact_cn(subject):
    """仅精确匹配译名表（含去除 the 前缀），不做括号动态组合。"""
    if not subject:
        return None
    if subject in SUBJECT_CN:
        return SUBJECT_CN[subject]
    s2 = re.sub(r'^the\s+', '', subject, flags=re.I).strip()
    if s2 in SUBJECT_CN:
        return SUBJECT_CN[s2]
    return None


# 美国州等次级政体（“Flag of the State of X”等用）
STATE_CN = {
    'Georgia': '佐治亚州', 'Maine': '缅因州', 'Maryland': '马里兰州',
    'Mississippi': '密西西比州', 'Washington': '华盛顿州', 'California': '加利福尼亚州',
    'Texas': '得克萨斯州', 'New York': '纽约州', 'Florida': '佛罗里达州',
    'Mexico': '墨西哥州',
    'Alabama': '阿拉巴马州', 'Alaska': '阿拉斯加州', 'Arizona': '亚利桑那州',
    'Arkansas': '阿肯色州', 'Colorado': '科罗拉多州', 'Connecticut': '康涅狄格州',
    'Delaware': '特拉华州', 'Hawaii': '夏威夷州', 'Idaho': '爱达荷州',
    'Illinois': '伊利诺伊州', 'Indiana': '印第安纳州', 'Iowa': '艾奥瓦州',
    'Kansas': '堪萨斯州', 'Kentucky': '肯塔基州', 'Louisiana': '路易斯安那州',
    'Massachusetts': '马萨诸塞州', 'Michigan': '密歇根州', 'Minnesota': '明尼苏达州',
    'Missouri': '密苏里州', 'Montana': '蒙大拿州', 'Nebraska': '内布拉斯加州',
    'Nevada': '内华达州', 'New Hampshire': '新罕布什尔州', 'New Jersey': '新泽西州',
    'New Mexico': '新墨西哥州', 'North Carolina': '北卡罗来纳州',
    'North Dakota': '北达科他州', 'Ohio': '俄亥俄州', 'Oklahoma': '俄克拉何马州',
    'Oregon': '俄勒冈州', 'Pennsylvania': '宾夕法尼亚州', 'Rhode Island': '罗德岛州',
    'South Carolina': '南卡罗来纳州', 'South Dakota': '南达科他州',
    'Tennessee': '田纳西州', 'Utah': '犹他州', 'Vermont': '佛蒙特州',
    'Virginia': '弗吉尼亚州', 'West Virginia': '西弗吉尼亚州',
    'Wisconsin': '威斯康星州', 'Wyoming': '怀俄明州',
}


# ============ 标题规则（按顺序匹配，先匹配先生效） ============
TRANSLATE_RULES = [
    (r'^Air Force Ensign of (.+)$', '空军旗'),
    (r'^Civil Air Ensign of (.+)$', '民用航空旗'),
    (r'^Civil Ensign of (.+)$', '民用船旗'),
    (r'^Naval Ensign of (.+)$', '海军旗'),
    (r'^War Ensign of (.+)$', '战旗'),
    (r'^War Flag of (.+)$', '战旗'),
    (r'^War flag of (.+)$', '战旗'),
    (r'^Military flag of (.+)$', '军旗'),
    (r'^Military Ensign of (.+)$', '军旗'),
    (r'^National emblem of (.+)$', '国徽'),
    (r'^Presidential Standard of (.+)$', '总统旗'),
    (r'^Presidential standard of (.+)$', '总统旗'),
    (r'^Royal Standard of (.+)$', '王旗'),
    (r'^Royal standard of (.+)$', '王旗'),
    (r'^Royal flag of (.+)$', '王旗'),
    (r'^Royal coat of arms of (.+)$', '皇家徽章'),
    (r'^Royal Coat of Arms of (.+)$', '皇家徽章'),
    (r'^Lesser [Cc]oat of [Aa]rms of (.+)$', '小国徽'),
    (r'^Coat of arms of (.+)$', '国徽'),
    (r'^Coat of Arms of (.+)$', '国徽'),
    (r'^(?:Grand|Greater|Great|Medium|Small|Imperial|Coloured|National) [Cc]oats? of [Aa]rms of (.+)$', '国徽'),
    (r'^Coats of arms of (.+)$', '国徽'),
    (r'^Reconstruction of the Grand Coat of Arms of (.+)$', '国徽'),
    (r'^Civil flag and ensign of (.+)$', '民用旗与民用船旗'),
    (r'^National flag of (.+)$', '国旗'),
    (r'^Historical flag of (.+)$', '历史旗帜'),
    (r'^Historical national \(armorial\) flag of (.+)$', '历史国旗（纹章）'),
    (r'^Merchant Flag and War Ensign of (.+)$', '商船旗与战旗'),
    (r'^Rank flag for (.+)$', '军衔旗'),
    (r'^Regimental Colours of (.+)$', '团旗'),
    (r'^Roundel of (.+)$', '圆徽'),
    (r'^Great emblem of (.+)$', '大徽章'),
    (r'^Emblem of (.+)$', '徽章'),
    (r'^Patch of (.+)$', '臂章'),
    (r'^Insignia of (.+)$', '徽章'),
    (r'^Flag for Commander-in-Chief of (.+)$', '总司令旗'),
    (r'^Flag for the Commander of (.+)$', '司令旗'),
    (r'^Flag of the General Staff of (.+)$', '总参谋部旗'),
    (r'^Flag of the Minister of (.+)$', '部长旗'),
    (r'^Flag of the Ministry of (.+)$', '部旗'),
    (r'^Flag of the Chairman of (.+)$', '主席旗'),
    (r'^Flag of the Commander in Chief of (.+)$', '总司令旗'),
    (r'^Flag of the Joint Command of (.+)$', '联合司令部旗'),
    (r'^Flag of the Logistical Support of (.+)$', '后勤支援旗'),
    (r'^Flag of the National Guard of (.+)$', '国民警卫队旗'),
    (r'^Flag of the Provisional Government of (.+)$', '临时政府旗'),
    (r"^Flag of the People's Provisional Government of (.+)$", '人民临时政府旗'),
    (r'^Flag of the Republic of (.+)$', '共和国旗'),
    (r'^Flag of the Kingdom of (.+)$', '王国旗'),
    (r'^Standard of the President of (.+)$', '总统旗'),
    (r'^Royal Standard of the King of (.+)$', '国王王旗'),
    (r'^Royal Standard of the Sultan of (.+)$', '苏丹王旗'),
    (r'^Royal Standard of the Regent of (.+)$', '摄政王旗'),
    (r'^Royal Standard of the (.+)$', '王旗'),
    (r'^Flag of a Swiss Armed Forces (.+)$', '瑞士武装部队'),
    (r'^State flag of (.+)$', '国旗（国家版）'),
    (r'^State Flag of (.+)$', '国旗（国家版）'),
    (r'^State Flag and War Ensign of (.+)$', '国家旗与战旗'),
    (r'^Civil flag of (.+)$', '民用旗'),
    (r'^Civil Flag of (.+)$', '民用旗'),
    (r'^Civil Flag and Civil Ensign of (.+)$', '民用旗与民用船旗'),
    (r'^Government Ensign of (.+)$', '政府船旗'),
    (r'^Government Flag of (.+)$', '政府旗'),
    (r'^Flag of the President of (.+)$', '总统旗'),
    (r'^Flag of the Government of (.+)$', '政府旗'),
    (r'^Flag of the Armed Forces of (.+)$', '武装部队旗'),
    (r'^Proposed flag of (.+)$', '旗帜（提案）'),
    (r'^Battle flag of (.+)$', '战旗'),
    (r'^Flag of the State of (.+)$', '州旗'),
    (r'^Flag of (.+)$', '旗'),  # 具体是国旗还是旗帜在 translate_title 中判定
    (r'^Ensign of (.+)$', '船旗'),
    (r'^Banner of (.+)$', '旗帜'),
    (r'^Standard of (.+)$', '旗帜'),
    (r'^Red [Ee]nsign of (.+)$', '红船旗'),
    (r'^State [Ee]nsign of (.+)$', '船旗（国家版）'),
    (r'^State Marine Ensign of (.+)$', '海事船旗（国家版）'),
    (r'^Naval Auxiliary Ensign of (.+)$', '海军辅助船旗'),
]


# 无法用规则翻译的特殊标题（精确匹配）
SPECIAL_TITLES = {
    'Austria Bundesadler': '奥地利联邦之鹰徽章',
    'Bandera de Gandia': '甘迪亚市旗',
    'SAUDI FLAG': '沙特阿拉伯国旗',
    'Flag orb Saudi Arabia': '沙特阿拉伯国旗',
    'Escudo de España': '西班牙国徽',
    'Bosniak National Flag in Sandzak': '桑扎克波什尼亚克族旗帜',
    'Alleged flag of the Captaincy General of Venezuela and war ensign of the State of Venezuela': '委内瑞拉都督区传闻旗帜与委内瑞拉州战旗',
    'Fictitious "War Flag and Ensign of Austria-Hungary (1915-1918)"': '虚构奥匈帝国战旗与船旗（1915–1918）',
    'Fictitious "War flag" of Austria-Hungary': '虚构奥匈帝国战旗',
    'Der Stahlhelm Reichskriegsflagge with swastika': '钢盔联盟万字战旗',
    'Z military symbol flag black': 'Z 军徽旗（黑色）',
    'Z military symbol flag white': 'Z 军徽旗（白色）',
    'India Flag - iconic waving': '印度国旗（飘动版）',
    'Liberia Flag - iconic waving': '利比里亚国旗（飘动版）',
    'Romania Flag - iconic waving': '罗马尼亚国旗（飘动版）',
    'Tuvalu Flag - iconic waving': '图瓦卢国旗（飘动版）',
    'Japan Construction sheet': '日本国旗制图版',
    'Turkey construction sheet': '土耳其国旗制图版',
    'Naval Ensign of Japan Construction sheet': '日本海军旗制图版',
    'Presidential Standard of Turkey construction sheet': '土耳其总统旗制图版',
    'Flag of Iceland - state and war (construction sheet)': '冰岛国家旗与战旗制图版',
    'Flag of Norway - state and war (construction sheet)': '挪威国家旗与战旗制图版',
    'North Korea communist flag (Korean War)': '朝鲜共产主义旗帜（朝鲜战争）',
    'Ottoman War Flag from the Balkan Wars': '巴尔干战争奥斯曼战旗',
    'United States "civil" flag (used by sovereign citizens)': '美国“民用旗”（主权公民运动）',
    'Reverse U.S. Civil Flag (Alt Colors)': '美国民用旗反转版（变体配色）',
    'Continental Navy Ensign (early variant)': '大陆海军船旗（早期变体）',
    'Crowned Canadian Red Ensign (1870)': '加拿大红船旗（1870，加王冠）',
    'British Naval Red Ensign (1807)': '英国海军红船旗（1807）',
    'Canadian Red Ensign (1907–1922)': '加拿大红船旗（1907–1922）',
    'Green Ensign 1st Regiment': '第一团绿船旗',
    'Hellenic Naval Ensign 1935': '希腊海军旗（1935）',
    'PL Ensign Jacht Klub MW Kotwica': '波兰海军俱乐部“锚”游艇旗',
    'Uss alliance ensign 1779 john paul jones-final': '美国海军“联盟号”船旗（1779，约翰·保罗·琼斯）',
    'ROC Military Academy Flag': '中华民国军校旗',
    'ROCN Admiral\'s Flag (Beiyang government, 1912)': '中华民国海军上将旗（北洋政府，1912）',
    'ROCN Commodore\'s Flag (Beiyang government, 1912)': '中华民国海军准将旗（北洋政府，1912）',
    'ROCN Senior Officer\'s Flag (Beiyang government, 1912)': '中华民国海军高级军官旗（北洋政府，1912）',
    'ROU AB Alba Iulia Flag Historical': '罗马尼亚“阿尔巴尤利亚”号巡洋舰历史旗帜',
    'Former War Flag of Afghanistan': '阿富汗旧战旗',
    'Former War Flag of Afghanistan (variant)': '阿富汗旧战旗（变体）',
    'Former flag of the Karen National Liberation Army': '克伦民族解放军旧旗帜',
    'Bangladesh Armed Forces Flag': '孟加拉国武装部队旗',
    'Kazakhstan Armed Forces Flag': '哈萨克斯坦武装部队旗',
    'Saudi Armed Forces Flag': '沙特阿拉伯武装部队旗',
    'Saudi Ministry of National Guard Flag': '沙特阿拉伯国民警卫队部旗',
    'Russian military space troops flag': '俄罗斯军事航天部队旗',
    'National Bolshevik Party flag': '民族布尔什维克党旗',
    'National Guard of Georgia flag (2018)': '格鲁吉亚国民警卫队旗（2018）',
    'Tentara Nasional Indonesia insignia': '印度尼西亚国民军徽章',
    'Tentara Nasional Indonesia Angkatan Udara insignia': '印度尼西亚国民军空军徽章',
    'POL COA Grand Duchy of Lithuania': '立陶宛大公国徽（波兰版）',
    "College of Arms-Lant's Roll": '纹章院兰特卷纹章',
    'War Flag of Germany proposed 1920': '德国战旗（1920 提案）',
    'War Ensign of Germany (1903–1919) Iron Cross variant': '德国战旗（1903–1919，铁十字变体）',
    'Flag of National Alliance 01': '全国联盟旗帜 01',
    'Flag of Nuestra Libertad Civil (ceremonial)': '“我们的公民自由”旗（礼仪版）',
    'Flag of Civil Position (Ukraine)': '乌克兰公民地位旗',
    'Flag of Commander of Civil Aviation (Greece)': '希腊民航司令旗',
    'Flag of Armed Forces Day (UK)': '英国武装部队日旗',
    'Flag of Bao Dai (1948-1955)': '保大旗（1948–1955）',
    'Flag Used in Empire Total War for Punjab': '《全面战争：帝国》旁遮普旗',
    'Flag of the United Provinces (Empire Total War)': '荷兰联合省旗（《全面战争：帝国》版）',
    'Coat of Arms Second Mexican Empire': '墨西哥第二帝国徽章',
    'Coat of Arms of Spain-1868 Proposal with the Civic Crown': '西班牙国徽（1868 提案，公民桂冠）',
    'Kenya presidential standard JOMO KENYATTA': '肯尼亚总统旗（乔莫·肯雅塔）',
    'Kenya presidential standard MWAI KIBAKI (variant)': '肯尼亚总统旗（姆瓦伊·齐贝吉，变体）',
    'Kenya presidential standard William Ruto': '肯尼亚总统旗（威廉·鲁托）',
    'Kenya presidential standard William Ruto (new)': '肯尼亚总统旗（威廉·鲁托，新版）',
    'Presidential Standard of Guyana - President Donald Ramotar': '圭亚那总统旗（拉莫塔尔总统时期）',
    'Presidential Standard of Guyana - President Irfaan Ali': '圭亚那总统旗（伊尔凡·阿里总统时期）',
    'Presidential Standard of Senegal under Abdou Diouf': '塞内加尔总统旗（迪乌夫时期）',
    'Presidential Standard of Senegal under Abdoulaye Wade': '塞内加尔总统旗（瓦德时期）',
    'Presidential Standard of Senegal under Léopold Sédar Senghor': '塞内加尔总统旗（桑戈尔时期）',
    'Presidential Standard of Senegal under Macky Sall': '塞内加尔总统旗（萨勒时期）',
    'UK Royal Coat of Arms': '英国皇家徽章',
    'Kingdom of scotland royal arms': '苏格兰王国皇家徽章',
    'Kingdom of scotland royal arms2': '苏格兰王国皇家徽章 2',
    'Flag of the Government of National Salvation (occupied Yugoslavia)': '救国政府旗（被占领的南斯拉夫）',
    'Flag of the Government of National Salvation 2': '救国政府旗 2',
    'Coat of arms of the Government of National Salvation 2': '救国政府徽章 2',
    'Regimental Colours of the Royal Siamese Armed Forces, according to the Flag Regulation of 1892': '暹罗皇家武装部队团旗（1892 旗制规约）',
    'Flag of the Siamese Expeditionary Force in World War I (Obverse)': '暹罗远征军旗（一战，正面）',
    'Flag of the Siamese Expeditionary Force in World War I (Reverse)': '暹罗远征军旗（一战，背面）',
    'Ensign of the 50º Stormo of the Italian Air Force (1942-1943)': '意大利空军第50联队船旗（1942–1943）',
    'Ensign of the Belgian Section of the Royal Air Force': '英国皇家空军比利时分队船旗',
    'Ensign of the Imperial House of Japan': '日本皇室船旗',
    'Ensign of the USS Alliance,1779': '美国海军“联盟号”船旗（1779）',
    'Military Ensign of Kyrgyz Armed Forces (Kyrgyz)': '吉尔吉斯武装力量军旗（吉尔吉斯文版）',
    'Military Ensign of Kyrgyz Armed Forces (Russian)': '吉尔吉斯武装力量军旗（俄文版）',
    'State Ensign of the Free City of Danzig (Dienstflagge)': '但泽自由市船旗（Dienstflagge）',
    'State Marine Ensign of Singapore, 2-3': '新加坡海事船旗（2:3）',
    'Flag of the Islamic State of Iraq and the Levant2': '伊斯兰国旗帜（伊拉克和黎凡特）',
    'Flag of the British Empire (Dangarsleigh War Memorial)': '大英帝国旗（丹加斯利战争纪念馆）',
    'Flag of the Chairman of the Joint Chiefs (Philippines)': '菲律宾参谋长联席会议主席旗',
    'Flag of the Ministry of Defence and Armed Forces Logistics of Iran': '伊朗国防与武装力量后勤部旗',
    'Flag of the Ministry of Defence and Armed Forces Logistics of Iran (reverse)': '伊朗国防与武装力量后勤部旗（背面）',
    'Flag of the National Guard of the Republic of Georgia 2007-2020': '格鲁吉亚共和国国民警卫队旗（2007–2020）',
    'Flag of the Republic of China-Nanjing (War Ensign)': '中华民国（南京）战旗',
    'Flag of the Royal Thai Armed Forces HQ': '泰国皇家武装部队总部旗',
    'Flag of the Royal Thai Armed Forces Headquarters': '泰国皇家武装部队总部旗',
    'Flag of the Syrian Armed Forces based on Flag of the Syrian Arab Armed Forces': '叙利亚武装部队旗（基于叙利亚阿拉伯武装部队旗）',
    'Flag of the United States National Aeronautics and Space Administration': '美国国家航空航天局旗',
    'Grand Royal Coat of Arms of France & Navarre': '法国与纳瓦拉大皇家徽章',
    'Historical flag of the President of Turkey': '土耳其总统历史旗',
    'Historical merchant fleet flag of Montenegro version3': '黑山历史商船队旗 3',
    'Patch of the Russian Armed Forces (1992, former)': '俄罗斯武装力量臂章（1992，旧版）',
    'Presidential Standard of Guyana 1970-1980': '圭亚那总统旗（1970–1980）',
    'Proposed flag of the Black Country (2012) - Design B': '英国黑乡旗帜（2012，方案 B）',
    'Proposed flag of the Black Country (2012) - Design D': '英国黑乡旗帜（2012，方案 D）',
    'Proposed flag of the Black Country (2012) - Design E': '英国黑乡旗帜（2012，方案 E）',
    'Proposed flag of the Black Country (2012) - Design F': '英国黑乡旗帜（2012，方案 F）',
    'Roundel of the Royal Malaysian Air Force variant 02': '马来西亚皇家空军圆徽（变体 02）',
    'Royal Brunei Armed Forces emblem': '文莱皇家武装部队徽章',
    'Spanish Civil War anarchist flag (type 1)': '西班牙内战无政府主义旗帜（类型 1）',
    'Spanish civil war anarchist flag (type 3)': '西班牙内战无政府主义旗帜（类型 3）',
    'UK Civil Air Ensign Sky Blue': '英国民用航空旗（天蓝）',
    'Uzbekistan Armed Forces (Cyrillic script)': '乌兹别克斯坦武装部队旗（西里尔文版）',
    'Uzbekistan Armed Forces (Latin script)': '乌兹别克斯坦武装部队旗（拉丁文版）',
    'Flag of Peru (war) 2025': '秘鲁战旗（2025）',
    'Coat of arms of Poland2 1919-1927': '波兰国徽 2（1919–1927）',
    'Coat of arms of Gibraltar1': '直布罗陀徽章 1',
    'Coat of Arms of the Republic of Venice': '威尼斯共和国徽章',
    'Coat of Arms of Trump International Golf Club': '特朗普国际高尔夫俱乐部徽章',
    'State Flag of Hungary (1995 proposal; 1-2 aspect ratio)': '匈牙利国旗（1995 提案；1:2 比例）',
    'Flag of Syria (2025-) (stars variant)': '叙利亚国旗（2025 起，星形变体）',
    'Flag of the Republic of Korea Civil Defense Corps (1975–2023)': '韩国民防团旗（1975–2023）',
    'Naval Ensign of Brunei (1984-late 1990s)': '文莱海军旗（1984–1990 年代后期）',
    'Naval Ensign of Brunei (1984-late 1990s, variant)': '文莱海军旗（1984–1990 年代后期，变体）',
}

# 供规则使用的总统/人物补全（Kenya/Guyana/Senegal 等已用 SPECIAL_TITLES）
SUBJECT_CN.update({
    'Perak': '霹雳', 'Kedah': '吉打', 'Terengganu': '登嘉楼',
    'Third Burmese Empire (Konbaung Dynasty)': '缅甸贡榜王朝',
    'Free State of Fiume': '阜姆自由邦',
    'Liberia': '利比里亚', 'Moldova': '摩尔多瓦', 'Philippines': '菲律宾',
    'Bahamas': '巴哈马', 'Guernsey': '根西', 'Great Britain': '英国',
    'British Straits Settlements': '英国海峡殖民地',
    'Prussia 1701-1935': '普鲁士（1701–1935）', 'Hanover 1837-1866': '汉诺威（1837–1866）',
    'Herat Government 1930': '赫拉特政府（1930）', 'Poland under Russian rule': '俄国统治下的波兰',
    'Poland-official': '波兰（官方版）', 'Grand Duchy of Lithuania 1581': '立陶宛大公国（1581）',
    'House of Gelmini 2': '杰尔米尼家族 2', 'Syrian Armed Forces': '叙利亚武装部队',
    'Armed Forces of Malta': '马耳他武装部队', 'Paraguay Armed Forces': '巴拉圭武装部队',
    'Armed Forces of the Islamic Republic of Iran': '伊朗伊斯兰共和国武装力量',
    'Indian Armed Forces': '印度武装部队', 'Armed Forces of Peru': '秘鲁武装部队',
    'Russian Armed Forces': '俄罗斯武装力量',
    'Armed Forces of the Independent State of Croatia': '克罗地亚独立国武装部队',
    'Revolutionary Armed Forces of Cuba': '古巴革命武装部队',
    'Republic of Korea': '大韩民国', 'Korea Civil Defense Corps': '韩国民防团',
    'Cambodian Armed Forces': '柬埔寨武装部队', 'Gorizia': '戈里齐亚',
    'Istria': '伊斯特拉', 'Sokol': '索科尔', 'Hellenic Army': '希腊陆军',
})


def translate_title(title):
    """返回 (中文名, 主体中文, 英文主体) 或 (None, None, None)。"""
    t = title.replace('File:', '').replace('.svg', '').strip()
    if t in SPECIAL_TITLES:
        return SPECIAL_TITLES[t], None, None
    for pat, suffix in TRANSLATE_RULES:
        m = re.match(pat, t, re.I)
        if not m:
            continue
        subject = m.group(1).strip()
        subject_clean = subject.strip()
        # 整串（含括号）已有完整译名时直接用，如 “Third Burmese Empire (Konbaung Dynasty)”
        full_cn = exact_cn(subject_clean)
        if full_cn and '(' in subject_clean:
            subj_key = re.sub(r'^the\s+', '', subject_clean, flags=re.I).strip()
            is_country = subject_clean in COUNTRIES or subj_key in COUNTRIES
            sfx = '国旗' if (suffix == '旗' and is_country) else ('旗帜' if suffix == '旗' else suffix)
            sfx = '徽章' if (sfx == '国徽' and not is_country) else sfx
            return full_cn + sfx, full_cn, subject_clean
        # 把剩余括号（日期/修饰）拆出来，统一放到名称末尾
        paren = ''
        m_paren = re.search(r'\s*\(([^)]*)\)\s*$', subject_clean)
        if m_paren:
            paren = m_paren.group(1).strip()
            subject_clean = subject_clean[:m_paren.start()].strip()
        if paren:
            mods = {
                'Coat of arms variant': '国徽变体', 'Official': '官方版', 'official': '官方版',
                'civil': '民用版', 'state': '国家版', 'Front': '正面', 'Reverse': '背面',
                'old': '旧版', 'new': '新版', 'greater': '大', 'present': '今',
                'war': '战时', 'square canton': '方形上角', 'Proposal': '提案', 'proposal': '提案',
                'At Sea': '海上版', 'variant': '变体', '2-3': '2:3', '1-2': '1:2',
                'Yakutia': '雅库特', 'Order of the Seraphim': '六翼天使勋章',
                'Order of the Golden Fleece': '金羊毛勋章', 'until 2011': '至 2011 年',
                'Pantone': 'Pantone 配色', 'historical': '历史版', 'civil, horizontal': '民用版，横版',
                '3-5': '3:5', '2012': '2012', 'obverse': '正面', 'reverse': '背面',
                'Variant': '变体', 'variant': '变体', 'proposal': '提案', 'new': '新版',
                'lighter variant': '浅色变体', 'round': '圆形', 'square': '方形',
                'vertical': '竖版', 'rhombus': '菱形', 'upside down': '倒置',
                'cropped': '裁切版', 'construction sheet': '制图版',
                'non-generic': '非通用版', "st. edward's crown": '圣爱德华王冠',
                'alternate': '变体版', 'fictional': '虚构版', 'legal ratio': '法定比例',
                'armed forces': '武装部队版', '31-22 aspect': '31:22 比例',
                'in Scotland': '苏格兰版', 'pre-1993': '1993 年前',
                'FDRE': '埃塞俄比亚联邦民主共和国', 'Proposed 1919': '1919 年提案',
                'a. guagnini, 1581': 'A. 瓜尼尼，1581', 'construction sheet - leaf geometry': '制图版·枫叶几何',
                'official government version': '官方政府版', 'civil use, 1826-1854': '民用版，1826–1854',
                'unofficial civil': '非官方民用版', 'reconstructed': '复原版',
                'empire total war': '《全面战争：帝国》版', 'state ensign': '国家船旗',
                'without national emblem': '无国徽版', 'pre–2011, civil': '2011 年前民用版',
                'original': '原版', 'russian tricolour': '俄罗斯三色旗样式',
                'pashto and dari': '普什图语和达里语', 'unofficial improved version': '非官方改进版',
                'corrected': '修正版', 'alternative version': '另版', 'green': '绿色',
                'us government printing office specifications': '美国政府印刷局规格',
                'improved': '改进版', 'dienstflagge': '官方旗', 'flaggenbuch': '《旗帜手册》版',
            }
            paren_lower = paren.lower()
            mods_lower = {k.lower(): v for k, v in mods.items()}
            if paren_lower in mods_lower:
                paren = mods_lower[paren_lower]
            m_v = re.match(r'^[Vv]ariant\s+(.+)$', paren)
            if m_v:
                paren = '变体 ' + m_v.group(1).strip()
            if 'at sea' in paren.lower():
                paren = re.sub(r'\bat sea\b', '海上版', paren, flags=re.I)
            paren = re.sub(r'\bBalkenkreuz\b', '巴尔干十字徽', paren)
            paren = re.sub(r'\bIron Cross\b', '铁十字', paren)
            paren = re.sub(r'\bcirca\s+', '约 ', paren, flags=re.I)
            paren = re.sub(r'\bpresent\b', '今', paren)
            paren = re.sub(r'\s*-\s*', '–', paren)
        # “Flag of the State of X” 用美国州名
        if suffix == '州旗' and subject_clean in STATE_CN:
            state_cn = STATE_CN[subject_clean]
            return state_cn + '州旗' + (f'（{paren}）' if paren else ''), state_cn, subject_clean
        # 瑞士武装部队军衔旗：flag of a Swiss Armed Forces X
        if suffix == '瑞士武装部队':
            ranks = {
                'brigadier general': '准将', 'general and chief of the armed forces': '上将兼武装部队总司令',
                'lieutenant general': '中将', 'major general': '少将',
            }
            rank_cn = ranks.get(subject_clean.lower())
            if not rank_cn:
                return None, None, None
            return '瑞士武装部队' + rank_cn + '旗', '瑞士', subject_clean
        cn = subject_cn(subject_clean)
        if not cn:
            return None, None, None
        subj_key = re.sub(r'^the\s+', '', subject_clean, flags=re.I).strip()
        is_country = subject_clean in COUNTRIES or subj_key in COUNTRIES
        # “Flag of X”：国家→X国旗，否则 X旗帜
        if suffix == '旗':
            suffix = '国旗' if is_country else '旗帜'
        # “Coat of arms of X”：国家→X国徽，否则 X徽章
        if suffix == '国徽' and not is_country:
            suffix = '徽章'
        return cn + suffix + (f'（{paren}）' if paren else ''), cn, subject_clean
    return None, None, None
