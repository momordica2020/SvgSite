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
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPM

# 项目根目录（admin 的上级目录）
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SVG_DIR = os.path.join(PROJECT_ROOT, 'svg')
ORIGINALS_DIR = os.path.join(PROJECT_ROOT, 'originals')
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
METADATA_FILE = os.path.join(DATA_DIR, 'metadata.json')
GENERATE_SCRIPT = os.path.join(PROJECT_ROOT, 'scripts', 'generate.js')


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

        # 标签
        ttk.Label(parent, text="标签 (逗号分隔):").grid(row=2, column=0, sticky=tk.W, pady=4)
        self.tags_var = tk.StringVar()
        ttk.Entry(parent, textvariable=self.tags_var, width=40).grid(row=2, column=1, sticky=tk.EW, pady=4)

        # SVG文件
        ttk.Label(parent, text="SVG 文件:").grid(row=3, column=0, sticky=tk.W, pady=4)
        svg_frame = ttk.Frame(parent)
        svg_frame.grid(row=3, column=1, sticky=tk.EW, pady=4)
        self.svg_file_var = tk.StringVar()
        ttk.Entry(svg_frame, textvariable=self.svg_file_var, width=30).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(svg_frame, text="选择...", command=self.choose_svg).pack(side=tk.LEFT, padx=4)
        ttk.Button(svg_frame, text="导入", command=self.import_svg).pack(side=tk.LEFT)

        # 原始图片
        ttk.Label(parent, text="原始图片:").grid(row=4, column=0, sticky=tk.W, pady=4)
        orig_frame = ttk.Frame(parent)
        orig_frame.grid(row=4, column=1, sticky=tk.EW, pady=4)
        self.original_image_var = tk.StringVar()
        ttk.Entry(orig_frame, textvariable=self.original_image_var, width=30).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(orig_frame, text="选择...", command=self.choose_original).pack(side=tk.LEFT, padx=4)
        ttk.Button(orig_frame, text="导入", command=self.import_original).pack(side=tk.LEFT)
        ttk.Button(orig_frame, text="清除", command=self.clear_original).pack(side=tk.LEFT, padx=4)

        # SVG预览
        ttk.Label(parent, text="SVG 预览:").grid(row=5, column=0, sticky=tk.NW, pady=4)
        preview_frame = ttk.Frame(parent, relief=tk.SUNKEN, borderwidth=1)
        preview_frame.grid(row=5, column=1, sticky=tk.NSEW, pady=4)
        self.preview_canvas = tk.Canvas(preview_frame, width=400, height=300, bg='#f1f5f9')
        self.preview_canvas.pack(fill=tk.BOTH, expand=True)

        # 描述
        ttk.Label(parent, text="Markdown 描述:").grid(row=6, column=0, sticky=tk.NW, pady=4)
        self.desc_text = ScrolledText(parent, width=50, height=12, font=('Consolas', 10))
        self.desc_text.grid(row=6, column=1, sticky=tk.NSEW, pady=4)

        parent.columnconfigure(1, weight=1)
        parent.rowconfigure(6, weight=1)

        # 绑定变化时刷新预览
        self.svg_file_var.trace_add('write', lambda *_: self.update_preview())

    # ========== 目录管理 ==========
    def ensure_dirs(self):
        for d in [SVG_DIR, ORIGINALS_DIR, DATA_DIR]:
            os.makedirs(d, exist_ok=True)

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
                messagebox.showerror("错误", f"读取 metadata.json 失败:\n{e}")
                self.metadata = []

        self.refresh_list()
        self.set_status(f"已加载 {len(self.metadata)} 条记录")

    def save_metadata(self):
        """保存 metadata.json"""
        try:
            with open(METADATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.metadata, f, ensure_ascii=False, indent=2)
            self.set_status("metadata.json 已保存")
            return True
        except Exception as e:
            messagebox.showerror("保存失败", str(e))
            return False

    def refresh_list(self):
        """刷新左侧列表"""
        self.tree.delete(*self.tree.get_children())
        for item in self.metadata:
            tags_str = ', '.join(item.get('tags', []))
            self.tree.insert('', tk.END, iid=item['id'], values=(item.get('name', ''), tags_str))

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
        self.tags_var.set(', '.join(item.get('tags', [])))
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
        self.tags_var.set('')
        self.svg_file_var.set('')
        self.original_image_var.set('')
        self.desc_text.delete('1.0', tk.END)
        self.preview_canvas.delete('all')
        self.set_status("新建条目")

    def save_item(self):
        """保存当前编辑的条目"""
        name = self.name_var.get().strip()
        if not name:
            messagebox.showwarning("提示", "请输入名称")
            return

        tags_raw = self.tags_var.get().strip()
        #tags = [t.strip() for t in tags_raw.split(',') if t.strip()] if tags_raw else []
        tags = [t.strip() for t in re.split(r'[,，]', tags_raw) if t.strip()] if tags_raw else []
        svg_file = self.svg_file_var.get().strip()
        if not svg_file:
            messagebox.showwarning("提示", "请选择 SVG 文件")
            return

        original_image = self.original_image_var.get().strip() or None
        description = self.desc_text.get('1.0', tk.END).rstrip('\n')

        # 生成ID
        if self.current_id:
            item_id = self.current_id
        else:
            item_id = self.generate_id(name)
            # 检查ID是否已存在
            existing_ids = {m['id'] for m in self.metadata}
            if item_id in existing_ids:
                item_id = f"{item_id}-{datetime.now().strftime('%H%M%S')}"

        # 自动将 SVG 文件重命名为 {id}.svg
        new_svg_file = f"{item_id}.svg"
        if svg_file != new_svg_file:
            # 检查目标文件名是否被其他条目占用
            for m in self.metadata:
                if m.get('svgFile') == new_svg_file and m.get('id') != self.current_id:
                    messagebox.showerror("错误", f"文件名 {new_svg_file} 已被其他条目占用")
                    return
            src_path = os.path.join(SVG_DIR, svg_file)
            dest_path = os.path.join(SVG_DIR, new_svg_file)
            if os.path.exists(src_path):
                try:
                    os.replace(src_path, dest_path)
                except Exception as e:
                    messagebox.showerror("重命名失败", str(e))
                    return
            # 无论源文件是否存在，都同步字段为规范的 {id}.svg
            svg_file = new_svg_file
            self.svg_file_var.set(svg_file)

        item_data = {
            'id': item_id,
            'name': name,
            'tags': tags,
            'svgFile': svg_file,
            'originalImage': original_image,
            'description': description
        }

        if self.current_id:
            # 更新已有
            for i, m in enumerate(self.metadata):
                if m['id'] == self.current_id:
                    self.metadata[i] = item_data
                    break
        else:
            # 新建
            self.metadata.append(item_data)
            self.current_id = item_id

        if self.save_metadata():
            self.refresh_list()
            self.tree.selection_set(item_id)
            messagebox.showinfo("成功", "保存成功！")

    def delete_item(self):
        """删除当前条目"""
        if not self.current_id:
            messagebox.showwarning("提示", "请先选择要删除的条目")
            return

        result = messagebox.askyesno("确认", f"确定删除 \"{self.name_var.get()}\" 吗？\n\n（SVG文件和原始图片不会被删除，仅从元数据中移除）")
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
            # 如果文件在 svg 目录中，只取文件名
            if os.path.dirname(filepath) == SVG_DIR:
                self.svg_file_var.set(os.path.basename(filepath))
            else:
                self.svg_file_var.set(os.path.basename(filepath))
                # 提示导入
                if messagebox.askyesno("导入", "该文件不在 svg 目录中，是否导入？"):
                    self.import_svg_from(filepath)

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
            if os.path.dirname(filepath) == ORIGINALS_DIR:
                self.original_image_var.set(os.path.basename(filepath))
            else:
                self.original_image_var.set(os.path.basename(filepath))
                if messagebox.askyesno("导入", "该文件不在 originals 目录中，是否导入？"):
                    self.import_original_from(filepath)

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
        """更新SVG预览"""
        self.preview_canvas.delete('all')
    
        svg_file = self.svg_file_var.get().strip()
        if not svg_file:
            return

        filepath = os.path.join(SVG_DIR, svg_file)
        if not os.path.exists(filepath):
            self.preview_canvas.create_text(100, 75, text="文件不存在", fill='#ef4444')
            return

        try:
            # ====================== 修改这一行 ======================
            # 请把下面路径改成你电脑上 Inkscape 的实际路径
            inkscape_path = r"D:\Inkscape\bin\inkscape.com"
            # =====================================================

            if not os.path.exists(inkscape_path):
                self.preview_canvas.create_text(150, 80, 
                    text=f"Inkscape 未找到\n{inkscape_path}", fill='#ef4444', width=250)
                return

            # 临时 PNG 文件
            temp_png = filepath.replace('.svg', '_temp_preview.png')

            # 调用 Inkscape 转换
            result = subprocess.run([
                inkscape_path,
                filepath,
                "--export-type=png",
                f"--export-filename={temp_png}",
                "--export-width=900",           # 可调整清晰度
                "--export-background=#ffffff"
            ], check=True, timeout=10, 
            creationflags=subprocess.CREATE_NO_WINDOW)

            # 读取图片
            img = Image.open(temp_png)
            
            # 自适应画布大小
            canvas_w = self.preview_canvas.winfo_width() or 400
            canvas_h = self.preview_canvas.winfo_height() or 300
            
            if canvas_w > 100 and canvas_h > 120:
                ratio = min((canvas_w - 40) / img.width, (canvas_h - 120) / img.height)
                new_w = int(img.width * ratio)
                new_h = int(img.height * ratio)
                img = img.resize((new_w, new_h), Image.LANCZOS)

            self.preview_photo = ImageTk.PhotoImage(img)

            self.preview_canvas.create_image(canvas_w//2, (canvas_h-80)//2, 
                                        image=self.preview_photo, anchor='center')

            self.preview_canvas.create_text(canvas_w//2, canvas_h-35, 
                                        text=svg_file, fill='#1e293b', font=('Segoe UI', 9))

            # 清理临时文件
            try:
                os.remove(temp_png)
            except:
                pass
        except:
            pass

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
                self.set_status("数据生成成功")
                messagebox.showinfo("成功", f"数据生成成功！\n\n{result.stdout}")
            else:
                self.set_status("生成失败")
                messagebox.showerror("生成失败", result.stderr or result.stdout)
        except FileNotFoundError:
            messagebox.showerror("错误", "未找到 Node.js，请确保已安装 Node.js 并在 PATH 中")
            self.set_status("错误: 未找到 Node.js")
        except Exception as e:
            messagebox.showerror("错误", str(e))
            self.set_status(f"错误: {e}")

    # ========== GitHub 同步 ==========
    def sync_github(self):
        """一键同步至 GitHub: 生成数据 -> git add -> git commit -> git push"""
        result = messagebox.askyesno(
            "确认同步",
            "将执行以下操作:\n\n"
            "1. 生成数据 (node generate.js)\n"
            "2. git add .\n"
            "3. git commit\n"
            "4. git push\n\n"
            "确认继续？"
        )
        if not result:
            return

        # 在后台线程执行
        thread = threading.Thread(target=self._do_sync, daemon=True)
        thread.start()

    def _do_sync(self):
        steps = [
            ("生成数据...", lambda: subprocess.run(
                ['node', GENERATE_SCRIPT], capture_output=True, text=True,
                cwd=PROJECT_ROOT, encoding='utf-8'
            )),
            ("Git add...", lambda: subprocess.run(
                ['git', 'add', '.'], capture_output=True, text=True,
                cwd=PROJECT_ROOT, encoding='utf-8'
            )),
        ]

        commit_msg = f"Update gallery - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        steps.append((
            "Git commit...",
            lambda: subprocess.run(
                ['git', 'commit', '-m', commit_msg], capture_output=True, text=True,
                cwd=PROJECT_ROOT, encoding='utf-8'
            )
        ))
        steps.append((
            "Git push...",
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
                    error_msg = result.stderr or result.stdout
                    self.root.after(0, lambda msg=error_msg: messagebox.showerror("同步失败", msg))
                    self.set_status("同步失败")
                    return
            except FileNotFoundError as e:
                self.root.after(0, lambda msg=str(e): messagebox.showerror("错误", f"命令未找到: {msg}"))
                self.set_status("同步失败")
                return
            except Exception as e:
                self.root.after(0, lambda msg=str(e): messagebox.showerror("错误", msg))
                self.set_status("同步失败")
                return

        self.set_status("同步完成！")
        self.root.after(0, lambda: messagebox.showinfo("成功", "已成功同步至 GitHub！"))

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