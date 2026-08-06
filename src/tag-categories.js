/**
 * 标签分类配置（二级标签树：一级分类 -> 二级标签）
 * 本文件同时供浏览器（index.html / detail 页）与 Node（scripts/generate.js）使用。
 *
 * 分类说明：
 *   style   旗帜学样式（构图/形制：三角、中心、横线、上角……）
 *   color   颜色（红色、黄色……）
 *   element 图案要素（鸟、龙、神兽、植物……）
 *   region  地区/组织（旗帜所属地区或组织）
 *   usage   用途（logo、国徽、船旗、国旗……）
 *   other   其他（未归类的兜底）
 */
(function (root, factory) {
    var api = factory();
    if (typeof module !== 'undefined' && module.exports) {
        module.exports = api;
    } else {
        root.TAG_CATEGORIES = api.TAG_CATEGORIES;
        root.TAG_TO_CATEGORY = api.TAG_TO_CATEGORY;
        root.classifyTags = api.classifyTags;
        root.flattenTags = api.flattenTags;
    }
})(typeof window !== 'undefined' ? window : this, function () {
    'use strict';

    var TAG_CATEGORIES = {
        style: {
            label: '旗帜学样式',
            icon: '📐',
            tags: [
                '中心', '上角', '横条', '横线', '竖条', '竖切', '斜切', '三等分',
                '方块', '方旗', '三角', '三角旗', '燕尾', '十字', '圆环', '十角形',
                '心形', '箭', '箭头', '镶边', '波浪', '剪影', '地图', '风景',
                '三色旗', '五色旗', '米字旗', '五星红旗', '青天白日',
                '八卦', '太极', '阴阳', '万字', '草案',
            ]
        },
        color: {
            label: '颜色',
            icon: '🎨',
            tags: [
                '红色', '白色', '黄色', '蓝色', '黑色', '绿色',
                '橙色', '紫色', '灰色', '粉色', '棕色',
            ]
        },
        element: {
            label: '图案要素',
            icon: '🐉',
            tags: [
                // 星形
                '五角星', '六角星', '七角星', '四角星', '九角星',
                // 动物/生物
                '动物', '鸟类', '龙', '神兽', '狮子', '鹰', '双头鹰', '虎', '马',
                '鸡', '昆虫', '麒麟', '鸿雁',
                // 植物
                '植物', '花', '树', '麦穗', '嘉禾', '梅花',
                // 文字
                '汉字', '英文', '阿拉伯语', '俄文', '蒙古文', '天成文',
                // 天体/自然
                '太阳', '月', '月亮', '地球', '火焰', '闪电',
                // 器物
                '镰锤', '火炬', '齿轮', '翅膀', '王冠', '皇冠', '头盔', '盾徽',
                '鞭子', '锄头', '武器', '船锚', '船',
                // 建筑/其他
                '建筑', '机器人', '肢体', '孙中山', '人物', '骑士',
                '十二章', '华虫', '纹章',
            ]
        },
        region: {
            label: '地区/组织',
            icon: '🌍',
            tags: [
                // 中国地区
                '中国', '中华人民共和国', '中华民国', '台湾', '清朝', '北洋',
                '香港', '内蒙古', '内蒙古自治政府', '内蒙古人民革命党', '海南',
                '东北', '琼崖', '山西', '河北', '上海', '中西',
                // 外国
                '英国', '德国', '意大利', '比利时', '苏联', '吉尔吉斯斯坦',
                '阿尔巴尼亚', '以色列', '巴勒斯坦', '荷兰', '法国', '加拿大',
                '不丹', '立陶宛', '哈萨克斯坦', '神圣罗马帝国', '蒙古',
                '丹麦', '乌克兰', '乌干达', '伊拉克', '伊朗', '俄罗斯', '保加利亚',
                '克罗地亚', '利比亚', '加纳', '南非', '卢旺达', '卢森堡', '印度',
                '印度尼西亚', '危地马拉', '叙利亚', '哥斯达黎加', '图瓦卢', '土耳其',
                '圭亚那', '埃及', '埃塞俄比亚', '塞尔维亚', '墨西哥', '多哥', '奥地利',
                '委内瑞拉', '威尔士', '孟加拉国', '尼日利亚', '巴基斯坦', '巴拿马',
                '巴西', '帕劳', '拉脱维亚', '摩洛哥', '斯威士兰', '斯洛伐克',
                '斯洛文尼亚', '斯里兰卡', '新加坡', '日本', '格鲁吉亚', '毛里塔尼亚',
                '毛里求斯', '沙特阿拉伯', '澳大利亚', '爱尔兰', '爱沙尼亚', '玻利维亚',
                '瑞典', '白俄罗斯', '百慕大', '秘鲁', '缅甸', '罗马尼亚', '美国',
                '老挝', '芬兰', '苏格兰', '苏里南', '菲律宾', '西班牙', '海地', '英格兰', '阿富汗',
                '阿尔及利亚', '阿尔巴尼亚', '韩国', '马拉维', '马来西亚', '马里', '比利时',
                // 州/行政区/城市
                '佐治亚州', '华盛顿州', '密西西比州', '缅因州', '马里兰州',
                '加利西亚', '克钦邦', '拉瓜伊拉州', '拉姆拉', '敖德萨', '维也纳',
                '澳门', '阿扎尔', '甘迪亚', '夏威夷', '柔佛',
                // 历史政权
                '俄罗斯帝国', '大日本帝国', '奥匈帝国', '德意志邦联', '德涅斯特河沿岸',
                '撒丁王国', '斯洛伐克第一共和国', '朝鲜王朝', '满洲国', '波斯', '暹罗',
                '锡兰', '普鲁士', '英国海峡殖民地', '英属索马里兰', '里奥格兰德', '欧加登',
                // 组织/意识形态
                '中国共产党', '国民党', '中国人民解放军', '共产党',
                '犹太', '穆斯林', '佛教', '宗教', '邪教', '意识形态',
                '共产主义', '纳粹', '法西斯', '反福瑞', '匿名者', '黑客',
                'LGBT', '苏维埃', '无政府主义', '伊斯兰国',
            ]
        },
        usage: {
            label: '用途',
            icon: '🏷️',
            tags: [
                // 旗/徽种类
                '国旗', '军旗', '党旗', '会旗', '校旗', '团旗', '市旗', '区旗',
                '州旗', '民用旗', '船旗', '总统旗', '王旗',
                '海军', '陆军', '空军', '国徽', '军徽', '党徽', '徽章', 'logo', '公司',
                // 机构
                '海关', '缉私处', '巡警', '警察', '武警', '邮政', '盐务', '航天',
                '国防部', '海军总长旗', '参谋部', '抗大', '军校',
                '红军', '共青团', '少先队', '火箭军', '军事航天部队',
                '网络空间部队', '信息支援部队', '联勤保障部队', '整复师',
                // 性质
                '抗日战争', '虚构', '搞笑', '民运', '政党', '地区',
            ]
        },
        other: {
            label: '其他',
            icon: '📦',
            tags: []
        }
    };

    var TAG_CATEGORY_ORDER = ['style', 'color', 'element', 'region', 'usage', 'other'];

    // 反向映射：标签 -> 分类
    var TAG_TO_CATEGORY = {};
    Object.keys(TAG_CATEGORIES).forEach(function (cat) {
        TAG_CATEGORIES[cat].tags.forEach(function (tag) {
            TAG_TO_CATEGORY[tag] = cat;
        });
    });

    /**
     * 将扁平标签数组按分类归类，返回 { style: [...], color: [...] }。
     * 无法识别的标签归入 other。
     */
    function classifyTags(flatTags) {
        var result = {};
        TAG_CATEGORY_ORDER.forEach(function (cat) {
            result[cat] = [];
        });
        (flatTags || []).forEach(function (tag) {
            var cat = TAG_TO_CATEGORY[tag] || 'other';
            if (result[cat].indexOf(tag) === -1) {
                result[cat].push(tag);
            }
        });
        // 去掉空分类
        Object.keys(result).forEach(function (cat) {
            if (result[cat].length === 0) {
                delete result[cat];
            }
        });
        return result;
    }

    /**
     * 将分类字典扁平化为标签数组（按分类顺序）。
     */
    function flattenTags(tagsObj) {
        if (!tagsObj || typeof tagsObj !== 'object') return [];
        var out = [];
        TAG_CATEGORY_ORDER.forEach(function (cat) {
            (tagsObj[cat] || []).forEach(function (tag) {
                if (out.indexOf(tag) === -1) out.push(tag);
            });
        });
        return out;
    }

    return {
        TAG_CATEGORIES: TAG_CATEGORIES,
        TAG_TO_CATEGORY: TAG_TO_CATEGORY,
        TAG_CATEGORY_ORDER: TAG_CATEGORY_ORDER,
        classifyTags: classifyTags,
        flattenTags: flattenTags
    };
});
