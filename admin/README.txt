SVG Gallery 管理工具
=====================

使用方法:
1. 确保已安装 Python 3.x (https://www.python.org/downloads/)
2. 确保已安装 Node.js (用于生成数据)
3. 双击 run.bat 启动，或命令行运行: python app.py

功能:
- 新建/编辑/删除图片元数据
- 导入SVG文件到 svg/ 目录
- 导入原始图片(jpg/webp)到 originals/ 目录
- 编辑Markdown格式的描述
- 一键生成网站数据 (运行 generate.js)
- 一键同步至GitHub (git add + commit + push)

数据文件:
- data/metadata.json - 元数据文件（本工具管理）
- data/images.json   - 网站数据文件（自动生成）

目录结构:
- svg/         - SVG矢量图文件
- originals/   - 原始来源图片(jpg/webp)
- data/        - 数据文件