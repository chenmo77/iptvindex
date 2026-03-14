import requests
import time
import re
from collections import OrderedDict
import os

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

# ----- 央视排序专用列表 (1-17) -----
CCTV_ORDER = [
    "CCTV1", "CCTV2", "CCTV3", "CCTV4", "CCTV5", "CCTV5+", "CCTV6", "CCTV7",
    "CCTV8", "CCTV9", "CCTV10", "CCTV11", "CCTV12", "CCTV13", "CCTV14",
    "CCTV15", "CCTV16", "CCTV17"
]

# ----- 卫视优先级顺序 -----
WEISHI_PRIORITY = ['湖南', '浙江', '江苏', '北京', '东方']

# ----- 港澳分类优先顺序 -----
GANGAO_PRIORITY = ['凤凰中文', '凤凰资讯', '凤凰香港']

# ----- 海外分类关键词 -----
OVERSEAS_KEYWORDS = [
    'CNN', 'BBC', 'NHK', 'KBS', 'SBS', 'MBC', 'FOX', 'HBO', 'CINEMAX',
    'DISCOVERY', 'NGC', 'HISTORY', 'DW', 'FRANCE', 'ALJAZEERA',
    'BLOOMBERG', 'CNBC', 'ABC', 'NBC', 'CBS', '国家地理', '探索频道'
]

# ----- 直播平台分类（按来源URL匹配）-----
PLATFORM_SOURCES = {
    'yylunbo.m3u': 'YY',
    'bililive.m3u': 'B站',
    'huyayqk.m3u': '虎牙',
    'douyuyqk.m3u': '斗鱼'
}

# ----- 有效频道关键词（用于过滤无效内容）-----
VALID_CHANNEL_KEYWORDS = [
    'CCTV', '卫视', 'TVB', '凤凰', '明珠', '翡翠', 'J2', '互动新闻',
    'CNN', 'BBC', 'NHK', 'KBS', 'SBS', 'MBC', 'FOX', 'HBO',
    'Discovery', '国家地理', '探索频道', '电影', '体育', '新闻',
    '综合', '都市', '影视', '少儿', '卡通', '动画', '音乐', '戏曲',
    # 直播平台关键词
    'YY', 'B站', '哔哩哔哩', '虎牙', '斗鱼', '直播'
]

def clean_channel_name(name):
    """清理频道名称，去掉多余的修饰词"""
    # 去掉分辨率标记
    name = re.sub(r'[\(\[（【][\d\s]*[Pp][\)\]）】]?', '', name)
    name = re.sub(r'[\s-]*\d+P', '', name, flags=re.IGNORECASE)
    name = re.sub(r'[\s-]*[超高清4K8K]', '', name)
    
    # 去掉多余的空白
    name = re.sub(r'\s+', ' ', name).strip()
    return name

def standardize_cctv_name(name):
    """
    将央视名称标准化，非数字频道去掉CCTV前缀
    """
    upper_name = name.upper()
    cleaned = clean_channel_name(name)
    
    # 特殊处理：世界地理、高尔夫网球等去掉CCTV
    special_cctv = ['世界地理', '高尔夫网球', '风云足球', '风云音乐', 
                    '第一剧场', '风云剧场', '怀旧剧场', '女性时尚',
                    '央视台球', '兵器科技', '文化精品', '电视指南']
    
    for special in special_cctv:
        if special in cleaned or special in upper_name:
            # 如果包含CCTV则去掉
            cleaned = re.sub(r'^CCTV[\s-]*', '', cleaned, flags=re.IGNORECASE)
            # 特殊处理高尔夫网球
            if '高尔夫' in cleaned and '网球' in cleaned:
                cleaned = '高尔夫·网球'
            return cleaned.strip()
    
    # 提取标准CCTV数字
    match = re.search(r'CCTV?[\s-]*(\d+[\+]?)', upper_name)
    if match:
        num = match.group(1)
        return f"CCTV{num}"
    
    # 处理中文“中央一套”等情况
    match = re.search(r'中央[^\d]*(\d+)', upper_name)
    if match:
        num = match.group(1)
        return f"CCTV{num}"
    
    return cleaned

def is_valid_channel(name):
    """判断是否为有效频道（过滤垃圾内容）"""
    name_upper = name.upper()
    
    # 过滤明显不是频道的内容
    invalid_patterns = [
        r'19\d{2}年春晚', r'20\d{2}年春晚', r'春晚',
        r'更新时间', r'总频道数', r'分类统计',
        r'测试', r'直播源', r'收集', r'整理',
        r'CCTV[^\d]*$',  # 单独的"CCTV"没有数字
    ]
    
    for pattern in invalid_patterns:
        if re.search(pattern, name_upper):
            return False
    
    # 至少包含一个有效关键词才保留
    for kw in VALID_CHANNEL_KEYWORDS:
        if kw in name_upper:
            return True
    
    return False

def get_channel_category(name, source_url):
    """
    根据频道名和来源URL判断所属分类
    返回: (分类, 显示名称, 排序键)
    """
    original_name = name
    cleaned_name = clean_channel_name(name)
    
    # 先判断是否有效频道
    if not is_valid_channel(cleaned_name) and not is_valid_channel(original_name):
        return None, None, None
    
    name_upper = cleaned_name.upper()
    
    # ----- 直播平台分类（按来源URL）-----
    for url_pattern, platform_name in PLATFORM_SOURCES.items():
        if url_pattern in source_url:
            # 对于直播平台，保留原始名称，不做额外处理
            return platform_name, cleaned_name, cleaned_name
    
    # ----- 央视分类 -----
    if 'CCTV' in name_upper or '中央' in name_upper or '央视' in name_upper:
        std_name = standardize_cctv_name(cleaned_name)
        if std_name.startswith('CCTV') and re.search(r'CCTV\d', std_name):
            return '央视', std_name, std_name
        return '央视', std_name, std_name
    
    # ----- 港澳分类 -----
    gangao_keywords = [
        'TVB', '明珠', '翡翠', 'J2', '互动新闻', '无线',
        '凤凰中文', '凤凰资讯', '凤凰香港', '凤凰卫视',
        'HK', 'MACAU', '澳亚', '莲花', '澳视'
    ]
    for kw in gangao_keywords:
        if kw in cleaned_name or kw in name_upper:
            if '凤凰中文' in cleaned_name or '凤凰中文台' in cleaned_name:
                return '港澳', '凤凰中文', '凤凰中文'
            if '凤凰资讯' in cleaned_name:
                return '港澳', '凤凰资讯', '凤凰资讯'
            if '凤凰香港' in cleaned_name:
                return '港澳', '凤凰香港', '凤凰香港'
            return '港澳', cleaned_name, cleaned_name
    
    # ----- 卫视分类 -----
    if '卫视' in cleaned_name:
        weishi_match = re.match(r'([^卫视]+)卫视', cleaned_name)
        if weishi_match:
            core_name = weishi_match.group(1).strip()
            if core_name == '湖南':
                return '卫视', '湖南卫视', '湖南'
            elif core_name == '浙江':
                return '卫视', '浙江卫视', '浙江'
            elif core_name == '江苏':
                return '卫视', '江苏卫视', '江苏'
            elif core_name == '北京':
                return '卫视', '北京卫视', '北京'
            elif core_name == '东方':
                return '卫视', '东方卫视', '东方'
            else:
                return '卫视', f"{core_name}卫视", core_name
        return '卫视', cleaned_name, cleaned_name
    
    # ----- 海外分类 -----
    for kw in OVERSEAS_KEYWORDS:
        if kw in name_upper or kw in cleaned_name:
            return '海外', cleaned_name, cleaned_name
    
    # 其他分类
    return '其他', cleaned_name, cleaned_name

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
        
        if line.startswith('#EXTINF:'):
            name_match = re.search(r',([^,]+)$', line)
            if name_match:
                channel_name = name_match.group(1).strip()
                
                if i + 1 < len(lines):
                    channel_url = lines[i + 1].strip()
                    if channel_url and not channel_url.startswith('#'):
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
    
    print("=" * 60)
    print("🚀 开始抓取直播源...")
    print("=" * 60)
    
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
            
            print(f"   ✅ 解析到 {len(channels)} 个频道")
            all_channels.extend(channels)
            
        except Exception as e:
            print(f"   ❌ 抓取失败: {e}")
    
    print(f"\n📊 共抓取到 {len(all_channels)} 个原始频道")
    
    # 2. 分类和过滤
    print("\n🔍 正在分类和过滤频道...")
    
    current_date = time.strftime('%y%m%d')
    current_time_full = time.strftime('%Y-%m-%d %H:%M:%S')
    
    # 存储处理后的频道
    processed_channels = []
    # 统计所有分类（包括直播平台）
    all_categories = ['央视', '卫视', '港澳', '海外', '其他', 'YY', 'B站', '虎牙', '斗鱼', current_date]
    category_stats = {cat: 0 for cat in all_categories}
    
    for ch in all_channels:
        result = get_channel_category(ch['name'], ch['source'])
        if result[0] is None:  # 无效频道
            continue
            
        category, display_name, sort_key = result
        
        processed_channels.append({
            'display_name': display_name,
            'sort_key': sort_key,
            'category': category,
            'url': ch['url']
        })
        category_stats[category] += 1
    
    print(f"✅ 过滤后剩余 {len(processed_channels)} 个有效频道")
    print("📊 分类统计：")
    for cat in ['央视', '卫视', '港澳', '海外', '其他', 'YY', 'B站', '虎牙', '斗鱼']:
        if category_stats[cat] > 0:
            print(f"   {cat}: {category_stats[cat]} 个")
    
    # 3. 按分类和频道名分组
    channels_by_category = {cat: {} for cat in ['央视', '卫视', '港澳', '海外', '其他', 'YY', 'B站', '虎牙', '斗鱼']}
    
    for ch in processed_channels:
        cat = ch['category']
        key = ch['sort_key']
        
        if cat not in channels_by_category:
            channels_by_category[cat] = {}
        
        if key not in channels_by_category[cat]:
            channels_by_category[cat][key] = []
        channels_by_category[cat][key].append(ch)
    
    # 4. 写入最终文件
    print(f"\n💾 正在写入TXT文件: {OUTPUT_FILE}")
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(f"# 自动聚合直播源 - 生成时间: {current_time_full}\n")
        f.write(f"# 总频道数: {len(processed_channels)} | 分类: 央视/卫视/港澳/海外/其他/YY/B站/虎牙/斗鱼/日期\n\n")
        
        # ----- 央视分类 -----
        cctv_dict = channels_by_category.get('央视', {})
        if cctv_dict:
            f.write(f"\n央视,#genre#\n")
            written = set()
            for std_name in CCTV_ORDER:
                if std_name in cctv_dict:
                    for ch in cctv_dict[std_name]:
                        f.write(f"{ch['display_name']},{ch['url']}\n")
                    written.add(std_name)
            others = sorted([k for k in cctv_dict.keys() if k not in written])
            for key in others:
                for ch in cctv_dict[key]:
                    f.write(f"{ch['display_name']},{ch['url']}\n")
        
        # ----- 卫视分类 -----
        weishi_dict = channels_by_category.get('卫视', {})
        if weishi_dict:
            f.write(f"\n卫视,#genre#\n")
            written = set()
            for p in WEISHI_PRIORITY:
                if p in weishi_dict:
                    for ch in weishi_dict[p]:
                        f.write(f"{ch['display_name']},{ch['url']}\n")
                    written.add(p)
            others = sorted([k for k in weishi_dict.keys() if k not in written])
            for key in others:
                for ch in weishi_dict[key]:
                    f.write(f"{ch['display_name']},{ch['url']}\n")
        
        # ----- 港澳分类 -----
        gangao_dict = channels_by_category.get('港澳', {})
        if gangao_dict:
            f.write(f"\n港澳,#genre#\n")
            written = set()
            for p in GANGAO_PRIORITY:
                if p in gangao_dict:
                    for ch in gangao_dict[p]:
                        f.write(f"{ch['display_name']},{ch['url']}\n")
                    written.add(p)
            others = sorted([k for k in gangao_dict.keys() if k not in written])
            for key in others:
                for ch in gangao_dict[key]:
                    f.write(f"{ch['display_name']},{ch['url']}\n")
        
        # ----- 海外分类 -----
        overseas_dict = channels_by_category.get('海外', {})
        if overseas_dict:
            f.write(f"\n海外,#genre#\n")
            for key in sorted(overseas_dict.keys()):
                for ch in overseas_dict[key]:
                    f.write(f"{ch['display_name']},{ch['url']}\n")
        
        # ----- 其他分类 -----
        other_dict = channels_by_category.get('其他', {})
        if other_dict:
            f.write(f"\n其他,#genre#\n")
            for key in sorted(other_dict.keys()):
                for ch in other_dict[key]:
                    f.write(f"{ch['display_name']},{ch['url']}\n")
        
        # ----- 直播平台分类（YY/B站/虎牙/斗鱼）-----
        platform_order = ['YY', 'B站', '虎牙', '斗鱼']
        for platform in platform_order:
            platform_dict = channels_by_category.get(platform, {})
            if platform_dict:
                f.write(f"\n{platform},#genre#\n")
                for key in sorted(platform_dict.keys()):
                    for ch in platform_dict[key]:
                        f.write(f"{ch['display_name']},{ch['url']}\n")
        
        # ========== 日期分类 ==========
        f.write(f"\n{current_date},#genre#\n")
        f.write(f"更新时间 本频道列表更新于 {current_time_full}\n")
        f.write(f"总频道数 {len(processed_channels)}个\n")
        for cat in ['央视', '卫视', '港澳', '海外', '其他', 'YY', 'B站', '虎牙', '斗鱼']:
            if category_stats[cat] > 0:
                f.write(f"{cat} {category_stats[cat]}个\n")
        
        # 文件末尾信息
        f.write(f"\n\n# ========================================\n")
        f.write(f"# 文件生成时间: {current_time_full}\n")
        f.write(f"# 总频道数量: {len(processed_channels)} 个\n")
        f.write(f"# 来源数量: {len(SOURCE_URLS)} 个\n")
        for cat in ['央视', '卫视', '港澳', '海外', '其他', 'YY', 'B站', '虎牙', '斗鱼']:
            if category_stats[cat] > 0:
                f.write(f"#   {cat}: {category_stats[cat]} 个\n")
        f.write(f"# ========================================\n")
    
    print(f"✅ 完成！")
    print(f"   📊 总共 {len(processed_channels)} 个有效频道")
    print(f"   📁 保存到: {OUTPUT_FILE}")
    print(f"   🕐 日期分类: {current_date}")
    print("=" * 60)
    
    # 调试信息
    print("\n🔍 调试信息：")
    print(f"   当前目录: {os.getcwd()}")
    print(f"   目录下文件: {os.listdir('.')}")
    if os.path.exists(OUTPUT_FILE):
        print(f"   文件大小: {os.path.getsize(OUTPUT_FILE)} 字节")

if __name__ == "__main__":
    fetch_and_merge()
