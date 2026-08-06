import re, sys
from pathlib import Path

path = Path("scripts/parse_data_v4.py")
content = path.read_text(encoding="utf-8")

# 1. Replace the image extraction in quick_parse_header
old_img_block = '    # \u63d0\u53d6\u7b2c\u4e00\u5f20\u6709\u6548\u65d7\u5e1c\u56fe\u7247\r\n    letter = code[0].lower() if code else "a"\r\n    # \u5148\u5c1d\u8bd5\u9ed8\u8ba4\u8def\u5f84\r\n    default_path = f"images/{letter}/{code}.gif"\r\n    # \u627e\u6240\u6709img\r\n    first_img = ""\r\n    for m in re.finditer(r''<img\s[^>]*src="([^"]+)"[^>]*>'', content, re.I):\r\n        src = normalize_img_src(m.group(1))\r\n        if src and not is_image_skippable(src):\r\n            first_img = src\r\n            break\r\n    result["main_image"] = first_img or default_path'
)