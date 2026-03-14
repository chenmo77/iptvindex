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
    "https://php.946985.filegear-sg.me/test.m3u",
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

# ================ 📺 严格按照您指定的顺序 ================

# ----- 央视分类（完全按照您的顺序）-----
CCTV_CHANNELS = [
    "CCTV1", "CCTV2", "CCTV3", "CCTV4", "CCTV5", "CCTV5+", "CCTV6", "CCTV7",
    "CCTV8", "CCTV9", "CCTV10", "CCTV11", "CCTV12", "CCTV13", "CCTV14",
    "CCTV15", "CCTV16", "CCTV17",
    "CCTV4美洲", "CCTV4欧洲",
    "CGTN", "CGTN纪录", "CGTN法语", "CGTN俄语", "CGTN西语", "CGTN阿语",
    "兵器科技", "第一剧场", "电视指南", "风云剧场", "风云音乐", "风云足球",
    "高尔夫·网球", "怀旧剧场", "女性时尚", "世界地理", "央视台球", "央视文化精品"
]

# ----- 卫视分类优先级（完全按照您的顺序）-----
WEISHI_PRIORITY = ["湖南卫视", "浙江卫视", "江苏卫视", "北京卫视", "东方卫视", "深圳卫视"]

# ----- 港澳分类（凤凰系列优先）-----
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

# ----- 直播平台源标识 -----
PLATFORM_SOURCES = [
    "yylunbo.m3u",
    "bililive.m3u", 
    "huyayqk.m3u",
    "douyuyqk.m3u"
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
    """清理频道名称，去掉分辨率/清晰度标记"""
    # 去掉分辨率/清晰度标记
    name = re.sub(r'[\(\[（【][\d\s]*[PpKk][\)\]）】]?', '', name)
    name = re.sub(r'[\s-]*\d+[PpKk]', '', name)
    name = re.sub(r'[\s-]*(超清|高清|HD|4K|8K|UHD)', '', name)
    name = re.sub(r'[\s-]*\d{3,4}x\d{3,4}', '', name)
    
    # 去掉多余的空白
    name = re.sub(r'\s+', ' ', name).strip()
    return name

def normalize_cctv_name(name):
    """标准化央视名称"""
    # 先尝试精确匹配预定义列表
    for cctv_name in CCTV_CHANNELS:
        if cctv_name.lower() in name.lower():
            return cctv_name
    
    # 匹配CCTV数字格式
    name_upper = name.upper()
    
    # 处理CCTV5+这种特殊格式
    if re.search(r'CCTV[\s-]*5[\s-]*\+', name_upper):
        return "CCTV5+"
    
    # 匹配普通CCTV数字
    match = re.search(r'CCTV[\s-]*(\d+)', name_upper)
    if match:
        num = match.group(1)
        # 只保留1-17的数字
        if 1 <= int(num) <= 17:
            return f"CCTV{num}"
    
    # 匹配中文中央
    match = re.search(r'中央[^\d]*(\d+)', name_upper)
    if match:
        num = match.group(1)
        if 1 <= int(num) <= 17:
            return f"CCTV{num}"
    
    return None

def normalize_weishi_name(name):
    """标准化卫视名称"""
    if '卫视' not in name:
        return None
    
    # 提取卫视核心名（去掉"卫视"及后面所有内容）
    core = re.sub(r'卫视.*$', '', name)
    # 去掉清晰度标记
    core = clean_channel_name(core)
    
    # 如果提取后为空，返回原清理后的名称
    if not core:
        cleaned = clean_channel_name(name)
        if '卫视' in cleaned:
            return cleaned
    
    return core + '卫视'

def normalize_gangao_name(name):
    """标准化港澳名称"""
    # 特殊处理凤凰系列
    if '凤凰中文' in name:
        return '凤凰中文'
    elif '凤凰资讯' in name:
        return '凤凰资讯'
    elif '凤凰香港' in name:
        return '凤凰香港'
    
    # 其他港澳频道
    return clean_channel_name(name)

def is_platform_source(source_url):
    """判断是否为直播平台源"""
    for platform in PLATFORM_SOURCES:
        if platform in source_url:
            return True
    return False

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
    print("🚀 开始抓取直播源（严格按照您的规则分类）...")
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
    
    # 用于全局URL去重
    unique_urls = set()
    
    # 3. 先处理直播平台源（放在“其他”分类的最前面）
    platform_channels = []
    regular_channels = []
    
    for ch in all_channels:
        if is_platform_source(ch['source']):
            platform_channels.append(ch)
        else:
            regular_channels.append(ch)
    
    print(f"\n🔍 识别到 {len(platform_channels)} 个直播平台频道（将放在其他分类最前面）")
    
    # 4. 处理直播平台频道（直接进“其他”）
    for ch in platform_channels:
        if ch['url'] in unique_urls:
            continue
        unique_urls.add(ch['url'])
        
        std_name = clean_channel_name(ch['name'])
        if std_name and len(std_name) > 1:
            if std_name not in channels_by_category['其他']:
                channels_by_category['其他'][std_name] = []
            channels_by_category['其他'][std_name].append({
                'url': ch['url'],
                'original_name': ch['name']
            })
    
    # 5. 处理其他频道（按规则分类）
    for ch in regular_channels:
        if ch['url'] in unique_urls:
            continue
        unique_urls.add(ch['url'])
        
        # 央视匹配
        matched = False
        cctv_std = normalize_cctv_name(ch['name'])
        if cctv_std and cctv_std in CCTV_CHANNELS:
            if cctv_std not in channels_by_category['央视']:
                channels_by_category['央视'][cctv_std] = []
            channels_by_category['央视'][cctv_std].append({
                'url': ch['url'],
                'original_name': ch['name']
            })
            continue
        
        # 卫视匹配
        weishi_std = normalize_weishi_name(ch['name'])
        if weishi_std:
            if weishi_std not in channels_by_category['卫视']:
                channels_by_category['卫视'][weishi_std] = []
            channels_by_category['卫视'][weishi_std].append({
                'url': ch['url'],
                'original_name': ch['name']
            })
            continue
        
        # 港澳匹配
        for kw in GANGAO_KEYWORDS:
            if kw in ch['name']:
                gangao_std = normalize_gangao_name(ch['name'])
                if gangao_std not in channels_by_category['港澳']:
                    channels_by_category['港澳'][gangao_std] = []
                channels_by_category['港澳'][gangao_std].append({
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
                channels_by_category['海外'][std_name].append({
                    'url': ch['url'],
                    'original_name': ch['name']
                })
                matched = True
                break
        
        if matched:
            continue
        
        # 其他分类（非平台源）
        std_name = clean_channel_name(ch['name'])
        if std_name and len(std_name) > 1:
            if std_name not in channels_by_category['其他']:
                channels_by_category['其他'][std_name] = []
            channels_by_category['其他'][std_name].append({
                'url': ch['url'],
                'original_name': ch['name']
            })
    
    # 6. 统计各分类源数量
    category_counts = {}
    for cat in categories:
        count = sum(len(urls) for urls in channels_by_category[cat].values())
        category_counts[cat] = count
    
    total_channels = sum(category_counts.values())
    total_unique_urls = len(unique_urls)
    
    print("\n📊 分类统计（按源数量）：")
    for cat in categories:
        if category_counts[cat] > 0:
            print(f"   {cat}: {category_counts[cat]} 个源")
    
    # 7. 写入最终文件
    print(f"\n💾 正在写入TXT文件: {OUTPUT_FILE}")
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(f"# 自动聚合直播源 - 生成时间: {current_time_full}\n")
        f.write(f"# 总源数: {total_channels} | 总去重后URL数: {total_unique_urls}\n")
        f.write(f"# 分类: 央视/卫视/港澳/海外/其他\n\n")
        
        # ----- 央视分类（严格按照您指定的顺序）-----
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
        
        # ----- 其他分类（直播平台优先+拼音）-----
        if channels_by_category['其他']:
            f.write(f"\n其他,#genre#\n")
            
            # 先写直播平台频道（保持原有顺序）
            platform_names = []
            for name in channels_by_category['其他'].keys():
                # 这里可以根据需要标记哪些是平台频道
                f.write(f"{name},{ch['url']}\n")
            
            # 按拼音排序写入所有其他频道
            for name in sorted(channels_by_category['其他'].keys()):
                for ch in channels_by_category['其他'][name]:
                    f.write(f"{name},{ch['url']}\n")
        
        # ========== 日期分类 ==========
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
