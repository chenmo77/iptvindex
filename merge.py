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

def standardize_cctv_name(name):
    """
    将各类央视名称标准化为 "CCTV数字" 或 "CCTV5+" 格式，
    非标准数字系列（如兵器科技）则保留原名且不加CCTV前缀。
    """
    upper_name = name.upper()
    # 特殊处理：CCTV5+ 或 风云足球 等非数字频道，不强制加CCTV前缀
    if '兵器科技' in upper_name or '台球' in upper_name or '风云' in upper_name:
        return name.strip()
    
    # 提取数字部分（包括可能的'+'号）
    match = re.search(r'CCTV?[\s-]*(\d+[\+]?)', upper_name)
    if match:
        num = match.group(1)
        return f"CCTV{num}"
    
    # 处理中文“中央一套”等情况
    match = re.search(r'中央[^\d]*(\d+)', upper_name)
    if match:
        num = match.group(1)
        return f"CCTV{num}"
    
    return name.strip()

def get_channel_category(channel_name):
    """根据频道名判断所属分类"""
    name = channel_name.upper()
    
    # ----- 央视分类 -----
    # 先标准化名称
    std_name = standardize_cctv_name(channel_name)
    # 如果标准化后以CCTV开头，且确实是数字系列，才归入央视
    if std_name.startswith('CCTV'):
        # 过滤掉非标准数字频道（如CCTV兵器科技不应该进央视）
        if '兵器' not in std_name and '台球' not in std_name:
            return '央视', std_name
    
    # ----- 卫视分类（严格筛选）-----
    # 只有频道名明确包含“卫视”二字的才归入此类
    if '卫视' in channel_name:
        # 提取卫视名（去掉“卫视”二字以便排序）
        weishi_name = channel_name.replace('卫视', '').strip()
        return '卫视', weishi_name
    
    # ----- 4K分类 -----
    if '4K' in name or '4k' in channel_name or '超清' in name or 'UHD' in name:
        return '4K', channel_name.strip()
    
    # ----- 港澳分类 -----
    gangao_keywords = ['香港', '澳门', 'TVB', '明珠', '翡翠', 'J2', '互动新闻',
                       '无线', '凤凰', 'HK', 'MACAU', '澳亚', '莲花', '澳视']
    for kw in gangao_keywords:
        if kw in name:
            return '港澳', channel_name.strip()
    
    # ----- 海外分类 -----
    overseas_keywords = ['CNN', 'BBC', 'NHK', 'KBS', 'SBS', 'MBC', 'FOX',
                         'HBO', 'CINEMAX', '卫视电影', '卫视体育', '卫视中文',
                         'DISCOVERY', 'NGC', 'HISTORY', 'DW', 'FRANCE', 'ALJAZEERA',
                         'BLOOMBERG', 'CNBC', 'ABC', 'NBC', 'CBS']
    for kw in overseas_keywords:
        if kw in name:
            return '海外', channel_name.strip()
    
    # ----- 其他分类 -----
    return '其他', channel_name.strip()

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
    
    # 分类并标准化名称
    print("\n🔍 正在分类和标准化频道名...")
    
    current_date = time.strftime('%y%m%d')
    current_time_full = time.strftime('%Y-%m-%d %H:%M:%S')
    
    # 存储标准化后的频道对象，同时保留原始名用于去重
    processed_channels = []
    category_stats = {cat: 0 for cat in ['央视', '卫视', '4K', '港澳', '海外', '其他', current_date]}
    
    for ch in all_channels:
        category, sort_key = get_channel_category(ch['name'])
        
        # 标准化央视名称
        if category == '央视':
            display_name = sort_key  # sort_key已经是标准化后的CCTV名称
        else:
            display_name = ch['name'].strip()
        
        processed_channels.append({
            'display_name': display_name,
            'sort_key': sort_key,
            'category': category,
            'url': ch['url'],
            'source': ch['source']
        })
        category_stats[category] += 1
    
    # 按分类和排序键分组
    channels_by_category = {cat: {} for cat in ['央视', '卫视', '4K', '港澳', '海外', '其他', current_date]}
    
    for ch in processed_channels:
        cat = ch['category']
        key = ch['sort_key']  # 卫视这里存的是去掉“卫视”后的名字，用于排序
        
        if key not in channels_by_category[cat]:
            channels_by_category[cat][key] = []
        channels_by_category[cat][key].append(ch)
    
    # 输出统计
    print("📊 分类统计：")
    for cat in ['央视', '卫视', '4K', '港澳', '海外', '其他']:
        if category_stats[cat] > 0:
            print(f"   {cat}: {category_stats[cat]} 个")
    
    # 写入文件
    print(f"\n💾 正在写入TXT文件: {OUTPUT_FILE}")
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(f"# 自动聚合直播源 - 生成时间: {current_time_full}\n")
        f.write(f"# 总频道数: {len(processed_channels)} | 分类: 央视/卫视/4K/港澳/海外/其他/日期\n\n")
        
        # ----- 央视分类 (按CCTV_ORDER排序) -----
        cctv_dict = channels_by_category['央视']
        if cctv_dict:
            f.write(f"\n央视,#genre#\n")
            # 先按指定顺序写入1-17
            written = set()
            for std_name in CCTV_ORDER:
                if std_name in cctv_dict:
                    for ch in cctv_dict[std_name]:
                        f.write(f"{ch['display_name']},{ch['url']}\n")
                    written.add(std_name)
            # 再写入其他央视（如CCTVNews等）按字母顺序
            others = sorted([k for k in cctv_dict.keys() if k not in written])
            for key in others:
                for ch in cctv_dict[key]:
                    f.write(f"{ch['display_name']},{ch['url']}\n")
        
        # ----- 卫视分类 (指定顺序+拼音) -----
        weishi_dict = channels_by_category['卫视']
        if weishi_dict:
            f.write(f"\n卫视,#genre#\n")
            # 指定顺序
            priority = ['湖南', '浙江', '北京', '东方']
            written = set()
            for p in priority:
                if p in weishi_dict:
                    for ch in weishi_dict[p]:
                        f.write(f"{ch['display_name']},{ch['url']}\n")
                    written.add(p)
            # 其余按拼音排序
            others = sorted([k for k in weishi_dict.keys() if k not in written])
            for key in others:
                for ch in weishi_dict[key]:
                    f.write(f"{ch['display_name']},{ch['url']}\n")
        
        # ----- 4K分类 (拼音排序) -----
        dict_4k = channels_by_category['4K']
        if dict_4k:
            f.write(f"\n4K,#genre#\n")
            for key in sorted(dict_4k.keys()):
                for ch in dict_4k[key]:
                    f.write(f"{ch['display_name']},{ch['url']}\n")
        
        # ----- 港澳分类 (拼音排序) -----
        dict_gangao = channels_by_category['港澳']
        if dict_gangao:
            f.write(f"\n港澳,#genre#\n")
            for key in sorted(dict_gangao.keys()):
                for ch in dict_gangao[key]:
                    f.write(f"{ch['display_name']},{ch['url']}\n")
        
        # ----- 海外分类 (拼音排序) -----
        dict_overseas = channels_by_category['海外']
        if dict_overseas:
            f.write(f"\n海外,#genre#\n")
            for key in sorted(dict_overseas.keys()):
                for ch in dict_overseas[key]:
                    f.write(f"{ch['display_name']},{ch['url']}\n")
        
        # ----- 其他分类 (拼音排序) -----
        dict_other = channels_by_category['其他']
        if dict_other:
            f.write(f"\n其他,#genre#\n")
            for key in sorted(dict_other.keys()):
                for ch in dict_other[key]:
                    f.write(f"{ch['display_name']},{ch['url']}\n")
        
        # ----- 日期分类 (统计数据) -----
        f.write(f"\n{current_date},#genre#\n")
        f.write(f"更新时间 本频道列表更新于 {current_time_full}\n")
        f.write(f"总频道数 {len(processed_channels)} 个\n")
        for cat in ['央视', '卫视', '4K', '港澳', '海外', '其他']:
            if category_stats[cat] > 0:
                f.write(f"{cat} {category_stats[cat]} 个\n")
        
        # 文件末尾信息
        f.write(f"\n\n# ========================================\n")
        f.write(f"# 文件生成时间: {current_time_full}\n")
        f.write(f"# 总频道数量: {len(processed_channels)} 个\n")
        f.write(f"# 来源数量: {len(SOURCE_URLS)} 个\n")
        for cat in ['央视', '卫视', '4K', '港澳', '海外', '其他']:
            if category_stats[cat] > 0:
                f.write(f"#   {cat}: {category_stats[cat]} 个\n")
        f.write(f"# ========================================\n")
    
    print(f"✅ 完成！")
    print(f"   📊 总共 {len(processed_channels)} 个频道")
    print(f"   📁 保存到: {OUTPUT_FILE}")
    print("=" * 60)

if __name__ == "__main__":
    fetch_and_merge()
