"""
SVG Gallery 管理工具
用于管理 SVG 图片的元数据（增删改查）、预览、生成数据文件和一键同步至 GitHub。

使用方法:
    python app.py

依赖: 无（仅使用 Python 标准库）
"""

import io
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import tkinter as tk
from datetime import datetime
from tkinter import Image, filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText
from PIL import Image, ImageTk
import cairosvg
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPM

# 项目根目录（admin 的上级目录）
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SVG_DIR = os.path.join(PROJECT_ROOT, 'svg')
ORIGINALS_DIR = os.path.join(PROJECT_ROOT, 'originals')
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
METADATA_FILE = os.path.join(DATA_DIR, 'metadata.json')
GENERATE_SCRIPT = os.path.join(PROJECT_ROOT, 'scripts', 'generate.js')

# 标签分类配置
TAG_CATEGORIES = {
    'style':   {'label': '旗帜学样式', 'icon': '📐', 'tags': [
        '中心', '上角', '横条', '横线', '竖条', '竖切', '斜切', '三等分',
        '方块', '方旗', '三角', '三角旗', '燕尾', '十字', '圆环', '十角形',
        '心形', '箭', '箭头', '镶边', '波浪', '剪影', '地图', '风景',
        '三色旗', '五色旗', '米字旗', '五星红旗', '青天白日',
        '八卦', '太极', '阴阳', '万字', '草案',
    ]},
    'color':   {'label': '颜色', 'icon': '🎨', 'tags': [
        '红色', '白色', '黄色', '蓝色', '黑色', '绿色', '橙色', '紫色',
        '灰色', '粉色', '棕色',
    ]},
    'element': {'label': '图案要素', 'icon': '🐉', 'tags': [
        '五角星', '六角星', '七角星', '四角星', '九角星',
        '动物', '鸟类', '龙', '神兽', '狮子', '鹰', '双头鹰', '虎', '马',
        '鸡', '昆虫', '麒麟', '鸿雁',
        '植物', '花', '树', '麦穗', '嘉禾', '梅花',
        '汉字', '英文', '阿拉伯语', '俄文', '蒙古文', '天成文',
        '太阳', '月', '月亮', '地球', '火焰', '闪电',
        '镰锤', '火炬', '齿轮', '翅膀', '王冠', '皇冠', '头盔', '盾徽',
        '鞭子', '锄头', '武器', '船锚', '船',
        '建筑', '机器人', '肢体', '孙中山', '人物', '骑士',
        '十二章', '华虫', '纹章',
    ]},
    'region':  {'label': '地区/组织', 'icon': '🌍', 'tags': [
        '中国', '中华人民共和国', '中华民国', '台湾', '清朝', '北洋',
        '香港', '内蒙古', '内蒙古自治政府', '内蒙古人民革命党', '海南',
        '东北', '琼崖', '山西', '河北', '上海', '中西',
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
        '佐治亚州', '华盛顿州', '密西西比州', '缅因州', '马里兰州',
        '加利西亚', '克钦邦', '拉瓜伊拉州', '拉姆拉', '敖德萨', '维也纳',
        '澳门', '阿扎尔', '甘迪亚', '夏威夷', '柔佛',
        '俄罗斯帝国', '大日本帝国', '奥匈帝国', '德意志邦联', '德涅斯特河沿岸',
        '撒丁王国', '斯洛伐克第一共和国', '朝鲜王朝', '满洲国', '波斯', '暹罗',
        '锡兰', '普鲁士', '英国海峡殖民地', '英属索马里兰', '里奥格兰德', '欧加登',
        '中国共产党', '国民党', '中国人民解放军', '共产党',
        '犹太', '穆斯林', '佛教', '宗教', '邪教', '意识形态',
        '共产主义', '纳粹', '法西斯', '反福瑞', '匿名者', '黑客',
        'LGBT', '苏维埃', '无政府主义', '伊斯兰国',
    ]},
    'usage':   {'label': '用途', 'icon': '🏷️', 'tags': [
        '国旗', '军旗', '党旗', '会旗', '校旗', '团旗', '市旗', '区旗',
        '州旗', '民用旗', '船旗', '总统旗', '王旗',
        '海军', '陆军', '空军', '国徽', '军徽', '党徽', '徽章', 'logo', '公司',
        '海关', '缉私处', '巡警', '警察', '武警', '邮政', '盐务', '航天',
        '国防部', '海军总长旗', '参谋部', '抗大', '军校',
        '红军', '共青团', '少先队', '火箭军', '军事航天部队',
        '网络空间部队', '信息支援部队', '联勤保障部队', '整复师',
        '抗日战争', '虚构', '搞笑', '民运', '政党', '地区',
    ]},
    'other':   {'label': '其他', 'icon': '📦', 'tags': []},
}

# 反向映射
TAG_TO_CATEGORY = {}
for _cat, _info in TAG_CATEGORIES.items():
    for _t in _info['tags']:
        TAG_TO_CATEGORY[_t] = _cat

TAG_CATEGORY_ORDER = ['style', 'color', 'element', 'region', 'usage', 'other']


class SvgGalleryAdmin:
    def __init__(self, root):
        self.root = root
        self.root.title("SVG Gallery 管理工具")
        self.root.geometry("1000x700")
        self.root.minsize(800, 600)

        # 当前选中的条目
        self.current_id = None

        self.setup_styles()
        self.setup_ui()
        self.ensure_dirs()
        self.load_metadata()

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Toolbar.TFrame', padding=5)
        style.configure('Action.TButton', padding=5)
        style.configure('Treeview', rowheight=28)
        style.configure('Treeview.Heading', font=('Segoe UI', 10, 'bold'))

    def setup_ui(self):
        # 顶部工具栏
        toolbar = ttk.Frame(self.root)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=8, pady=4)

        ttk.Button(toolbar, text="新建", command=self.new_item, style='Action.TButton').pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="保存", command=self.save_item, style='Action.TButton').pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="删除", command=self.delete_item, style='Action.TButton').pack(side=tk.LEFT, padx=2)
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8, pady=2)
        ttk.Button(toolbar, text="生成数据", command=self.generate_data, style='Action.TButton').pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="同步至 GitHub", command=self.sync_github, style='Action.TButton').pack(side=tk.LEFT, padx=2)
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8, pady=2)
        ttk.Button(toolbar, text="刷新列表", command=self.load_metadata, style='Action.TButton').pack(side=tk.LEFT, padx=2)

        # 状态栏
        self.status_var = tk.StringVar(value="就绪")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        # 主区域：左侧列表 + 右侧编辑
        paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        # 左侧列表
        list_frame = ttk.LabelFrame(paned, text="图片列表", padding=4)
        paned.add(list_frame, weight=1)

        self.tree = ttk.Treeview(list_frame, columns=('name', 'tags'), show='headings', selectmode='browse')
        self.tree.heading('name', text='名称')
        self.tree.heading('tags', text='标签')
        self.tree.column('name', width=150)
        self.tree.column('tags', width=200)
        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree.bind('<<TreeviewSelect>>', self.on_select)

        # 右侧编辑区
        edit_frame = ttk.LabelFrame(paned, text="编辑", padding=8)
        paned.add(edit_frame, weight=2)

        self.build_edit_panel(edit_frame)

    def build_edit_panel(self, parent):
        # ID
        ttk.Label(parent, text="ID:").grid(row=0, column=0, sticky=tk.W, pady=4)
        self.id_var = tk.StringVar()
        ttk.Entry(parent, textvariable=self.id_var, state='readonly', width=40).grid(row=0, column=1, sticky=tk.EW, pady=4)

        # 名称
        ttk.Label(parent, text="名称:").grid(row=1, column=0, sticky=tk.W, pady=4)
        self.name_var = tk.StringVar()
        ttk.Entry(parent, textvariable=self.name_var, width=40).grid(row=1, column=1, sticky=tk.EW, pady=4)

        # 标签 - 按分类分栏，放在可滚动区域中
        ttk.Label(parent, text="标签分类:").grid(row=2, column=0, sticky=tk.NW, pady=4)
        tags_outer = ttk.Frame(parent)
        tags_outer.grid(row=2, column=1, sticky=tk.NSEW, pady=4)

        # 创建Canvas+Scrollbar实现可滚动标签区域
        tags_canvas = tk.Canvas(tags_outer, height=180, highlightthickness=0)
        tags_scrollbar = ttk.Scrollbar(tags_outer, orient=tk.VERTICAL, command=tags_canvas.yview)
        tags_inner = ttk.Frame(tags_canvas)
        tags_inner.bind(
            '<Configure>',
            lambda e: tags_canvas.configure(scrollregion=tags_canvas.bbox('all'))
        )
        tags_canvas.create_window((0, 0), window=tags_inner, anchor='nw')
        tags_canvas.configure(yscrollcommand=tags_scrollbar.set)
        tags_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tags_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        # 鼠标滚轮支持
        def _on_mousewheel(event):
            tags_canvas.yview_scroll(int(-1 * (event.delta / 120)), 'units')
        tags_canvas.bind('<Enter>', lambda e: tags_canvas.bind_all('<MouseWheel>', _on_mousewheel))
        tags_canvas.bind('<Leave>', lambda e: tags_canvas.unbind_all('<MouseWheel>'))

        self.tag_category_vars = {}  # {category: tk.StringVar}
        self.tag_category_entries = {}  # {category: ttk.Entry}
        for i, cat in enumerate(TAG_CATEGORY_ORDER):
            info = TAG_CATEGORIES[cat]
            # 分类标签行：图标+分类名 在左，输入框在右
            row_frame = ttk.Frame(tags_inner)
            row_frame.grid(row=i, column=0, sticky=tk.EW, pady=2, padx=4)
            row_frame.columnconfigure(1, weight=1)
            cat_label_text = f"{info['icon']} {info['label']}"
            ttk.Label(row_frame, text=cat_label_text, width=12).grid(row=0, column=0, sticky=tk.W, padx=(0, 6))
            var = tk.StringVar()
            entry = ttk.Entry(row_frame, textvariable=var, width=40)
            entry.grid(row=0, column=1, sticky=tk.EW)
            self.tag_category_vars[cat] = var
            self.tag_category_entries[cat] = entry
            # 快捷标签按钮行（紧凑排列）
            suggested = info['tags']
            if suggested:
                btn_frame = ttk.Frame(tags_inner)
                btn_frame.grid(row=i, column=0, sticky=tk.W, padx=4, pady=(0, 4))
                # 分类标签列宽对齐
                ttk.Label(btn_frame, text='', width=14).grid(row=0, column=0)
                btns_area = ttk.Frame(btn_frame)
                btns_area.grid(row=0, column=1, sticky=tk.W)
                # 每行最多放 N 个按钮
                per_row = 8
                for j, tag in enumerate(suggested):
                    r, c = divmod(j, per_row)
                    btn = tk.Button(btns_area, text=tag, relief=tk.FLAT, font=('Segoe UI', 8),
                                    padx=4, pady=1, height=1,
                                    command=lambda t=tag, c=cat: self.toggle_tag(t, c))
                    btn.grid(row=r, column=c, padx=1, pady=1, sticky=tk.W)

        # SVG文件
        svg_row = 3
        ttk.Label(parent, text="SVG 文件:").grid(row=svg_row, column=0, sticky=tk.W, pady=4)
        svg_frame = ttk.Frame(parent)
        svg_frame.grid(row=svg_row, column=1, sticky=tk.EW, pady=4)
        self.svg_file_var = tk.StringVar()
        ttk.Entry(svg_frame, textvariable=self.svg_file_var, width=30).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(svg_frame, text="选择...", command=self.choose_svg).pack(side=tk.LEFT, padx=4)
        ttk.Button(svg_frame, text="导入", command=self.import_svg).pack(side=tk.LEFT)

        # 原始图片
        orig_row = svg_row + 1
        ttk.Label(parent, text="原始图片:").grid(row=orig_row, column=0, sticky=tk.W, pady=4)
        orig_frame = ttk.Frame(parent)
        orig_frame.grid(row=orig_row, column=1, sticky=tk.EW, pady=4)
        self.original_image_var = tk.StringVar()
        ttk.Entry(orig_frame, textvariable=self.original_image_var, width=30).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(orig_frame, text="选择...", command=self.choose_original).pack(side=tk.LEFT, padx=4)
        ttk.Button(orig_frame, text="导入", command=self.import_original).pack(side=tk.LEFT)
        ttk.Button(orig_frame, text="清除", command=self.clear_original).pack(side=tk.LEFT, padx=4)

        # SVG预览
        preview_row = orig_row + 1
        ttk.Label(parent, text="SVG 预览:").grid(row=preview_row, column=0, sticky=tk.NW, pady=4)
        preview_frame = ttk.Frame(parent, relief=tk.SUNKEN, borderwidth=1)
        preview_frame.grid(row=preview_row, column=1, sticky=tk.NSEW, pady=4)
        self.preview_canvas = tk.Canvas(preview_frame, width=400, height=300, bg='#f1f5f9')
        self.preview_canvas.pack(fill=tk.BOTH, expand=True)
        self._preview_cache = {}
        self._preview_cache_key = None
        self._preview_thread = None
        self._preview_token = 0
        self._preview_loading_id = None

        # 描述
        desc_row = preview_row + 1
        ttk.Label(parent, text="Markdown 描述:").grid(row=desc_row, column=0, sticky=tk.NW, pady=4)
        self.desc_text = ScrolledText(parent, width=50, height=12, font=('Consolas', 10))
        self.desc_text.grid(row=desc_row, column=1, sticky=tk.NSEW, pady=4)

        parent.columnconfigure(1, weight=1)
        parent.rowconfigure(desc_row, weight=1)

        # 绑定变化时刷新预览
        self.svg_file_var.trace_add('write', lambda *_: self.update_preview())

    # ========== 目录管理 ==========
    def ensure_dirs(self):
        for d in [SVG_DIR, ORIGINALS_DIR, DATA_DIR]:
            os.makedirs(d, exist_ok=True)

    # ========== 标签分类辅助方法 ==========
    def toggle_tag(self, tag, category):
        """在指定分类的输入框中切换tag的选中状态"""
        var = self.tag_category_vars.get(category)
        if not var:
            return
        current = [t.strip() for t in re.split(r'[,，]', var.get()) if t.strip()]
        if tag in current:
            current.remove(tag)
        else:
            current.append(tag)
        var.set(', '.join(current))

    def load_tags_to_fields(self, item):
        """从metadata条目加载tags到分类输入框"""
        tags = item.get('tags', [])
        # 兼容分类字典和扁平数组
        if isinstance(tags, dict):
            for cat in TAG_CATEGORY_ORDER:
                var = self.tag_category_vars.get(cat)
                if var:
                    var.set(', '.join(tags.get(cat, [])))
        elif isinstance(tags, list):
            # 扁平数组：按分类拆分
            for cat in TAG_CATEGORY_ORDER:
                var = self.tag_category_vars.get(cat)
                if var:
                    var.set('')
            for tag in tags:
                cat = TAG_TO_CATEGORY.get(tag, 'other')
                var = self.tag_category_vars.get(cat)
                if var:
                    current = var.get().strip()
                    var.set((current + ', ' + tag) if current else tag)

    def collect_tags_from_fields(self):
        """从分类输入框收集tags，返回分类字典"""
        result = {}
        for cat in TAG_CATEGORY_ORDER:
            var = self.tag_category_vars.get(cat)
            if not var:
                continue
            raw = var.get().strip()
            tags = [t.strip() for t in re.split(r'[,，]', raw) if t.strip()] if raw else []
            if tags:
                result[cat] = tags
        return result

    def tags_to_flat_string(self, item):
        """将item的tags（无论格式）转换为逗号分隔的字符串（用于列表显示）"""
        tags = item.get('tags', [])
        if isinstance(tags, dict):
            parts = []
            for cat in TAG_CATEGORY_ORDER:
                parts.extend(tags.get(cat, []))
            return ', '.join(parts)
        elif isinstance(tags, list):
            return ', '.join(tags)
        return ''

    def tags_to_flat_list(self, item):
        """将item的tags（无论格式）转换为扁平数组"""
        tags = item.get('tags', [])
        if isinstance(tags, dict):
            parts = []
            for cat in TAG_CATEGORY_ORDER:
                parts.extend(tags.get(cat, []))
            return parts
        elif isinstance(tags, list):
            return tags
        return []

    # ========== 元数据管理 ==========
    def load_metadata(self):
        """加载 metadata.json 并刷新列表"""
        if not os.path.exists(METADATA_FILE):
            self.metadata = []
            with open(METADATA_FILE, 'w', encoding='utf-8') as f:
                json.dump([], f, ensure_ascii=False, indent=2)
        else:
            try:
                with open(METADATA_FILE, 'r', encoding='utf-8') as f:
                    self.metadata = json.load(f)
            except Exception as e:
                self.set_status(f"读取 metadata.json 失败: {e}")
                self.metadata = []

        self.refresh_list()
        self.set_status(f"已加载 {len(self.metadata)} 条记录")

    def save_metadata(self):
        """保存 metadata.json"""
        try:
            with open(METADATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.metadata, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            self.set_status(f"保存失败: {e}")
            return False

    def refresh_list(self):
        """刷新左侧列表（全量重建，倒序：最新的在最上面）"""
        self.tree.delete(*self.tree.get_children())
        for item in reversed(self.metadata):
            tags_str = self.tags_to_flat_string(item)
            self.tree.insert('', tk.END, iid=item['id'], values=(item.get('name', ''), tags_str))

    def update_single_row(self, item_id):
        """仅更新指定条目对应的一行，避免全量重建造成卡顿"""
        item = next((m for m in self.metadata if m['id'] == item_id), None)
        if not item:
            return
        tags_str = self.tags_to_flat_string(item)
        try:
            self.tree.item(item_id)
            self.tree.item(item_id, values=(item.get('name', ''), tags_str))
        except Exception:
            self.tree.insert('', 0, iid=item_id, values=(item.get('name', ''), tags_str))
            self.tree.see(item_id)

    def on_select(self, event):
        """选中列表项时加载到编辑区"""
        selection = self.tree.selection()
        if not selection:
            return
        item_id = selection[0]
        item = next((m for m in self.metadata if m['id'] == item_id), None)
        if not item:
            return

        self.current_id = item_id
        self.id_var.set(item.get('id', ''))
        self.name_var.set(item.get('name', ''))
        self.load_tags_to_fields(item)
        self.svg_file_var.set(item.get('svgFile', ''))
        self.original_image_var.set(item.get('originalImage') or '')
        self.desc_text.delete('1.0', tk.END)
        self.desc_text.insert('1.0', item.get('description', ''))
        self.update_preview()

    # ========== 增删改 ==========
    def new_item(self):
        """新建条目"""
        self.tree.selection_remove(*self.tree.selection())
        self.current_id = None
        self.id_var.set('(新建 - 保存时自动生成)')
        self.name_var.set('')
        for cat in TAG_CATEGORY_ORDER:
            var = self.tag_category_vars.get(cat)
            if var:
                var.set('')
        self.svg_file_var.set('')
        self.original_image_var.set('')
        self.desc_text.delete('1.0', tk.END)
        self.preview_canvas.delete('all')
        self.set_status("新建条目")

    def save_item(self):
        """保存当前编辑的条目"""
        name = self.name_var.get().strip()
        if not name:
            self.set_status("提示: 请输入名称")
            return

        tags_categorized = self.collect_tags_from_fields()
        tags_flat = []
        for cat in TAG_CATEGORY_ORDER:
            tags_flat.extend(tags_categorized.get(cat, []))
        svg_file = self.svg_file_var.get().strip()
        if not svg_file:
            self.set_status("提示: 请选择 SVG 文件")
            return

        original_image = self.original_image_var.get().strip() or None
        description = self.desc_text.get('1.0', tk.END).rstrip('\n')

        # 生成ID
        if self.current_id:
            item_id = self.current_id
        else:
            item_id = self.generate_id(name)
            existing_ids = {m['id'] for m in self.metadata}
            if item_id in existing_ids:
                item_id = f"{item_id}-{datetime.now().strftime('%H%M%S')}"

        # 自动将 SVG 文件重命名为 {id}.svg
        new_svg_file = f"{item_id}.svg"
        if svg_file != new_svg_file:
            for m in self.metadata:
                if m.get('svgFile') == new_svg_file and m.get('id') != self.current_id:
                    self.set_status(f"错误: 文件名 {new_svg_file} 已被其他条目占用")
                    return
            src_path = os.path.join(SVG_DIR, svg_file)
            dest_path = os.path.join(SVG_DIR, new_svg_file)
            if os.path.exists(src_path):
                try:
                    os.replace(src_path, dest_path)
                except Exception as e:
                    self.set_status(f"重命名失败: {e}")
                    return
            svg_file = new_svg_file
            self.svg_file_var.set(svg_file)

        item_data = {
            'id': item_id,
            'name': name,
            'tags': tags_categorized,
            'tags_flat': tags_flat,
            'svgFile': svg_file,
            'originalImage': original_image,
            'description': description
        }

        if self.current_id:
            for i, m in enumerate(self.metadata):
                if m['id'] == self.current_id:
                    self.metadata[i] = item_data
                    break
        else:
            self.metadata.append(item_data)
            self.current_id = item_id

        if self.save_metadata():
            self.update_single_row(item_id)
            self.tree.selection_set(item_id)
            self.set_status(f"保存成功: {name} (id={item_id})")

    def delete_item(self):
        """删除当前条目"""
        if not self.current_id:
            self.set_status("提示: 请先选择要删除的条目")
            return

        result = messagebox.askyesno("确认删除", f"确定删除 \"{self.name_var.get()}\" 吗？")
        if not result:
            return

        self.metadata = [m for m in self.metadata if m['id'] != self.current_id]
        if self.save_metadata():
            self.refresh_list()
            self.new_item()
            self.set_status("已删除")

    # ========== 文件选择 ==========
    def choose_svg(self):
        filepath = filedialog.askopenfilename(
            title="选择 SVG 文件",
            filetypes=[("SVG 文件", "*.svg"), ("所有文件", "*.*")],
            initialdir=SVG_DIR
        )
        if filepath:
            # 用 abspath 规范化后比较，避免分隔符/大小写差异导致误判
            if os.path.abspath(os.path.dirname(filepath)) == os.path.abspath(SVG_DIR):
                self.svg_file_var.set(os.path.basename(filepath))
                self.set_status(f"已选择 SVG: {os.path.basename(filepath)}")
            else:
                self.svg_file_var.set(os.path.basename(filepath))
                # 提示导入
                self.import_svg_from(filepath)
                #if messagebox.askyesno("导入", "该文件不在 svg 目录中，是否导入？"):
                    

    def import_svg(self):
        """从选择的文件导入SVG到svg目录"""
        filepath = filedialog.askopenfilename(
            title="选择要导入的 SVG 文件",
            filetypes=[("SVG 文件", "*.svg")],
        )
        if filepath:
            self.import_svg_from(filepath)

    def import_svg_from(self, filepath):
        filename = os.path.basename(filepath)
        dest = os.path.join(SVG_DIR, filename)
        if os.path.abspath(filepath) != os.path.abspath(dest):
            shutil.copy2(filepath, dest)
        self.svg_file_var.set(filename)
        self.set_status(f"已导入 SVG: {filename}")

    def choose_original(self):
        filepath = filedialog.askopenfilename(
            title="选择原始图片",
            filetypes=[("图片文件", "*.jpg *.jpeg *.webp *.png"), ("所有文件", "*.*")],
            initialdir=ORIGINALS_DIR
        )
        if filepath:
            # 用 abspath 规范化后比较，避免分隔符/大小写差异导致误判
            if os.path.abspath(os.path.dirname(filepath)) == os.path.abspath(ORIGINALS_DIR):
                self.original_image_var.set(os.path.basename(filepath))
                self.set_status(f"已选择原始图片: {os.path.basename(filepath)}")
            else:
                self.original_image_var.set(os.path.basename(filepath))
                self.import_original_from(filepath)
                #if messagebox.askyesno("导入", "该文件不在 originals 目录中，是否导入？"):
                    

    def import_original(self):
        filepath = filedialog.askopenfilename(
            title="选择要导入的原始图片",
            filetypes=[("图片文件", "*.jpg *.jpeg *.webp *.png")],
        )
        if filepath:
            self.import_original_from(filepath)

    def import_original_from(self, filepath):
        filename = os.path.basename(filepath)
        dest = os.path.join(ORIGINALS_DIR, filename)
        if os.path.abspath(filepath) != os.path.abspath(dest):
            shutil.copy2(filepath, dest)
        self.original_image_var.set(filename)
        self.set_status(f"已导入原始图片: {filename}")

    def clear_original(self):
        self.original_image_var.set('')

    # ========== 预览 ==========
    def update_preview(self):
        """更新SVG预览（异步渲染，避免复杂 SVG 阻塞 UI）"""
        svg_file = self.svg_file_var.get().strip()

        # SVG 文件名未变则跳过，避免保存后重复加载
        if svg_file and self._preview_cache_key and self._preview_cache_key[0] == svg_file:
            cache_mtime = self._preview_cache_key[1]
            filepath_check = os.path.join(SVG_DIR, svg_file)
            try:
                if os.path.exists(filepath_check) and os.path.getmtime(filepath_check) == cache_mtime:
                    if hasattr(self, 'preview_photo') and self.preview_photo:
                        # 命中缓存，仅重绘（Canvas 可能已被清空）
                        self._redraw_cached(svg_file)
                        return
            except Exception:
                pass

        # 取消上一个正在进行的渲染任务
        self._preview_token += 1
        token = self._preview_token

        self.preview_canvas.delete('all')
        if self._preview_loading_id:
            self._preview_loading_id = None

        if not svg_file:
            self._preview_cache_key = None
            return

        filepath = os.path.join(SVG_DIR, svg_file)
        if not os.path.exists(filepath):
            self.preview_canvas.create_text(100, 75, text="文件不存在", fill='#ef4444')
            self._preview_cache_key = None
            return

        # 显示加载中提示
        canvas_w = self.preview_canvas.winfo_width() or 400
        canvas_h = self.preview_canvas.winfo_height() or 300
        self._preview_loading_id = self.preview_canvas.create_text(
            canvas_w // 2, canvas_h // 2,
            text="加载中...",
            fill='#64748b',
            font=('Segoe UI', 10)
        )

        # 启动后台线程执行昂贵的 cairosvg 转换
        thread = threading.Thread(
            target=self._render_svg_async,
            args=(svg_file, filepath, token),
            daemon=True
        )
        self._preview_thread = thread
        thread.start()

    def _render_svg_async(self, svg_file, filepath, token):
        """后台线程：执行 cairosvg 转换（耗时操作），完成后回主线程显示"""
        # 任务被取消（用户已切换到其他条目）
        if token != self._preview_token:
            return

        try:
            mtime = os.path.getmtime(filepath)
            cache_key = (svg_file, mtime)

            # 再次检查缓存（可能在排队期间已被其他任务渲染）
            if cache_key == self._preview_cache_key and hasattr(self, 'preview_photo') and self.preview_photo:
                self.root.after(0, lambda: self._on_render_done(svg_file, self.preview_photo, token))
                return

            with open(filepath, 'r', encoding='utf-8') as f:
                svg_content = f.read()

            png_data = cairosvg.svg2png(
                bytestring=svg_content.encode('utf-8'),
                scale=2.5,
                background_color='#ffffff'
            )
            img = Image.open(io.BytesIO(png_data))

            # 转换完成前再次检查令牌
            if token != self._preview_token:
                return

            self.root.after(0, lambda: self._on_render_done(svg_file, img, token, cache_key))
        except Exception as e:
            if token != self._preview_token:
                return
            err_text = str(e)[:100]
            self.root.after(0, lambda: self._on_render_error(err_text, token))

    def _on_render_done(self, svg_file, img_or_photo, token, cache_key=None):
        """主线程：显示渲染结果"""
        # 令牌不匹配说明用户已切换，丢弃此次结果
        if token != self._preview_token:
            return

        canvas_w = self.preview_canvas.winfo_width() or 400
        canvas_h = self.preview_canvas.winfo_height() or 300

        self.preview_canvas.delete('all')
        self._preview_loading_id = None

        # 若传入的是 PIL Image，需按画布缩放后转为 PhotoImage
        if isinstance(img_or_photo, Image.Image):
            img = img_or_photo
            if canvas_w > 80 and canvas_h > 120:
                ratio = min((canvas_w - 40) / img.width, (canvas_h - 110) / img.height)
                new_w = max(1, int(img.width * ratio))
                new_h = max(1, int(img.height * ratio))
                img = img.resize((new_w, new_h), Image.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            self.preview_photo = photo
            if cache_key:
                self._preview_cache_key = cache_key
        else:
            # 已是 PhotoImage（缓存命中）
            photo = img_or_photo

        self.preview_canvas.create_image(
            canvas_w // 2,
            (canvas_h - 70) // 2,
            image=photo,
            anchor='center'
        )
        self.preview_canvas.create_text(
            canvas_w // 2, canvas_h - 30,
            text=svg_file,
            fill='#1e293b',
            font=('Segoe UI', 9)
        )

    def _on_render_error(self, err_text, token):
        """主线程：显示渲染错误"""
        if token != self._preview_token:
            return
        self.preview_canvas.delete('all')
        self._preview_loading_id = None
        canvas_w = self.preview_canvas.winfo_width() or 400
        canvas_h = self.preview_canvas.winfo_height() or 300
        self.preview_canvas.create_text(
            canvas_w // 2, canvas_h // 2,
            text=f"SVG 渲染失败\n{err_text}",
            fill='#ef4444',
            justify='center',
            width=280
        )

    def _redraw_cached(self, svg_file):
        """缓存命中时仅重绘 Canvas，不重新渲染"""
        if not hasattr(self, 'preview_photo') or not self.preview_photo:
            return
        canvas_w = self.preview_canvas.winfo_width() or 400
        canvas_h = self.preview_canvas.winfo_height() or 300
        self.preview_canvas.delete('all')
        self._preview_loading_id = None
        self.preview_canvas.create_image(
            canvas_w // 2,
            (canvas_h - 70) // 2,
            image=self.preview_photo,
            anchor='center'
        )
        self.preview_canvas.create_text(
            canvas_w // 2, canvas_h - 30,
            text=svg_file,
            fill='#1e293b',
            font=('Segoe UI', 9)
        )

    # ========== 生成数据 ==========
    def generate_data(self):
        """运行 generate.js 生成 images.json"""
        self.set_status("正在生成数据...")
        self.root.update()

        try:
            result = subprocess.run(
                ['node', GENERATE_SCRIPT],
                capture_output=True,
                text=True,
                cwd=PROJECT_ROOT,
                encoding='utf-8'
            )
            if result.returncode == 0:
                # 从 stdout 提取摘要行（如 "成功生成 N 张图片..."），避免长文本塞满状态栏
                summary = ''
                for line in result.stdout.strip().splitlines():
                    if line.startswith('成功生成'):
                        summary = line
                        break
                self.set_status(summary or "数据生成成功")
            else:
                err = (result.stderr or result.stdout or '').strip().splitlines()
                self.set_status(f"生成失败: {err[-1] if err else '未知错误'}")
        except FileNotFoundError:
            self.set_status("错误: 未找到 Node.js，请确保已安装并在 PATH 中")
        except Exception as e:
            self.set_status(f"错误: {e}")

    # ========== GitHub 同步 ==========
    def sync_github(self):
        """一键同步至 GitHub: 生成数据 -> git add -> git commit -> git push"""
        # result = messagebox.askyesno("确认同步", "将执行：生成数据 → git add → git commit → git push\n确认继续？")
        # if not result:
        #     return

        self.set_status("开始同步...")
        # 在后台线程执行
        thread = threading.Thread(target=self._do_sync, daemon=True)
        thread.start()

    def _do_sync(self):
        steps = [
            ("同步: 生成数据...", lambda: subprocess.run(
                ['node', GENERATE_SCRIPT], capture_output=True, text=True,
                cwd=PROJECT_ROOT, encoding='utf-8'
            )),
            ("同步: Git add...", lambda: subprocess.run(
                ['git', 'add', '.'], capture_output=True, text=True,
                cwd=PROJECT_ROOT, encoding='utf-8'
            )),
        ]

        commit_msg = f"Update gallery - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        steps.append((
            "同步: Git commit...",
            lambda: subprocess.run(
                ['git', 'commit', '-m', commit_msg], capture_output=True, text=True,
                cwd=PROJECT_ROOT, encoding='utf-8'
            )
        ))
        steps.append((
            "同步: Git push...",
            lambda: subprocess.run(
                ['git', 'push'], capture_output=True, text=True,
                cwd=PROJECT_ROOT, encoding='utf-8'
            )
        ))

        for label, cmd in steps:
            self.set_status(label)
            try:
                result = cmd()
                if result.returncode != 0:
                    # git commit 在没有变更时返回非0，这是正常的
                    if 'commit' in label and 'nothing to commit' in (result.stdout + result.stderr):
                        continue
                    err = (result.stderr or result.stdout or '').strip().splitlines()
                    self.set_status(f"同步失败: {err[-1] if err else '未知错误'}")
                    return
            except FileNotFoundError as e:
                self.set_status(f"同步失败: 命令未找到 - {e}")
                return
            except Exception as e:
                self.set_status(f"同步失败: {e}")
                return

        self.set_status("同步完成！已推送至 GitHub")

    # ========== 工具方法 ==========
    def generate_id(self, name):
        """根据名称生成 ID（保留中文、字母、数字，其他字符替换为 -）"""
        # 保留中文字符（\u4e00-\u9fff）、字母、数字，其他字符替换为 -
        id_str = re.sub(r'[^\u4e00-\u9fffa-zA-Z0-9]', '-', name.lower())
        id_str = re.sub(r'-+', '-', id_str).strip('-')
        # 名称全是特殊字符时，用时间戳作后备，避免重复生成 item
        if not id_str:
            id_str = f"item-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        return id_str

    def set_status(self, msg):
        """更新状态栏"""
        self.status_var.set(msg)
        self.root.update_idletasks()


def main():
    root = tk.Tk()
    app = SvgGalleryAdmin(root)
    root.mainloop()


if __name__ == '__main__':
    main()
