import requests
import time
import re

# ================ 🔧 配置区域 ================

# 1. 您的蓝本文件地址 (zb.txt)
MASTER_FILE_URL = "https://raw.githubusercontent.com/chenmo77/iptvindex/refs/heads/main/zb.txt"

# 2. 您自定义的其他直播源列表
#    格式: [("一级分组名称", "源地址"), ...]
CUSTOM_SOURCES = [
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

def m3u_to_txt(content):
    """
    将M3U/M3U8格式转换为TXT格式
    M3U格式：
        #EXTINF:-1,CCTV1
        http://example.com/cctv1.m3u8
    转换为：
        CCTV1,http://example.com/cctv1.m3u8
    """
    lines = content.split('\n')
    txt_lines = []
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        if line.startswith('#EXTINF:'):
            # 提取频道名称（逗号后面的部分）
            name_match = re.search(r',([^,]+)$', line)
            if name_match:
                channel_name = name_match.group(1).strip()
                
                # 下一行应该是URL
                if i + 1 < len(lines):
                    channel_url = lines[i + 1].strip()
                    if channel_url and not channel_url.startswith('#'):
                        txt_lines.append(f"{channel_name},{channel_url}")
            i += 2
        else:
            # 保留非EXTINF行（如注释、分组标记等）
            if line and not line.startswith('#EXT'):
                txt_lines.append(line)
            i += 1
    
    return '\n'.join(txt_lines)

def main():
    print("=" * 70)
    print("🚀 开始合并直播源（只合并，不修改）...")
    print("=" * 70)
    
    # 1. 获取蓝本文件
    master_content = fetch_file_content(MASTER_FILE_URL)
    if not master_content:
        print("❌ 无法获取蓝本文件，程序终止")
        return
    
    # 2. 构建最终文件内容
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
            
            # 为每个自定义源添加内容
            for group_name, source_url in CUSTOM_SOURCES:
                print(f"\n🔧 处理自定义源: {group_name}")
                print(f"   地址: {source_url}")
                
                # 添加一级分组
                final_lines.append(f"{group_name},#group#")
                
                # 获取源内容
                source_content = fetch_file_content(source_url)
                if source_content:
                    # 如果是M3U/M3U8格式，转换为TXT
                    if '.m3u' in source_url.lower() or '#EXTM3U' in source_content:
                        print(f"   📋 检测到M3U格式，正在转换...")
                        source_content = m3u_to_txt(source_content)
                    
                    # 添加源内容（原样保留）
                    source_lines = source_content.split('\n')
                    for source_line in source_lines:
                        if source_line.strip():  # 跳过空行
                            final_lines.append(source_line.rstrip())
                    print(f"   ✅ 添加 {len(source_lines)} 行内容")
                else:
                    print(f"   ⚠️ 该源无有效内容")
            
            # 最后再添加温馨提示行
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
    
    # 5. 统计信息
    total_lines = len(final_lines)
    print(f"✅ 完成！")
    print(f"   📊 总行数: {total_lines}")
    print(f"   📁 保存到: {OUTPUT_FILE}")
    print(f"   🕐 日期标记: {current_date},#group#")
    print("=" * 70)

if __name__ == "__main__":
    main()
