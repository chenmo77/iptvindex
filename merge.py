import requests
import time
import re
from collections import OrderedDict

# ================ 🔧 配置区域 ================

# 1. 您的蓝本文件地址 (zb.txt)
MASTER_FILE_URL = "https://raw.githubusercontent.com/chenmo77/iptvindex/refs/heads/main/zb.txt"

# 2. 您自定义的其他直播源列表
#    格式: [("一级分组名称", "源地址"), ...]
#    例如: [("我的备用源", "https://example.com/beiyong.txt"), ("另一个分组", "https://...")]
CUSTOM_SOURCES = [
    # 【请在此处填写您的自定义源，格式如 ("分组A", "http://..."), ("分组B", "http://...")】
    ("咪咕", "https://raw.githubusercontent.com/develop202/migu_video/refs/heads/main/interface.txt"),
    ("Guovin", "https://raw.githubusercontent.com/Guovin/iptv-api/gd/output/result.txt"),
    ("mytv", "https://gitee.com/mytv-android/iptv-api/raw/master/output/result.m3u"),
    ("946985", "https://php.946985.filegear-sg.me/test.m3u"),
    ("h6room", "https://d.h6room.com/frjzb.txt"),
    ("bxtv", "http://bxtv.3a.ink/live.m3u"),
    ("zbds", "https://live.zbds.org/tv/iptv4.txt"),
    ("FMMv6", "https://raw.githubusercontent.com/fanmingming/live/main/tv/m3u/ipv6.m3u"),
    ("cai23511-1", "https://raw.githubusercontent.com/cai23511/yex/master/TVlist/20210808384.m3u"),
    ("cai23511-2", "https://raw.githubusercontent.com/cai23511/yex/master/TVlist/20210808226.m3u"),
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

def normalize_channel_name(channel_name, master_names):
    """
    将频道名称标准化为蓝本文件中的名称
    master_names: 从蓝本文件中提取的所有频道名称集合
    """
    # 去掉清晰度/分辨率标记
    cleaned = re.sub(r'[\(\[（【][\d\s]*[PpKk][\)\]）】]?', '', channel_name)
    cleaned = re.sub(r'[\s-]*\d+[PpKk]', '', cleaned)
    cleaned = re.sub(r'[\s-]*(超清|高清|HD|4K|8K|UHD|标清).*$', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    
    # 在蓝本名称中寻找最接近的匹配
    for master_name in master_names:
        if master_name == cleaned:
            return master_name
        if master_name in cleaned:
            return master_name
        if cleaned in master_name:
            return master_name
    
    return cleaned

def extract_master_info(content):
    """
    解析蓝本文件(zb.txt)，提取所有频道名称
    """
    lines = content.split('\n')
    
    # 收集所有频道名称（用于标准化）
    channel_names = set()
    for line in lines:
        line = line.rstrip()
        if ',' in line and not line.endswith('#group#'):
            name_part = line.split(',')[0].strip()
            if name_part:
                channel_names.add(name_part)
    
    return channel_names

def process_custom_source(url, master_names):
    """
    处理单个自定义源：
    1. 获取内容
    2. 保留原有的 '#genre#' 分组
    3. 将频道名称标准化
    返回：处理后的行列表（不包含一级分组标记）
    """
    content = fetch_file_content(url)
    if not content:
        return []
    
    processed_lines = []
    lines = content.split('\n')
    
    for line in lines:
        line = line.rstrip()
        if not line:
            continue
            
        if '#genre#' in line:
            # 保留原有的二级分组标记
            processed_lines.append(line)
        elif ',' in line:
            # 处理频道行
            parts = line.split(',', 1)
            if len(parts) == 2:
                original_name, channel_url = parts
                # 标准化频道名称
                std_name = normalize_channel_name(original_name, master_names)
                processed_lines.append(f"{std_name},{channel_url}")
        else:
            # 其他内容（如注释）原样保留
            if line and not line.startswith('#'):
                processed_lines.append(line)
    
    return processed_lines

def main():
    print("=" * 70)
    print("🚀 开始生成直播源 (以您的zb.txt为蓝本)...")
    print("=" * 70)
    
    # 1. 获取蓝本文件
    master_content = fetch_file_content(MASTER_FILE_URL)
    if not master_content:
        print("❌ 无法获取蓝本文件，程序终止")
        return
    
    # 2. 提取蓝本中的频道名称（用于标准化）
    master_names = extract_master_info(master_content)
    print(f"📊 蓝本文件解析完成，共 {len(master_names)} 个频道名称")
    
    # 3. 构建最终文件内容
    final_lines = []
    lines = master_content.split('\n')
    
    # 标记是否已插入自定义内容
    custom_inserted = False
    
    for line in lines:
        line = line.rstrip()
        final_lines.append(line)
        
        # 在遇到“温馨提示,#group#”之前插入自定义内容
        if line.strip() == "温馨提示,#group#" and not custom_inserted:
            # 先移除刚添加的温馨提示行
            final_lines.pop()
            
            # 为每个自定义源添加一级分组和内容
            for group_name, source_url in CUSTOM_SOURCES:
                print(f"\n🔧 处理自定义源: {group_name}")
                
                # 添加一级分组（使用 #group#）
                final_lines.append(f"{group_name},#group#")
                
                # 处理源内容
                source_lines = process_custom_source(source_url, master_names)
                if source_lines:
                    final_lines.extend(source_lines)
                    print(f"   ✅ 添加 {len(source_lines)} 行内容")
                else:
                    print(f"   ⚠️ 该源无有效内容")
            
            # 最后再添加温馨提示行
            final_lines.append("温馨提示,#group#")
            custom_inserted = True
            print(f"\n📝 已插入 {len(CUSTOM_SOURCES)} 个自定义一级分组")
    
    # 4. 将“温馨提示”改为“生成日期”
    current_date = time.strftime('%y%m%d')
    final_lines = [line.replace("温馨提示,#group#", f"{current_date},#group#") for line in final_lines]
    
    # 5. 写入文件
    print(f"\n💾 正在写入最终文件: {OUTPUT_FILE}")
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write('\n'.join(final_lines))
    
    print(f"✅ 完成！")
    print(f"   📁 保存到: {OUTPUT_FILE}")
    print(f"   🕐 日期标记: {current_date},#group#")
    print("=" * 70)

if __name__ == "__main__":
    main()
