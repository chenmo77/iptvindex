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
OUTPUT_FILE = "live.txt"  # 最终生成的文件名
# ================================================================

def get_channel_category(channel_name):
    """根据频道名判断所属分类"""
    name = channel_name.upper()
    
    # 央视分类
    cctv_keywords = ['CCTV', '中央', '央视', 'CETV', 'CGTN']
    for kw in cctv_keywords:
        if kw in name:
            return '央视'
    
    # 4K分类
    if '4K' in name or '4k' in channel_name or '超清' in name or 'UHD' in name:
        return '4K'
    
    # 卫视分类
    weishi_keywords = ['卫视', '湖南', '浙江', '江苏', '东方', '北京', '深圳', '广东', 
                       '安徽', '山东', '天津', '重庆', '黑龙江', '辽宁', '吉林', '湖北',
                       '江西', '广西', '内蒙古', '宁夏', '青海', '陕西', '山西', '河北',
                       '河南', '云南', '贵州', '四川', '福建', '海南', '甘肃', '新疆',
                       '东南', '旅游', '金鹰', '卡酷', '炫动', '优漫', 'BRTV', 'BTV']
    for kw in weishi_keywords:
        if kw in name:
            return '卫视'
    
    # 港澳分类
    gangao_keywords = ['香港', '澳门', 'TVB', '明珠', '翡翠', 'J2', '互动新闻', 
                       '无线', '凤凰', 'HK', 'MACAU', '澳亚', '莲花', '澳视']
    for kw in gangao_keywords:
        if kw in name:
            return '港澳'
    
    # 海外分类
    overseas_keywords = ['CNN', 'BBC', 'NHK', 'KBS', 'SBS', 'MBC', 'FOX', 
                         'HBO', 'CINEMAX', '卫视电影', '卫视体育', '卫视中文',
                         'DISCOVERY', 'NGC', 'HISTORY', 'DW', 'FRANCE', 'ALJAZEERA',
                         'BLOOMBERG', 'CNBC', 'ABC', 'NBC', 'CBS']
    for kw in overseas_keywords:
        if kw in name:
            return '海外'
    
    # 默认为其他
    return '其他'

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
            # 去掉可能存在的注释
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
            # 提取频道名称
            name_match = re.search(r',([^,]+)$', line)
            if name_match:
                channel_name = name_match.group(1).strip()
                
                # 下一行应该是URL
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
    print("🚀 开始抓取直播源（极速模式：只合并分类，不测速）...")
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
    
    print(f"\n📊 共抓取到 {len(all_channels)} 个频道")
    
    # 2. 为每个频道分类
    print("\n🔍 正在分类频道...")
    
    # 获取当前日期，用于日期分类
    current_date = time.strftime('%y%m%d')  # 格式：260314
    current_time_full = time.strftime('%Y-%m-%d %H:%M:%S')
    
    # 统计各分类数量
    category_stats = {
        '央视': 0, '卫视': 0, '4K': 0, 
        '港澳': 0, '海外': 0, '其他': 0,
        current_date: 0  # 添加日期分类
    }
    
    for ch in all_channels:
        ch['category'] = get_channel_category(ch['name'])
        category_stats[ch['category']] = category_stats.get(ch['category'], 0) + 1
    
    print("📊 分类统计：")
    for cat, count in category_stats.items():
        if count > 0 and cat != current_date:  # 日期分类暂时没频道，稍后手动加
            print(f"   {cat}: {count} 个")
    
    # 3. 按分类和频道名分组（保留所有源）
    # 定义所有分类（包括动态日期分类）
    all_categories = ['央视', '卫视', '4K', '港澳', '海外', '其他', current_date]
    
    channels_by_category = {cat: {} for cat in all_categories}
    
    for ch in all_channels:
        category = ch['category']
        if ch['name'] not in channels_by_category[category]:
            channels_by_category[category][ch['name']] = []
        channels_by_category[category][ch['name']].append(ch)
    
    # 4. 写入最终文件
    print(f"\n💾 正在写入TXT文件: {OUTPUT_FILE}")
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(f"# 自动聚合直播源 - 生成时间: {current_time_full}\n")
        f.write(f"# 总频道数: {len(all_channels)} | 分类: 央视/卫视/4K/港澳/海外/其他/日期\n")
        f.write(f"# 注：同一个频道可能有多个源地址，全部保留\n\n")
        
        # 按分类顺序写入（央视、卫视、4K、港澳、海外、其他、日期）
        category_order = ['央视', '卫视', '4K', '港澳', '海外', '其他', current_date]
        
        for category in category_order:
            channels_dict = channels_by_category[category]
            
            if category == current_date:
                # 日期分类：只放一条说明信息
                f.write(f"\n{category},#genre#\n")
                f.write(f"更新时间,本频道列表更新于 {current_time_full}\n")
                f.write(f"总频道数,共 {len(all_channels)} 个频道\n")
                for cat, count in category_stats.items():
                    if cat != current_date and count > 0:
                        f.write(f"{cat}频道,{count} 个\n")
            else:
                # 正常分类
                if not channels_dict:
                    continue
                
                f.write(f"\n{category},#genre#\n")
                
                # 按频道名排序写入
                for channel_name in sorted(channels_dict.keys()):
                    for ch in channels_dict[channel_name]:
                        f.write(f"{ch['name']},{ch['url']}\n")
        
        # 在文件末尾添加时间标记
        f.write(f"\n\n# ========================================\n")
        f.write(f"# 文件生成时间: {current_time_full}\n")
        f.write(f"# 总频道数量: {len(all_channels)} 个\n")
        f.write(f"# 来源数量: {len(SOURCE_URLS)} 个\n")
        f.write(f"# 分类详情:\n")
        for cat, count in category_stats.items():
            if count > 0:
                f.write(f"#   {cat}: {count} 个\n")
        f.write(f"# ========================================\n")
    
    print(f"✅ 完成！")
    print(f"   📊 总共 {len(all_channels)} 个频道")
    print(f"   📋 涉及 {sum(len(v) for v in channels_by_category.values())} 个不同的频道名")
    print(f"   📁 保存到: {OUTPUT_FILE}")
    print(f"   🕐 日期分类: {current_date}（已添加）")
    print("=" * 60)

if __name__ == "__main__":
    fetch_and_merge()
