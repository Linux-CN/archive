 
import os
import re
import argparse
import concurrent.futures
import time


def process_file(filepath, cdn_base_url):
    """处理单个Markdown文件"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 编译正则表达式：匹配Markdown中的图片路径
    pattern = re.compile(
        r'('
        r'(!\[[^\]]*\]\()'  # 标准Markdown图片语法
        r'|'  # 或
        r'(\n\s*[a-zA-Z0-9_-]+\s*:)'  # YAML front matter键值对
        r')'
        r'(/data/(?:attachment/album|img)/[^\)\s]+)'  # 图片路径
    )

    replacements = []
    new_content = content

    # 查找所有匹配项
    matches = list(pattern.finditer(content))
    if not matches:
        return 0

    # 构建替换列表
    for match in matches:
        old_path = match.group(4)
        new_path = f"{cdn_base_url}{old_path}"
        replacements.append((old_path, new_path))

    # 一次性替换所有匹配项（反向替换避免索引偏移）
    for old_path, new_path in reversed(replacements):
        new_content = new_content.replace(old_path, new_path)

    # 写回文件
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)

    return len(replacements)


def replace_md_image_paths(directory, cdn_base_url, workers=8):
    """
    递归遍历目录，替换Markdown文件中的本地图片路径为CDN路径
    :param directory: 要遍历的目录路径
    :param cdn_base_url: CDN基础URL
    :param workers: 并行处理线程数
    """
    cdn_base_url = cdn_base_url.rstrip('/')
    file_queue = []
    total_files = 0
    total_replacements = 0

    # 收集所有需要处理的文件
    for root, _, files in os.walk(directory):
        for filename in files:
            if filename.lower().endswith('.md'):
                filepath = os.path.join(root, filename)
                file_queue.append(filepath)
                total_files += 1

    print(f"k开始处理: 共发现 {total_files} 个Markdown文件")
    start_time = time.time()

    # 使用线程池并行处理
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(process_file, fp, cdn_base_url): fp for fp in file_queue}

        for i, future in enumerate(concurrent.futures.as_completed(futures), 1):
            filepath = futures[future]
            try:
                replacements = future.result()
                if replacements > 0:
                    print(f"处理进度: {i}/{total_files} | 文件: {filepath} | 替换: {replacements}处")
                    total_replacements += replacements
            except Exception as e:
                print(f"\033[31m处理失败: {filepath} | 错误: {str(e)}\033[0m")

    elapsed = time.time() - start_time
    print(f"\n\033[1;32m处理完成! 共处理 {total_files} 个文件, 执行 {total_replacements} 次替换")
    print(f"总耗时: {elapsed:.2f}秒 | 平均速度: {total_files / elapsed:.1f} 文件/秒\033[0m")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='替换Markdown中的本地图片路径为CDN路径')
    parser.add_argument('directory', help='包含Markdown文件的根目录')
    parser.add_argument('cdn_url', help='CDN基础URL（如https://cdn.example.com）')
    parser.add_argument('--workers', type=int, default=8, help='并行处理线程数（默认是8）')
    args = parser.parse_args()

    replace_md_image_paths(args.directory, args.cdn_url, args.workers)
