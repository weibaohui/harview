import json
import sys
import os
import glob
from collections import defaultdict

def scan_har_files(directory):
    """
    扫描指定目录下的所有HAR文件
    """
    if not os.path.exists(directory):
        print(f"错误: 目录 '{directory}' 不存在")
        return []
    
    if not os.path.isdir(directory):
        print(f"错误: '{directory}' 不是一个目录")
        return []
    
    # 查找所有.har文件
    har_files = glob.glob(os.path.join(directory, "*.har"))
    
    if not har_files:
        print(f"警告: 目录 '{directory}' 中没有找到HAR文件")
        return []
    
    print(f"在目录 '{directory}' 中找到 {len(har_files)} 个HAR文件:")
    for file in har_files:
        print(f"  - {os.path.basename(file)}")
    
    return har_files

def analyze_har(folder_path, filter_assets=False):
    """
    分析文件夹中的所有HAR文件
    
    Args:
        folder_path: HAR文件夹路径
        filter_assets: 是否过滤CSS和JS文件
    """
    all_results = defaultdict(list)
    
    # 检查是否为文件夹
    if not os.path.isdir(folder_path):
        print(f"错误: '{folder_path}' 不是一个文件夹")
        return {}
    
    # 扫描文件夹中的所有HAR文件
    har_files = scan_har_files(folder_path)
    if not har_files:
        print(f"警告: 文件夹 '{folder_path}' 中没有找到HAR文件")
        return {}
    
    print(f"在 '{folder_path}' 中找到 {len(har_files)} 个HAR文件")
    
    # 处理所有HAR文件
    for har_file in har_files:
        try:
            with open(har_file, 'r', encoding='utf-8') as f:
                har = json.load(f)
            entries = har["log"]["entries"]

            for e in entries:
                url = e["request"]["url"]
                # 跳过WebSocket连接
                if url.startswith('wss://') or url.startswith('ws://'):
                    continue
                
                # 如果启用了资源过滤，跳过静态资源文件
                if filter_assets:
                    # 定义静态资源文件扩展名
                    static_extensions = [
                        '.css', '.js', '.svg', '.png', '.jpg', '.jpeg', '.gif', '.webp', '.ico',
                        '.woff', '.woff2', '.ttf', '.eot', '.otf',  # 字体文件
                        '.mp3', '.mp4', '.avi', '.mov', '.wmv', '.flv',  # 音视频文件
                        '.pdf', '.zip', '.rar', '.tar', '.gz'  # 文档和压缩文件
                    ]
                    
                    # 检查URL是否包含静态资源文件扩展名
                    is_static = False
                    for ext in static_extensions:
                        if (url.endswith(ext) or f'{ext}?' in url):
                            is_static = True
                            break
                    
                    # 检查URL路径是否包含静态资源目录
                    static_paths = ['/css/', '/js/', '/svg/', '/images/', '/img/', '/assets/', 
                                  '/static/', '/fonts/', '/media/', '_next/static']
                    for path in static_paths:
                        if path in url:
                            is_static = True
                            break
                    
                    if is_static:
                        continue
                
                time = e["time"]
                all_results[url].append(time)
                
        except Exception as e:
            print(f"警告: 无法处理文件 '{har_file}': {e}")
            continue

    # 计算每个URL的最大响应时间
    summary = {}
    for url, times in all_results.items():
        summary[url] = round(max(times), 2)
    
    return summary

def compare_performance(first_data, second_data, first_name="第一组", second_name="第二组"):
    """
    对比两组HAR数据的性能差异，以第一组为基准
    """
    comparison_results = []
    
    # 找到两组数据中相同的URL
    common_urls = set(first_data.keys()) & set(second_data.keys())
    
    for url in common_urls:
        first_max = first_data[url]  # 现在直接是最大时间值
        second_max = second_data[url]  # 现在直接是最大时间值
        
        # 计算差异
        time_diff = second_max - first_max
        if first_max > 0:
            percentage_diff = round((time_diff / first_max) * 100, 1)
        else:
            percentage_diff = 0
        
        comparison_results.append({
            'url': url,
            'first_avg': first_max,
            'second_avg': second_max,
            'time_diff': round(time_diff, 2),
            'percentage_diff': percentage_diff,
            'first_name': first_name,
            'second_name': second_name
        })
    
    # 按照时间差异排序（第二组比第一组慢的程度）
    comparison_results.sort(key=lambda x: x['time_diff'], reverse=True)
    
    return comparison_results

def analyze_slowest_urls(folder_data, folder_name, top_n=100):
    """
    分析最慢的URL
    """
    if not folder_data:
        print(f"文件夹 '{folder_name}' 中没有有效的数据")
        return []
    
    # 收集所有URL的性能数据
    url_performance = []
    for url, max_time in folder_data.items():
        url_performance.append({
            'url': url,
            'max_time': max_time
        })
    
    # 按最大响应时间降序排序
    url_performance.sort(key=lambda x: x['max_time'], reverse=True)
    
    return url_performance[:top_n]

def print_slowest_urls_analysis(slowest_urls, folder_name):
    """
    打印最慢URL分析结果
    """
    print("=" * 80)
    print(f"{folder_name} 文件夹最慢的前{len(slowest_urls)}个URL分析")
    print("=" * 80)
    
    if not slowest_urls:
        print("没有找到有效的URL数据")
        return
    
    print(f"\n共分析了 {len(slowest_urls)} 个URL\n")
    
    # 打印表头
    print(f"{'排名':<4} {'最大响应时间(ms)':<15} {'URL'}")
    print("-" * 80)
    
    # 打印前100个最慢的URL
    for i, url_data in enumerate(slowest_urls, 1):
        print(f"{i:<4} {url_data['max_time']:<15.2f} {url_data['url']}")
    
    # 统计信息
    max_response_time = max(url['max_time'] for url in slowest_urls)
    min_response_time = min(url['max_time'] for url in slowest_urls)
    
    print("\n" + "=" * 80)
    print("统计信息:")
    print(f"总URL数量: {len(slowest_urls)}")
    print(f"最慢URL: {slowest_urls[0]['url']} ({slowest_urls[0]['max_time']:.2f}ms)")
    if len(slowest_urls) > 1:
        print(f"最快URL: {slowest_urls[-1]['url']} ({slowest_urls[-1]['max_time']:.2f}ms)")
    print(f"最大响应时间: {max_response_time:.2f}ms")
    print(f"最小响应时间: {min_response_time:.2f}ms")


def print_usage():
    """打印使用说明"""
    print("HAR 文件夹性能分析工具")
    print("=" * 50)
    print()
    print("使用方法:")
    print("  python main.py <folder>                      # 分析单个文件夹中最慢的前100个URL")
    print("  python main.py <folder1> <folder2>           # 对比两个文件夹中的 HAR 文件")
    print("  python main.py --filter-assets <folder>      # 分析时过滤静态资源文件")
    print("  python main.py --filter-assets <folder1> <folder2>  # 对比时过滤静态资源文件")
    print("  python main.py --help                        # 显示此帮助信息")
    print()
    print("参数说明:")
    print("  --filter-assets    过滤静态资源文件，包括图片、CSS、JS、字体、音视频等，只分析API和页面请求")
    print()
    print("示例:")
    print("  python main.py cmcc-vpn                      # 分析 cmcc-vpn 文件夹中最慢的URL")
    print("  python main.py --filter-assets cmcc-vpn      # 分析时过滤静态资源文件")
    print("  python main.py vpn_folder direct_folder      # 对比两个文件夹")
    print("  python main.py --filter-assets scenario_a scenario_b  # 对比时过滤静态资源文件")
    print()
    print("功能说明:")
    print("  单文件夹分析模式:")
    print("    - 扫描指定文件夹中的所有 .har 文件")
    print("    - 分析所有URL的最大响应时间")
    print("    - 列出最慢的前100个URL及其详细统计信息")
    print("    - 显示最大/最小响应时间等统计数据")
    print()
    print("  文件夹对比模式:")
    print("    - 自动扫描两个文件夹中的所有 .har 文件")
    print("    - 自动匹配相同 URL 的请求进行性能对比分析")
    print("    - 输出详细的性能统计和对比结果")
    print("    - 支持自定义文件夹名称，结果中会显示实际的文件夹名称")
    print()
    print("  资源过滤功能:")
    print("    - 使用 --filter-assets 参数可过滤以下类型的静态资源文件:")
    print("      * 图片文件: .png, .jpg, .jpeg, .gif, .webp, .ico, .svg")
    print("      * 样式和脚本: .css, .js")
    print("      * 字体文件: .woff, .woff2, .ttf, .eot, .otf")
    print("      * 音视频文件: .mp3, .mp4, .avi, .mov, .wmv, .flv")
    print("      * 文档和压缩文件: .pdf, .zip, .rar, .tar, .gz")
    print("      * 静态资源目录: /css/, /js/, /images/, /img/, /assets/, /static/, /fonts/, /media/")
    print("      * 前端框架静态资源: _next/static 等")
    print("    - 过滤后只分析API接口和页面请求，更专注于业务逻辑性能")

# 解析命令行参数
def parse_arguments():
    """解析命令行参数"""
    args = sys.argv[1:]
    filter_assets = False
    folders = []
    
    # 检查是否有帮助参数
    if not args or args[0] in ["-h", "--help", "help"]:
        print_usage()
        sys.exit(0)
    
    # 解析参数
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--filter-assets":
            filter_assets = True
        elif not arg.startswith('-'):
            folders.append(arg)
        else:
            print(f"错误: 未知参数 '{arg}'")
            print_usage()
            sys.exit(1)
        i += 1
    
    return folders, filter_assets

# 检查命令行参数
folders, filter_assets = parse_arguments()

if len(folders) == 0:
    print("错误: 必须指定至少一个文件夹")
    print_usage()
    sys.exit(1)
elif len(folders) == 1:
    # 单文件夹分析模式
    folder_path = folders[0]
    
    # 检查路径是否存在且为文件夹
    if not os.path.exists(folder_path):
        print(f"错误: 路径 '{folder_path}' 不存在")
        sys.exit(1)
    if not os.path.isdir(folder_path):
        print(f"错误: '{folder_path}' 不是一个文件夹")
        sys.exit(1)
    
    # 提取文件夹名称用于显示
    folder_name = os.path.basename(folder_path.rstrip('/'))
        
    print(f"开始单文件夹性能分析:")
    print(f"分析文件夹: {folder_path} ({folder_name})")
    if filter_assets:
        print("已启用资源过滤: 将跳过图片、CSS、JS、字体、音视频等静态资源文件")
    print("-" * 50)
    
    folder_data = analyze_har(folder_path, filter_assets)
    
    if folder_data:
        slowest_urls = analyze_slowest_urls(folder_data, folder_name, 100)
        print_slowest_urls_analysis(slowest_urls, folder_name)
    else:
        print("没有找到有效的HAR文件数据")
    
    sys.exit(0)
    
elif len(folders) == 2:
    # 指定了两个文件夹参数，进行对比分析
    first_folder = folders[0]
    second_folder = folders[1]
    
    # 检查路径是否存在且为文件夹
    if not os.path.exists(first_folder):
        print(f"错误: 路径 '{first_folder}' 不存在")
        sys.exit(1)
    if not os.path.exists(second_folder):
        print(f"错误: 路径 '{second_folder}' 不存在")
        sys.exit(1)
    if not os.path.isdir(first_folder):
        print(f"错误: '{first_folder}' 不是一个文件夹")
        sys.exit(1)
    if not os.path.isdir(second_folder):
        print(f"错误: '{second_folder}' 不是一个文件夹")
        sys.exit(1)
    
    # 提取文件夹名称用于显示
    first_name = os.path.basename(first_folder.rstrip('/'))
    second_name = os.path.basename(second_folder.rstrip('/'))
        
    print(f"开始文件夹对比分析:")
    print(f"第一组文件夹: {first_folder} ({first_name})")
    print(f"第二组文件夹: {second_folder} ({second_name})")
    if filter_assets:
        print("已启用资源过滤: 将跳过图片、CSS、JS、字体、音视频等静态资源文件")
    print("-" * 50)
    
    first_data = analyze_har(first_folder, filter_assets)
    second_data = analyze_har(second_folder, filter_assets)

else:
    print(f"错误: 最多只能指定两个文件夹")
    print_usage()
    sys.exit(1)

# 进行对比分析
comparison_results = compare_performance(second_data, first_data, second_name, first_name)

print("=" * 80)
if comparison_results:
    first_name_display = comparison_results[0]['first_name']
    second_name_display = comparison_results[0]['second_name']
    print(f"{second_name_display} vs {first_name_display} 性能对比分析 (以{first_name_display}为基准)")
else:
    print("性能对比分析")
print("=" * 80)

if comparison_results:
    first_name_display = comparison_results[0]['first_name']
    second_name_display = comparison_results[0]['second_name']
    
    print(f"\n共找到 {len(comparison_results)} 个相同的URL进行对比\n")
    
    # 显示第二组比第一组慢最多的前100个URL
    print(f"{second_name_display}比{first_name_display}慢最多的前100个URL (最大响应时间对比):")
    print("-" * 80)
    print(f"{'排名':<4} {f'{first_name_display}最大(ms)':<15} {f'{second_name_display}最大(ms)':<15} {'差异(ms)':<10} {'差异(%)':<8} {'URL'}")
    print("-" * 80)
    
    for i, result in enumerate(comparison_results[:100]):
        print(f"{i+1:<4} {result['first_avg']:<15.2f} {result['second_avg']:<15.2f} "
              f"{result['time_diff']:<10} {result['percentage_diff']:>6}% {result['url']}")
    
    # 统计总体情况
    total_urls = len(comparison_results)
    slower_urls = len([r for r in comparison_results if r['time_diff'] > 0])
    faster_urls = len([r for r in comparison_results if r['time_diff'] < 0])
    same_urls = total_urls - slower_urls - faster_urls
    
    avg_time_diff = sum(r['time_diff'] for r in comparison_results) / total_urls
    avg_percentage_diff = sum(r['percentage_diff'] for r in comparison_results) / total_urls
    
    print("\n" + "=" * 80)
    print("总体统计:")
    print(f"{second_name_display}比{first_name_display}慢的URL数量: {slower_urls} ({slower_urls/total_urls*100:.1f}%)")
    print(f"{second_name_display}比{first_name_display}快的URL数量: {faster_urls} ({faster_urls/total_urls*100:.1f}%)")
    print(f"{second_name_display}与{first_name_display}相同的URL数量: {same_urls} ({same_urls/total_urls*100:.1f}%)")
    print(f"平均时间差异: {avg_time_diff:.2f}ms")
    print(f"平均性能差异: {avg_percentage_diff:.1f}%")
    
    if avg_time_diff > 0:
        print(f"\n结论: {second_name_display}最大响应时间平均比{first_name_display}慢 {avg_time_diff:.2f}ms ({avg_percentage_diff:.1f}%)")
    elif avg_time_diff < 0:
        print(f"\n结论: {second_name_display}最大响应时间平均比{first_name_display}快 {abs(avg_time_diff):.2f}ms ({abs(avg_percentage_diff):.1f}%)")
    else:
        print(f"\n结论: {second_name_display}与{first_name_display}最大响应时间基本相同")
        
else:
    print("没有找到相同的URL进行对比，请检查HAR文件是否包含相同的请求。")
