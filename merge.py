import requests
import time
import re
import os
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
    "https://raw.githubusercontent.com/mursor1985/LIVE/refs/heads/main/yylunbo.m3u",
    "https://raw.githubusercontent.com/mursor1985/LIVE/refs/heads/main/bililive.m3u",
    "https://raw.githubusercontent.com/mursor1985/LIVE/refs/heads/main/huyayqk.m3u",
    "https://raw.githubusercontent.com/mursor1985/LIVE/refs/heads/main/douyuyqk.m3u"
]

# ================ 🔧 配置区域 2：输出设置 ================
OUTPUT_FILE = "live.txt"
# ================================================================

# ================ 📺 预定义频道列表 ================

# ----- 央视分类（按指定顺序）-----
CCTV_CHANNELS = [
    "CCTV1", "CCTV2", "CCTV3", "CCTV4", "CCTV5", "CCTV5+", "CCTV6", "CCTV7",
    "CCTV8", "CCTV9", "CCTV10", "CCTV11", "CCTV12", "CCTV13", "CCTV14",
    "CCTV15", "CCTV16", "CCTV17",
    "CCTV4美洲", "CCTV4欧洲",
    "CGTN", "CGTN纪录", "CGTN法语", "CGTN俄语", "CGTN西语", "CGTN阿语",
    "兵器科技", "第一剧场", "电视指南", "风云剧场", "风云音乐", "风云足球",
    "高尔夫·网球", "怀旧剧场", "女性时尚", "世界地理", "央视台球", "央视文化精品"
]

# ----- 卫视分类（按指定顺序+拼音）-----
WEISHI_PRIORITY = ["湖南卫视", "浙江卫视", "江苏卫视", "北京卫视", "东方卫视", "深圳卫视"]

# ----- 港澳分类（按指定顺序+拼音）-----
GANGAO_PRIORITY = ["凤凰中文", "凤凰资讯", "凤凰香港"]
GANGAO_KEYWORDS = [
    "TVB", "明珠台", "翡翠台", "J2", "互动新闻台", "无线新闻台",
    "凤凰", "HK", "MACAU", "澳亚卫视", "澳门卫视", "莲花卫视",
    "香港卫视", "台湾", "民视", "三立", "中天", "东森", "TVBS"
]

# ----- 海外分类关键词 -----
OVERSEAS_KEYWORDS = [
    "CNN", "BBC", "NHK", "KBS", "SBS", "MBC", "FOX", "HBO", "CINEMAX",
    "Discovery", "国家地理", "探索频道", "History", "DW", "France",
    "Al Jazeera", "Bloomberg", "CNBC", "ABC", "NBC", "CBS", "EuroNews"
]

# ================================================

def is_valid_url(url):
    """检查URL是否有效（不是空链接或占位符）"""
    if not url or len(url) < 10:
        return False
    
    url = url.strip().lower()
    
    # 过滤无效URL
    invalid_patterns = [
        r'^https?://$',  # 只有http://或https://
        r'^https?://\s*$',  # http://后面是空白
        r'^#$',  # 只有#
        r'^javascript:',
        r'^about:',
        r'null',
        r'undefined'
    ]
    
    for pattern in invalid_patterns:
        if re.match(pattern, url):
            return False
    
    # 必须有有效的域名结构
    if not re.match(r'^https?://[^\s]+', url):
        return False
    
    return True

def clean_channel_name(name):
    """清理频道名称，去掉多余的修饰词"""
    # 去掉分辨率/清晰度标记
    name = re.sub(r'[\(\[（【][\d\s]*[PpKk][\)\]）】]?', '', name)
    name = re.sub(r'[\s-]*\d+[PpKk]', '', name)
    name = re.sub(r'[\s-]*(超清|高清|HD|4K|8K|UHD)', '', name)
    name = re.sub(r'[\s-]*\d{3,4}x\d{3,4}', '', name)
    
    # 去掉多余的空白
    name = re.sub(r'\s+', ' ', name).strip()
    return name

def normalize_channel_name(name, category):
    """根据分类标准化频道名称"""
    cleaned = clean_channel_name(name)
    
    # 央视标准化
    if category == '央视':
        # 先匹配预定义列表中的特殊名称
        for cctv_name in CCTV_CHANNELS:
            if cctv_name.lower() in cleaned.lower():
                return cctv_name
        
        # 匹配CCTV数字格式
        upper_name = cleaned.upper()
        match = re.search(r'CCTV?[\s-]*(\d+[\+]?)', upper_name)
        if match:
            num = match.group(1)
            return f"CCTV{num}"
        
        # 匹配中文中央
        match = re.search(r'中央[^\d]*(\d+)', upper_name)
        if match:
            num = match.group(1)
            return f"CCTV{num}"
        
        return cleaned
    
    # 卫视标准化
    elif category == '卫视':
        if '卫视' in cleaned:
            core = re.sub(r'卫视.*$', '', cleaned)
            return core + '卫视'
        return cleaned
    
    # 其他分类直接返回清理后的名称
    return cleaned

def is_channel_match(channel_name, target_pattern):
    """判断频道名是否匹配目标（忽略大小写）"""
    name_upper = channel_name.upper()
    pattern_upper = target_pattern.upper()
    
    return pattern_upper in name_upper

def parse_txt_content(content, source_url):
    """解析TXT格式的直播源"""
    channels = []
    lines = content.split('\n')
    for line in lines:
        line = line.strip()
        if not line or '#genre#' in line or line.startswith('#'):
            continue
        
        match = re.match(r'([^,]+),(.+)', line)
        if match:
            channel_name = match.group(1).strip()
            channel_url = match.group(2).strip()
            
            # 去掉注释
            if ' #' in channel_url:
                channel_url = channel_url.split(' #')[0]
            
            # 只保留有效URL的频道
            if is_valid_url(channel_url):
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
        
        if line.startswith('#EXTINF:'):
            name_match = re.search(r',([^,]+)$', line)
            if name_match:
                channel_name = name_match.group(1).strip()
                
                if i + 1 < len(lines):
                    channel_url = lines[i + 1].strip()
                    if channel_url and not channel_url.startswith('#'):
                        # 只保留有效URL的频道
                        if is_valid_url(channel_url):
                            channels.append({
                                'name': channel_name,
                                'url': channel_url,
                                'source': source_url
                            })
            i += 2
        else:
            i += 1
    return channels

def fetch_and_merge():
    all_channels = []
    
    print("=" * 70)
    print("🚀 开始抓取直播源（精简版：5大分类 + 智能去重）...")
    print("=" * 70)
    
    # 1. 抓取所有源
    for url in SOURCE_URLS:
        try:
            print(f"📡 正在抓取: {url}")
            response = requests.get(url, timeout=10)
            response.encoding = 'utf-8'
            content = response.text
            
            if '.m3u' in url.lower() or '#EXTM3U' in content:
                print(f"   📋 检测到M3U格式")
                channels = parse_m3u_content(content, url)
            else:
                print(f"   📋 检测到TXT格式")
                channels = parse_txt_content(content, url)
            
            print(f"   ✅ 解析到 {len(channels)} 个有效频道")
            all_channels.extend(channels)
            
        except Exception as e:
            print(f"   ❌ 抓取失败: {e}")
    
    print(f"\n📊 共抓取到 {len(all_channels)} 个有效频道（已过滤无效URL）")
    
    # 2. 初始化分类字典
    current_date = time.strftime('%y%m%d')
    current_time_full = time.strftime('%Y-%m-%d %H:%M:%S')
    
    # 定义5大分类
    categories = ['央视', '卫视', '港澳', '海外', '其他']
    
    # 每个分类存储 {标准化名称: {去重后的URL列表}}
    channels_by_category = {cat: OrderedDict() for cat in categories}
    
    # 3. 匹配频道到各分类（先去重）
    print("\n🔍 正在匹配和去重...")
    
    # 用于全局去重的集合 (url已去重，这里主要是为了统计)
    unique_urls = set()
    
    for ch in all_channels:
        # 先检查URL是否已存在（全局去重）
        if ch['url'] in unique_urls:
            continue
        unique_urls.add(ch['url'])
        
        # 央视匹配
        matched = False
        for cctv_name in CCTV_CHANNELS:
            if is_channel_match(ch['name'], cctv_name):
                std_name = normalize_channel_name(ch['name'], '央视')
                if std_name not in channels_by_category['央视']:
                    channels_by_category['央视'][std_name] = []
                # 同一频道名下再按URL去重
                if ch['url'] not in [item['url'] for item in channels_by_category['央视'][std_name]]:
                    channels_by_category['央视'][std_name].append({
                        'url': ch['url'],
                        'original_name': ch['name']
                    })
                matched = True
                break
        
        if matched:
            continue
        
        # 卫视匹配（优先级列表）
        for weishi in WEISHI_PRIORITY:
            if is_channel_match(ch['name'], weishi):
                std_name = normalize_channel_name(ch['name'], '卫视')
                if std_name not in channels_by_category['卫视']:
                    channels_by_category['卫视'][std_name] = []
                if ch['url'] not in [item['url'] for item in channels_by_category['卫视'][std_name]]:
                    channels_by_category['卫视'][std_name].append({
                        'url': ch['url'],
                        'original_name': ch['name']
                    })
                matched = True
                break
        
        if matched:
            continue
        
        # 卫视匹配（其他卫视）
        if '卫视' in ch['name']:
            std_name = normalize_channel_name(ch['name'], '卫视')
            if std_name not in channels_by_category['卫视']:
                channels_by_category['卫视'][std_name] = []
            if ch['url'] not in [item['url'] for item in channels_by_category['卫视'][std_name]]:
                channels_by_category['卫视'][std_name].append({
                    'url': ch['url'],
                    'original_name': ch['name']
                })
            continue
        
        # 港澳匹配
        for kw in GANGAO_KEYWORDS:
            if kw in ch['name']:
                # 特殊处理凤凰系列
                if '凤凰中文' in ch['name']:
                    std_name = '凤凰中文'
                elif '凤凰资讯' in ch['name']:
                    std_name = '凤凰资讯'
                elif '凤凰香港' in ch['name']:
                    std_name = '凤凰香港'
                else:
                    std_name = clean_channel_name(ch['name'])
                
                if std_name not in channels_by_category['港澳']:
                    channels_by_category['港澳'][std_name] = []
                if ch['url'] not in [item['url'] for item in channels_by_category['港澳'][std_name]]:
                    channels_by_category['港澳'][std_name].append({
                        'url': ch['url'],
                        'original_name': ch['name']
                    })
                matched = True
                break
        
        if matched:
            continue
        
        # 海外匹配
        for kw in OVERSEAS_KEYWORDS:
            if kw.upper() in ch['name'].upper():
                std_name = clean_channel_name(ch['name'])
                if std_name not in channels_by_category['海外']:
                    channels_by_category['海外'][std_name] = []
                if ch['url'] not in [item['url'] for item in channels_by_category['海外'][std_name]]:
                    channels_by_category['海外'][std_name].append({
                        'url': ch['url'],
                        'original_name': ch['name']
                    })
                matched = True
                break
        
        if matched:
            continue
        
        # 其他分类（包含所有未匹配的，包括YY/B站/虎牙/斗鱼）
        std_name = clean_channel_name(ch['name'])
        if std_name and len(std_name) > 1:
            if std_name not in channels_by_category['其他']:
                channels_by_category['其他'][std_name] = []
            if ch['url'] not in [item['url'] for item in channels_by_category['其他'][std_name]]:
                channels_by_category['其他'][std_name].append({
                    'url': ch['url'],
                    'original_name': ch['name']
                })
    
    # 4. 统计各分类频道数（按URL计数，不是按频道名）
    category_counts = {}
    for cat in categories:
        count = sum(len(urls) for urls in channels_by_category[cat].values())
        category_counts[cat] = count
    
    total_channels = sum(category_counts.values())
    total_unique_urls = len(unique_urls)
    
    print("\n📊 分类统计（按URL计数）：")
    for cat in categories:
        if category_counts[cat] > 0:
            print(f"   {cat}: {category_counts[cat]} 个源")
    
    # 5. 写入最终文件
    print(f"\n💾 正在写入TXT文件: {OUTPUT_FILE}")
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(f"# 自动聚合直播源 - 生成时间: {current_time_full}\n")
        f.write(f"# 总源数: {total_channels} | 总去重后URL数: {total_unique_urls}\n")
        f.write(f"# 分类: 央视/卫视/港澳/海外/其他\n\n")
        
        # ----- 央视分类（按预定义顺序）-----
        if channels_by_category['央视']:
            f.write(f"\n央视,#genre#\n")
            for cctv_name in CCTV_CHANNELS:
                if cctv_name in channels_by_category['央视']:
                    for ch in channels_by_category['央视'][cctv_name]:
                        f.write(f"{cctv_name},{ch['url']}\n")
        
        # ----- 卫视分类（优先级+拼音）-----
        if channels_by_category['卫视']:
            f.write(f"\n卫视,#genre#\n")
            # 先写优先级列表中的
            written = set()
            for weishi in WEISHI_PRIORITY:
                if weishi in channels_by_category['卫视']:
                    for ch in channels_by_category['卫视'][weishi]:
                        f.write(f"{weishi},{ch['url']}\n")
                    written.add(weishi)
            # 再写其他的（按拼音排序）
            others = sorted([name for name in channels_by_category['卫视'].keys() if name not in written])
            for name in others:
                for ch in channels_by_category['卫视'][name]:
                    f.write(f"{name},{ch['url']}\n")
        
        # ----- 港澳分类（凤凰优先+拼音）-----
        if channels_by_category['港澳']:
            f.write(f"\n港澳,#genre#\n")
            # 先写凤凰系列
            written = set()
            for phoenix in GANGAO_PRIORITY:
                if phoenix in channels_by_category['港澳']:
                    for ch in channels_by_category['港澳'][phoenix]:
                        f.write(f"{phoenix},{ch['url']}\n")
                    written.add(phoenix)
            # 再写其他的（按拼音排序）
            others = sorted([name for name in channels_by_category['港澳'].keys() if name not in written])
            for name in others:
                for ch in channels_by_category['港澳'][name]:
                    f.write(f"{name},{ch['url']}\n")
        
        # ----- 海外分类（拼音排序）-----
        if channels_by_category['海外']:
            f.write(f"\n海外,#genre#\n")
            for name in sorted(channels_by_category['海外'].keys()):
                for ch in channels_by_category['海外'][name]:
                    f.write(f"{name},{ch['url']}\n")
        
        # ----- 其他分类（拼音排序）- 包含YY/B站/虎牙/斗鱼等 -----
        if channels_by_category['其他']:
            f.write(f"\n其他,#genre#\n")
            for name in sorted(channels_by_category['其他'].keys()):
                for ch in channels_by_category['其他'][name]:
                    f.write(f"{name},{ch['url']}\n")
        
        # ========== 日期分类（格式：频道名,http://）==========
        f.write(f"\n{current_date},#genre#\n")
        f.write(f"总源数{total_channels}个,http://\n")
        for cat in categories:
            if category_counts[cat] > 0:
                f.write(f"{cat}{category_counts[cat]}个,http://\n")
        
        # 文件末尾信息
        f.write(f"\n\n# ========================================\n")
        f.write(f"# 文件生成时间: {current_time_full}\n")
        f.write(f"# 总源数量: {total_channels} 个\n")
        f.write(f"# 总去重后URL数: {total_unique_urls} 个\n")
        f.write(f"# 来源数量: {len(SOURCE_URLS)} 个\n")
        for cat in categories:
            if category_counts[cat] > 0:
                f.write(f"#   {cat}: {category_counts[cat]} 个\n")
        f.write(f"# ========================================\n")
    
    print(f"✅ 完成！")
    print(f"   📊 总共 {total_channels} 个有效源（去重后 {total_unique_urls} 个唯一URL）")
    print(f"   📁 保存到: {OUTPUT_FILE}")
    print(f"   🕐 日期分类: {current_date}")
    print("=" * 70)
    
    # 调试信息
    print("\n🔍 调试信息：")
    print(f"   当前目录: {os.getcwd()}")
    print(f"   目录下文件: {os.listdir('.')}")
    if os.path.exists(OUTPUT_FILE):
        print(f"   文件大小: {os.path.getsize(OUTPUT_FILE)} 字节")

if __name__ == "__main__":
    fetch_and_merge()
