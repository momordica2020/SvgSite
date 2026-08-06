import re
import html
from collections import Counter


def analyze_file(filepath):
    print("=" * 80)
    print(f"分析文件: {filepath}")
    print("=" * 80)

    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    except Exception as e:
        print(f"读取文件失败: {e}")
        return

    img_tag_pattern = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
    img_tags = img_tag_pattern.findall(content)

    print(f"共找到 {len(img_tags)} 个 <img> 标签")
    print()

    src_pattern = re.compile(
        r"src\s*=\s*(\".*?\"|'.*?'|[^'\"\s>]+)",
        re.IGNORECASE | re.DOTALL,
    )

    total = len(img_tags)
    display_count = min(total, 10)
    print(f"前 {display_count} 个 <img> 标签详情：")
    print("-" * 80)

    src_quote_counter = Counter()
    other_attr_quote_counter = Counter()
    overall_tag_pattern = Counter()

    for i, tag in enumerate(img_tags[:display_count], 1):
        print(f"\n[{i}/{total}] 标签内容:")
        print(f"  原始标签: {tag}")

        src_match = src_pattern.search(tag)
        if src_match:
            src_raw = src_match.group(1)
            if src_raw.startswith('"') and src_raw.endswith('"'):
                src_quote_type = "双引号"
                src_value = src_raw[1:-1]
            elif src_raw.startswith("'") and src_raw.endswith("'"):
                src_quote_type = "单引号"
                src_value = src_raw[1:-1]
            else:
                src_quote_type = "无引号"
                src_value = src_raw

            print(f"  src引号类型: {src_quote_type}")
            print(f"  src值: {src_value}")
        else:
            src_quote_type = "无src属性"
            src_value = ""
            print("  未找到 src 属性")

        attr_pattern = re.compile(
            r"([a-zA-Z_:][a-zA-Z0-9_:.-]*)\s*=\s*(\".*?\"|'.*?'|[^'\"\s>]+)",
            re.DOTALL,
        )
        attrs = attr_pattern.findall(tag)

        tag_quote_signature = []
        for attr_name, attr_value in attrs:
            if attr_name.lower() == "src":
                continue

            if attr_value.startswith('"') and attr_value.endswith('"'):
                qtype = "双引号"
            elif attr_value.startswith("'") and attr_value.endswith("'"):
                qtype = "单引号"
            else:
                qtype = "无引号"

            other_attr_quote_counter[qtype] += 1
            tag_quote_signature.append(f"{attr_name.lower()}:{qtype}")

        if tag_quote_signature:
            attrs_info = ", ".join(tag_quote_signature)
            print(f"  其他属性引号: {attrs_info}")
        else:
            print(f"  其他属性引号: 无其他带值属性")

    print()
    print("=" * 80)
    print("统计汇总")
    print("=" * 80)

    for i, tag in enumerate(img_tags, 1):
        src_match = src_pattern.search(tag)
        if src_match:
            src_raw = src_match.group(1)
            if src_raw.startswith('"') and src_raw.endswith('"'):
                src_quote_type = "双引号"
            elif src_raw.startswith("'") and src_raw.endswith("'"):
                src_quote_type = "单引号"
            else:
                src_quote_type = "无引号"
        else:
            src_quote_type = "无src属性"

        src_quote_counter[src_quote_type] += 1

        attr_pattern_2 = re.compile(
            r"([a-zA-Z_:][a-zA-Z0-9_:.-]*)\s*=\s*(\".*?\"|'.*?'|[^'\"\s>]+)",
            re.DOTALL,
        )
        attrs_2 = attr_pattern_2.findall(tag)

        tag_pattern_parts = [f"src:{src_quote_type}"]
        for attr_name, attr_value in attrs_2:
            if attr_name.lower() == "src":
                continue

            if attr_value.startswith('"') and attr_value.endswith('"'):
                qtype = "双引号"
            elif attr_value.startswith("'") and attr_value.endswith("'"):
                qtype = "单引号"
            else:
                qtype = "无引号"

            other_attr_quote_counter[qtype] += 1
            tag_pattern_parts.append(f"{attr_name.lower()}:{qtype}")

        overall_tag_pattern[" | ".join(sorted(tag_pattern_parts))] += 1

    print(f"\n【src 属性引号情况统计】")
    for k in ["双引号", "单引号", "无引号", "无src属性"]:
        if k in src_quote_counter:
            print(f"  {k}: {src_quote_counter[k]} 个")

    print(f"\n【其他属性引号情况统计】")
    for k in ["双引号", "单引号", "无引号"]:
        if k in other_attr_quote_counter:
            print(f"  {k}: {other_attr_quote_counter[k]} 个")
        else:
            print(f"  {k}: 0 个")

    print(f"\n【标签写法模式统计（Top 10）】")
    sorted_patterns = sorted(
        overall_tag_pattern.items(), key=lambda x: x[1], reverse=True
    )
    for idx, (pattern, count) in enumerate(sorted_patterns[:10], 1):
        print(f"  {idx}. [{count} 次] {pattern}")

    return img_tags


if __name__ == "__main__":
    base_dir = r"d:\Projects\SvgSite\fotw\flags"
    files = [
        f"{base_dir}\\ag^.html",
        f"{base_dir}\\af^.html",
    ]

    for f in files:
        analyze_file(f)
        print("\n\n")
