import requests
import time
import re

# ================ 🔧 配置区域 ================

# 1. 您的蓝本文件地址 (zb.txt)
MASTER_FILE_URL = "https://raw.githubusercontent.com/chenmo77/iptvindex/refs/heads/main/zb.txt"

# 2. 您自定义的其他直播源列表（已按您的要求填好）
CUSTOM_SOURCES = [
    ("IPV4", "https://live.hacks.tools/tv/iptv4.txt"),
    ("IPV6", "https://live.hacks.tools/tv/iptv6.txt"),
    ("IPHW", "https://live.hacks.tools/iptv/index.m3u"),
    ("咪咕", "https://raw.githubusercontent.com/develop202/migu_video/refs/heads/main/interface.txt"),
    ("Guovin", "https://raw.githubusercontent.com/Guovin/iptv-api/gd/output/result.txt"),
    ("h6room", "https://d.h6room.com/frjzb.txt"),
    ("zbds", "https://live.zbds.org/tv/iptv4.txt"),
    ("tv84", "https://raw.githubusercontent.com/cai23511/yex/master/TVlist/20210808384.m3u"),
    ("tv26", "https://raw.githubusercontent.com/cai23511/yex/master/TVlist/20210808226.m3u"),
    ("YY", "https://raw.githubusercontent.com/mursor1985/LIVE/refs/heads/main/yylunbo.m3u"),
    ("B站", "https://raw.githubusercontent.com/mursor1985/LIVE/refs/heads/main/bililive.m3u"),
    ("虎牙", "https://raw.githubusercontent.com/mursor1985/LIVE/refs/heads/main/huyayqk.m3u"),
    ("斗鱼", "https://raw.githubusercontent.com/mursor1985/LIVE/refs/heads/main/douyuyqk.m3u")
]

# 3. 输出文件
OUTPUT_FILE = "live.txt"

# =============================================

def fetch_file_content(url):
    """获取远程文件内容"""
    try:
        print(f"📡 正在抓取: {url}")
        response = requests.get(url, timeout=10)
        response.encoding = 'utf-8'
        return response.text
    except Exception as e:
        print(f"   ❌ 抓取失败: {e}")
        return None

def is_m3u_format(content):
    """判断内容是否为M3U格式（通过文件头或内容特征）"""
    first_line = content.strip().split('\n')[0] if content else ''
    if '#EXTM3U' in first_line:
        return True
    if '#EXTINF:' in content:
        return True
    return False

def parse_m3u_to_txt(content):
    """
    将M3U格式内容转换为TXT格式，并尝试从 group-title 提取分类
    """
    lines = content.split('\n')
    txt_lines = []
    current_genre = None
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        if '#EXTINF:' in line:
            group_match = re.search(r'group-title="([^"]+)"', line)
            if group_match:
                genre_name = group_match.group(1).strip()
                if genre_name and genre_name != current_genre:
                    current_genre = genre_name
                    txt_lines.append(f"{current_genre},#genre#")
            
            name_match = re.search(r',([^,]+)$', line)
            channel_name = name_match.group(1).strip() if name_match else ""
            
            if i + 1 < len(lines):
                channel_url = lines[i + 1].strip()
                if channel_url and not channel_url.startswith('#'):
                    txt_lines.append(f"{channel_name},{channel_url}")
            i += 2
        else:
            if line and not line.startswith('#EXTM3U'):
                txt_lines.append(line)
            i += 1
    
    return '\n'.join(txt_lines)

def convert_to_txt(content, url):
    """
    智能转换函数：判断内容格式，统一输出TXT
    """
    if '.m3u' in url.lower() or is_m3u_format(content):
        print(f"   📋 检测到M3U格式，正在智能转换（保留分类）...")
        return parse_m3u_to_txt(content)
    else:
        return content

def main():
    print("=" * 70)
    print("🚀 开始合并直播源（智能解析M3U分类）...")
    print("=" * 70)
    
    # 1. 获取蓝本文件
    master_content = fetch_file_content(MASTER_FILE_URL)
    if not master_content:
        print("❌ 无法获取蓝本文件，程序终止")
        return
    
    # 2. 构建最终文件内容
    final_lines = []
    lines = master_content.split('\n')
    
    custom_inserted = False
    
    for line in lines:
        line = line.rstrip()
        final_lines.append(line)
        
        if line.strip() == "温馨提示,#group#" and not custom_inserted:
            final_lines.pop()
            
            # 为每个自定义源添加内容
            for group_name, source_url in CUSTOM_SOURCES:
                print(f"\n🔧 处理自定义源: {group_name}")
                print(f"   地址: {source_url}")
                
                # 添加一级分组
                final_lines.append(f"{group_name},#group#")
                
                # --- 针对 tv84 和 tv26 的特殊处理：强制添加“综合”分类 ---
                if group_name in ["tv84", "tv26"]:
                    print(f"   📌 为 {group_name} 添加默认分类: 综合,#genre#")
                    final_lines.append("综合,#genre#")
                # ----------------------------------------------------
                
                # 获取源内容
                source_content = fetch_file_content(source_url)
                if source_content:
                    converted_content = convert_to_txt(source_content, source_url)
                    source_lines = converted_content.split('\n')
                    for source_line in source_lines:
                        if source_line.strip():
                            final_lines.append(source_line.rstrip())
                    print(f"   ✅ 添加 {len(source_lines)} 行内容")
                else:
                    print(f"   ⚠️ 该源无有效内容")
            
            final_lines.append("温馨提示,#group#")
            custom_inserted = True
            print(f"\n📝 已插入 {len(CUSTOM_SOURCES)} 个自定义源")
    
    # 3. 将“温馨提示”改为“生成日期”
    current_date = time.strftime('%y%m%d')
    final_lines = [line.replace("温馨提示,#group#", f"{current_date},#group#") for line in final_lines]
    
    # 4. 写入文件
    print(f"\n💾 正在写入最终文件: {OUTPUT_FILE}")
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write('\n'.join(final_lines))
    
    total_lines = len(final_lines)
    print(f"✅ 完成！")
    print(f"   📊 总行数: {total_lines}")
    print(f"   📁 保存到: {OUTPUT_FILE}")
    print(f"   🕐 日期标记: {current_date},#genre#")
    print("=" * 70)

if __name__ == "__main__":
    main()
