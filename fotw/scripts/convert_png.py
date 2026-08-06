#!/usr/bin/env python3
"""批量将FOTW GIF转换为PNG"""
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
IMAGES_DIR = BASE_DIR / "images"
IMAGES_PNG_DIR = BASE_DIR / "images-png"

def main():
    try:
        from PIL import Image
    except ImportError:
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow"])
        from PIL import Image

    IMAGES_PNG_DIR.mkdir(parents=True, exist_ok=True)

    gif_files = list(IMAGES_DIR.rglob("*.gif"))
    total = len(gif_files)
    print(f"共 {total} 个GIF文件待转换")

    converted = 0
    skipped = 0
    errors = 0

    for i, gif_path in enumerate(gif_files):
        try:
            rel_path = gif_path.relative_to(IMAGES_DIR)
            png_path = IMAGES_PNG_DIR / rel_path.with_suffix('.png')
            png_path.parent.mkdir(parents=True, exist_ok=True)

            if png_path.exists():
                skipped += 1
            else:
                img = Image.open(str(gif_path))
                if img.mode in ('P', 'L', 'LA'):
                    img = img.convert('RGBA')
                elif img.mode == 'RGB':
                    img = img.convert('RGBA')
                img.save(str(png_path), 'PNG')
                converted += 1

            if (i + 1) % 10000 == 0:
                print(f"  进度: {i+1}/{total} (新增:{converted}, 跳过:{skipped}, 错误:{errors})")
        except Exception as e:
            errors += 1
            if errors <= 5:
                print(f"  [警告] {gif_path.name}: {e}")

    print(f"完成! 新增:{converted}, 跳过:{skipped}, 错误:{errors}")

if __name__ == "__main__":
    main()
