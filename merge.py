import requests
import re
import os
from datetime import datetime

# 直播源配置
sources = [
    # 无#genre#的源 - 将自动放入IPTV分组
    ("中国", "https://raw.githubusercontent.com/iptv-org/iptv/refs/heads/master/streams/****3u"),
    ("TW", "https://raw.githubusercontent.com/iptv-org/iptv/refs/heads/master/streams/tw.m3u"),
    ("HK", "https://raw.githubusercontent.com/iptv-org/iptv/refs/heads/master/streams/hk.m3u"),
    ("漂亮国", "https://raw.githubusercontent.com/iptv-org/iptv/refs/heads/master/streams/us.m3u"),
    ("大毛子", "https://raw.githubusercontent.com/iptv-org/iptv/refs/heads/master/streams/ru.m3u"),
    ("大不列", "https://raw.githubusercontent.com/iptv-org/iptv/refs/heads/master/streams/uk_bbc.m3u"),
    ("小日子", "https://raw.githubusercontent.com/iptv-org/iptv/refs/heads/master/streams/jp.m3u"),
    ("samsung", "https://raw.githubusercontent.com/iptv-org/iptv/refs/heads/master/streams/uk_samsung.m3u"),
    
    # 其他正常源 - 按原有顺序放在最后
    ("先锋", "http://ge.html-5.me//ii/%E9%BB%84%E8%9A%82%E8%9A%81%E5%85%88%E9%94%8B%E6%8E%A8%E6%B5%81%E6%BA%90.txt"),
    ("iptvz", "https://raw.githubusercontent.com/q1017673817/iptvz/refs/heads/main/zubo_all.txt"),
    ("zbds", "https://live.zbds.org/tv/iptv4.txt"),
    ("咪咕", "https://raw.githubusercontent.com/develop202/migu_video/refs/heads/main/interface.txt"),
    ("Guovin", "https://raw.githubusercontent.com/Guovin/iptv-api/gd/output/result.txt"),
    ("alan", "https://raw.githubusercontent.com/alantang1977/aTV/refs/heads/master/output/result.txt"),
    ("YY", "https://raw.githubusercontent.com/mursor1985/LIVE/refs/heads/main/yylunbo.m3u"),
    ("虎牙", "https://raw.githubusercontent.com/mursor1985/LIVE/refs/heads/main/huyayqk.m3u"),
    ("斗鱼", "https://raw.githubusercontent.com/mursor1985/LIVE/refs/heads/main/douyuyqk.m3u")
]

# 蓝本文件地址（排在最前）
blueprint_url = "https://raw.githubusercontent.com/your-username/your-repo/main/zb.txt"

def fetch_url(url):
    """获取URL内容"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"获取URL失败: {url}, 错误: {e}")
        return ""

def has_genre(content):
    """检查内容是否包含#genre#标签"""
    return "#genre#" in content

def process_no_genre_source(name, content):
    """处理没有#genre#的源，将其放入IPTV分组"""
    lines = content.strip().split('\n')
    processed_lines = []
    
    # 跳过M3U头
    if lines and lines[0].startswith('#EXTM3U'):
        lines = lines[1:]
    
    # 添加IPTV分组头和当前源作为genre
    processed_lines.append(f"IPTV,#genre#")
    processed_lines.append(f"{name},#genre#")
    
    # 处理频道行
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # 跳过EXTINF行，只保留"频道名,URL"格式的行
        if line.startswith('#EXTINF'):
            continue
        # 如果是URL行，尝试提取频道名
        if line.startswith('http'):
            # 尝试从URL中提取频道名，或者使用默认名
            channel_name = f"{name}_频道_{len(processed_lines) - 2}"
            processed_lines.append(f"{channel_name},{line}")
        elif ',' in line and not line.endswith('#genre#'):
            # 已经是"频道名,URL"格式
            processed_lines.append(line)
    
    return '\n'.join(processed_lines) + '\n'

def process_normal_source(content):
    """处理正常的有#genre#的源"""
    lines = content.strip().split('\n')
    processed_lines = []
    
    # 跳过M3U头
    if lines and lines[0].startswith('#EXTM3U'):
        lines = lines[1:]
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # 跳过EXTINF行
        if line.startswith('#EXTINF'):
            continue
        processed_lines.append(line)
    
    return '\n'.join(processed_lines) + '\n'

def main():
    output = []
    
    # 1. 首先添加蓝本文件内容（排在最前）
    print("正在获取蓝本文件...")
    blueprint_content = fetch_url(blueprint_url)
    if blueprint_content:
        output.append(process_normal_source(blueprint_content))
        print("蓝本文件添加成功")
    
    # 2. 处理无#genre#的源，放入IPTV分组
    print("正在处理无#genre#的源...")
    iptv_group_content = []
    
    for name, url in sources:
        # 先检查是否是无#genre#的源（通过URL特征判断）
        # 或者直接获取内容后检查
        content = fetch_url(url)
        if not content:
            print(f"跳过源: {name}")
            continue
            
        if not has_genre(content):
            print(f"处理无#genre#源: {name}")
            processed = process_no_genre_source(name, content)
            iptv_group_content.append(processed)
        else:
            # 正常源暂时不处理，留到后面
            pass
    
    # 将所有无#genre#的源合并到IPTV分组
    if iptv_group_content:
        # 先添加IPTV分组头
        output.append("IPTV,#genre#\n")
        # 然后添加各个源的内容（每个源已经自带了自己的genre）
        for content in iptv_group_content:
            output.append(content)
        print("IPTV分组添加成功")
    
    # 3. 处理其他正常源（排在最后）
    print("正在处理其他正常源...")
    for name, url in sources:
        # 跳过已经处理过的无#genre#的源
        # 这里通过名称判断哪些是需要放在最后的正常源
        normal_source_names = ["先锋", "iptvz"]  # 在这里添加所有正常源的名称
        if name in normal_source_names:
            content = fetch_url(url)
            if content:
                print(f"处理正常源: {name}")
                processed = process_normal_source(content)
                output.append(processed)
    
    # 合并所有内容
    final_content = ''.join(output)
    
    # 添加更新时间
    update_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    final_content = f"# 更新时间: {update_time}\n" + final_content
    
    # 写入文件
    with open("live.txt", "w", encoding="utf-8") as f:
        f.write(final_content)
    
    # 同时生成M3U格式
    with open("live.m3u", "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        lines = final_content.split('\n')
        current_group = ""
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if line.endswith('#genre#'):
                current_group = line.split(',')[0]
                continue
            if ',' in line:
                name, url = line.split(',', 1)
                f.write(f'#EXTINF:-1 group-title="{current_group}",{name}\n')
                f.write(f"{url}\n")
    
    print(f"生成完成！共处理 {len(sources)} 个源")
    print(f"输出文件: live.txt, live.m3u")
    print(f"更新时间: {update_time}")

if __name__ == "__main__":
    main()
