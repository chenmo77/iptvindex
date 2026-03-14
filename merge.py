import requests
import time
import re
from collections import OrderedDict

# ================ 🔧 配置区域 1：你的直播源地址列表 ================
SOURCE_URLS = [
    "https://raw.githubusercontent.com/chenmo77/iptvindex/refs/heads/main/zb.txt", 
    "https://raw.githubusercontent.com/develop202/migu_video/refs/heads/main/interface.txt",
    "https://raw.githubusercontent.com/Guovin/iptv-api/gd/output/result.txt", 
    "https://gitee.com/mytv-android/iptv-api/raw/master/output/result.m3u", 
    "https://d.h6room.com/frjzb.txt",
    "http://bxtv.3a.ink/live.m3u",
    "https://live.zbds.org/tv/iptv4.txt",
    "https://raw.githubusercontent.com/fanmingming/live/main/tv/m3u/ipv6.m3u",
    "https://raw.githubusercontent.com/cai23511/yex/master/TVlist/20210808384.m3u",
    "https://raw.githubusercontent.com/cai23511/yex/master/TVlist/20210808226.m3u",
    "https://raw.githubusercontent.com/Guovin/iptv-api/gd/output/result.m3u",
    "https://raw.githubusercontent.com/mursor1985/LIVE/refs/heads/main/yylunbo.m3u",
    "https://raw.githubusercontent.com/mursor1985/LIVE/refs/heads/main/bililive.m3u",
    "https://raw.githubusercontent.com/mursor1985/LIVE/refs/heads/main/huyayqk.m3u",
    "https://raw.githubusercontent.com/mursor1985/LIVE/refs/heads/main/douyuyqk.m3u"
]

# ================ 🔧 配置区域 2：测速和可用性设置 ================
OUTPUT_FILE = "live.txt"      # 最终生成的文件名（始终输出TXT格式，酷9专用）
TIMEOUT = 5                           # 测速超时时间（秒）
SPEED_TEST = True                     # 是否开启测速
KEEP_ONLY_WORKING = True               # 是否只保留可用的源
# ================================================================

def parse_txt_content(content, source_url):
    """解析TXT格式的直播源"""
    channels = []
    lines = content.split('\n')
    for line in lines:
        line = line.strip()
        if not line or '#genre#' in line or line.startswith('#'):
            continue
        
        # 匹配 "频道名,地址" 格式
        match = re.match(r'([^,]+),(.+)', line)
        if match:
            channel_name = match.group(1).strip()
            channel_url = match.group(2).strip()
            # 过滤掉注释（如果地址后面有#注释）
            if ' #' in channel_url:
                channel_url = channel_url.split(' #')[0]
            channels.append({
                'name': channel_name,
                'url': channel_url,
                'source': source_url
            })
    return channels

def parse_m3u_content(content, source_url):
    """解析M3U/M3U8格式的直播源"""
    channels = []
    lines = content.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # 查找EXTINF标签，里面包含频道信息
        if line.startswith('#EXTINF:'):
            # 提取频道名称
            # 格式示例: #EXTINF:-1 tvg-id="1" tvg-name="CCTV1" group-title="央视",CCTV1
            name_match = re.search(r',([^,]+)$', line)
            if name_match:
                channel_name = name_match.group(1).strip()
                
                # 下一行应该是URL
                if i + 1 < len(lines):
                    channel_url = lines[i + 1].strip()
                    # 跳过空行和注释行
                    if channel_url and not channel_url.startswith('#'):
                        channels.append({
                            'name': channel_name,
                            'url': channel_url,
                            'source': source_url
                        })
            i += 2  # 跳过URL行
        else:
            i += 1
    return channels

def check_stream_speed(url, timeout=5):
    """测试单个直播源地址的速度和可用性"""
    try:
        start_time = time.time()
        response = requests.get(url, stream=True, timeout=timeout)
        if response.status_code == 200:
            # 读取前1024字节判断是否真的可播放
            next(response.iter_content(1024))
            elapsed = time.time() - start_time
            return True, round(elapsed, 2)
        else:
            return False, None
    except Exception:
        return False, None

def fetch_and_merge():
    all_channels = []
    working_channels = []
    
    print("=" * 50)
    print("🚀 开始抓取直播源（支持TXT/M3U自动识别）...")
    print("=" * 50)
    
    # 1. 抓取所有源
    for url in SOURCE_URLS:
        try:
            print(f"📡 正在抓取: {url}")
            response = requests.get(url, timeout=TIMEOUT)
            response.encoding = 'utf-8'
            content = response.text
            
            # 根据URL后缀或内容自动判断格式
            if '.m3u' in url.lower() or '#EXTM3U' in content:
                print(f"   📋 检测到M3U格式")
                channels = parse_m3u_content(content, url)
            else:
                print(f"   📋 检测到TXT格式")
                channels = parse_txt_content(content, url)
            
            print(f"   ✅ 解析到 {len(channels)} 个频道")
            all_channels.extend(channels)
            
        except Exception as e:
            print(f"   ❌ 抓取失败: {e}")
    
    print(f"\n📊 共抓取到 {len(all_channels)} 个频道（去重前）")
    
    # 2. 频道级别去重
    unique_channels = OrderedDict()
    for ch in all_channels:
        key = f"{ch['name']},{ch['url']}"
        if key not in unique_channels:
            unique_channels[key] = ch
    
    print(f"🔄 去重后剩余 {len(unique_channels)} 个频道")
    
    # 3. 如果需要测速，测试每个频道的可用性
    if SPEED_TEST or KEEP_ONLY_WORKING:
        print("\n⏱️ 开始测试频道可用性和速度...")
        print("-" * 50)
        
        channels_list = list(unique_channels.values())
        total = len(channels_list)
        
        for i, ch in enumerate(channels_list, 1):
            print(f"  [{i}/{total}] 测试: {ch['name']}")
            is_working, speed = check_stream_speed(ch['url'], TIMEOUT)
            
            if is_working:
                ch['working'] = True
                ch['speed'] = speed
                working_channels.append(ch)
                print(f"    ✅ 可用 | 响应时间: {speed}秒")
            else:
                ch['working'] = False
                if not KEEP_ONLY_WORKING:
                    working_channels.append(ch)
                print(f"    ❌ 失效")
        
        print("-" * 50)
        print(f"📈 测速完成：{len(working_channels)}/{total} 个频道可用")
        
        final_channels = working_channels if KEEP_ONLY_WORKING else channels_list
    else:
        final_channels = list(unique_channels.values())
    
    # 4. 按速度排序
    if SPEED_TEST:
        final_channels.sort(key=lambda x: x.get('speed', 999))
    
    # 5. 写入最终文件（始终输出TXT格式，酷9专用）
    print(f"\n💾 正在写入TXT文件: {OUTPUT_FILE}")
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(f"# 自动聚合直播源 - 生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"# 总频道数: {len(final_channels)} | 测速: {'开启' if SPEED_TEST else '关闭'} | 只保留可用: {'是' if KEEP_ONLY_WORKING else '否'}\n")
        f.write(f"# 源格式: 自动识别TXT/M3U混合输入\n\n")
        
        # 按频道分组写入
        current_group = ""
        for ch in final_channels:
            # 简单的分组逻辑
            if ch['name'].startswith('CCTV'):
                group = "央视,#genre#"
            elif '卫视' in ch['name'] or 'TV' in ch['name']:
                group = "卫视,#genre#"
            else:
                group = "其他,#genre#"
            
            if group != current_group:
                f.write(f"\n{group}\n")
                current_group = group
            
            # 写入频道（带速度注释）
            if SPEED_TEST and 'speed' in ch:
                f.write(f"{ch['name']},{ch['url']} # {ch['speed']}秒\n")
            else:
                f.write(f"{ch['name']},{ch['url']}\n")
    
    print(f"✅ 完成！最终文件包含 {len(final_channels)} 个频道")
    print("=" * 50)

if __name__ == "__main__":
    fetch_and_merge()
