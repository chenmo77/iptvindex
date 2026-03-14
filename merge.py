import requests
import time
import re
import socket
import ipaddress
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
    # 在这里继续添加源地址，TXT或M3U格式都支持
]

# ================ 🔧 配置区域 2：输出设置 ================
OUTPUT_FILE = "live.txt"
ADD_ISP_TAG = True  # 是否自动添加运营商标记
# ================================================================

# 中国主要运营商IP段（精简常用段）
CHINA_IPS = {
    'telecom': [  # 电信
        '1.0.0.0/24', '1.2.0.0/16', '14.0.0.0/14', '27.8.0.0/13',
        '36.0.0.0/11', '39.0.0.0/12', '42.48.0.0/13', '49.52.0.0/14',
        '58.16.0.0/13', '59.32.0.0/11', '60.0.0.0/11', '61.128.0.0/10',
        '101.64.0.0/13', '110.80.0.0/13', '111.0.0.0/10', '112.0.0.0/10',
        '113.64.0.0/10', '114.80.0.0/12', '115.48.0.0/12', '116.192.0.0/12',
        '117.136.0.0/13', '118.112.0.0/13', '119.128.0.0/12', '120.192.0.0/10',
        '121.32.0.0/11', '122.64.0.0/11', '123.128.0.0/13', '124.64.0.0/15',
        '125.64.0.0/11', '175.0.0.0/12', '180.96.0.0/11', '182.112.0.0/12',
        '183.128.0.0/11', '202.96.0.0/12', '218.0.0.0/11', '219.128.0.0/11',
        '220.160.0.0/11', '221.0.0.0/12', '222.64.0.0/11', '223.0.0.0/12'
    ],
    'unicom': [  # 联通
        '27.184.0.0/13', '36.96.0.0/12', '39.64.0.0/11', '42.0.0.0/12',
        '49.64.0.0/11', '58.240.0.0/12', '60.208.0.0/12', '61.48.0.0/12',
        '101.16.0.0/12', '106.32.0.0/12', '110.96.0.0/11', '111.160.0.0/13',
        '112.96.0.0/12', '113.128.0.0/10', '115.24.0.0/14', '116.224.0.0/12',
        '117.8.0.0/13', '118.80.0.0/13', '119.112.0.0/13', '120.0.0.0/12',
        '121.16.0.0/12', '122.96.0.0/11', '123.160.0.0/12', '124.128.0.0/13',
        '175.148.0.0/14', '182.32.0.0/12', '183.160.0.0/12', '202.96.0.0/12',
        '210.192.0.0/11', '218.56.0.0/13', '219.148.0.0/14', '220.192.0.0/12',
        '221.192.0.0/13', '222.160.0.0/12'
    ],
    'mobile': [  # 移动
        '36.128.0.0/10', '39.128.0.0/10', '111.0.0.0/10', '112.0.0.0/10',
        '117.128.0.0/10', '120.192.0.0/10', '183.192.0.0/10', '211.136.0.0/13',
        '211.144.0.0/12', '218.200.0.0/13', '218.206.0.0/15', '219.156.0.0/15',
        '221.176.0.0/13', '222.128.0.0/12', '223.96.0.0/12'
    ]
}

# 港澳台及海外常用域名后缀（用于辅助判断）
OVERSEAS_KEYWORDS = [
    '.hk', '.tw', '.mo', '.uk', '.jp', '.kr', '.us', '.sg', '.my', '.th',
    'youtube', 'twitch', 'akamaized', 'cloudfront', 'netflix'
]

# DNS缓存，避免重复解析
DNS_CACHE = {}

def get_ip_from_url(url):
    """从URL中提取域名并解析IP地址"""
    try:
        # 提取域名
        domain_match = re.match(r'https?://([^/:]+)', url)
        if not domain_match:
            return None
        
        domain = domain_match.group(1)
        
        # 如果本身就是IP
        try:
            ipaddress.ip_address(domain)
            return domain
        except ValueError:
            pass
        
        # 查DNS缓存
        if domain in DNS_CACHE:
            return DNS_CACHE[domain]
        
        # 解析域名
        ip = socket.gethostbyname(domain)
        DNS_CACHE[domain] = ip
        return ip
    except Exception:
        return None

def is_ip_in_network(ip, network_cidr):
    """判断IP是否在某个网段内"""
    try:
        ip_obj = ipaddress.ip_address(ip)
        network = ipaddress.ip_network(network_cidr)
        return ip_obj in network
    except Exception:
        return False

def detect_isp_from_ip(ip):
    """根据IP判断运营商"""
    if not ip:
        return 'unknown'
    
    for isp, networks in CHINA_IPS.items():
        for network in networks:
            if is_ip_in_network(ip, network):
                return isp
    
    return 'foreign'

def is_likely_overseas_by_domain(url):
    """通过域名后缀判断是否为海外源"""
    url_lower = url.lower()
    for keyword in OVERSEAS_KEYWORDS:
        if keyword in url_lower:
            return True
    return False

def isp_to_tag(isp, url):
    """运营商代码转标记（海外源标记为#海外，无法判断的标记为#全网）"""
    # 先通过域名辅助判断
    if is_likely_overseas_by_domain(url):
        return '#海外'
    
    isp_map = {
        'telecom': '#电信',
        'unicom': '#联通',
        'mobile': '#移动',
        'foreign': '#海外',  # 海外IP标记为海外
        'unknown': '#全网'   # 无法判断的标记为全网
    }
    return isp_map.get(isp, '#全网')

def get_channel_category(channel_name):
    """根据频道名判断所属分类"""
    name = channel_name.upper()
    
    # 央视分类
    cctv_keywords = ['CCTV', '中央', '央视', 'CETV', 'CGTN']
    for kw in cctv_keywords:
        if kw in name:
            return '央视,#genre#'
    
    # 4K分类
    if '4K' in name or '4k' in channel_name or '超清' in name:
        return '4K,#genre#'
    
    # 卫视分类
    weishi_keywords = ['卫视', '湖南', '浙江', '江苏', '东方', '北京', '深圳', '广东', 
                       '安徽', '山东', '天津', '重庆', '黑龙江', '辽宁', '吉林', '湖北',
                       '江西', '广西', '内蒙古', '宁夏', '青海', '陕西', '山西', '河北',
                       '河南', '云南', '贵州', '四川', '福建', '海南', '甘肃', '新疆',
                       '东南', '旅游', '金鹰', '卡酷', '炫动', '优漫', 'BRTV', 'BTV']
    for kw in weishi_keywords:
        if kw in name:
            return '卫视,#genre#'
    
    # 港澳分类
    gangao_keywords = ['香港', '澳门', 'TVB', '明珠', '翡翠', 'J2', '互动新闻', 
                       '无线', '凤凰', 'HK', 'MACAU', '澳亚', '莲花', '澳视']
    for kw in gangao_keywords:
        if kw in name:
            return '港澳,#genre#'
    
    # 海外分类
    overseas_keywords = ['CNN', 'BBC', 'NHK', 'KBS', 'SBS', 'MBC', 'TVB', 'FOX', 
                         'HBO', 'CINEMAX', '卫视电影', '卫视体育', '卫视中文',
                         'Discovery', 'National Geographic', 'HISTORY', 'DW',
                         'FRANCE', 'ALJAZEERA', 'CGTN', 'RT', 'TRT', 'EURONEWS',
                         'Bloomberg', 'CNBC', 'ABC', 'NBC', 'CBS', 'FOX']
    for kw in overseas_keywords:
        if kw in name:
            return '海外,#genre#'
    
    # 默认为其他
    return '其他,#genre#'

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

def get_isp_tag_for_url(url):
    """获取URL对应的运营商标记"""
    ip = get_ip_from_url(url)
    if ip:
        isp = detect_isp_from_ip(ip)
        return isp_to_tag(isp, url)
    return isp_to_tag('unknown', url)  # 解析失败也走统一逻辑

def fetch_and_merge():
    all_channels = []
    
    print("=" * 60)
    print("🚀 开始抓取直播源（快速模式：只识别运营商，不测速）...")
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
    
    # 2. 识别每个频道的运营商和分类
    print("\n🔍 正在识别运营商和分类...")
    print("-" * 60)
    
    # 统计各分类数量
    category_stats = {
        '央视': 0, '卫视': 0, '4K': 0, 
        '港澳': 0, '海外': 0, '其他': 0
    }
    # 统计运营商标记
    isp_stats = {'#电信': 0, '#联通': 0, '#移动': 0, '#海外': 0, '#全网': 0}
    
    for i, ch in enumerate(all_channels, 1):
        # 获取分类
        ch['category'] = get_channel_category(ch['name'])
        
        # 获取运营商标记
        isp_tag = get_isp_tag_for_url(ch['url'])
        ch['isp_tag'] = isp_tag
        
        # 更新统计
        category_name = ch['category'].split(',')[0]
        category_stats[category_name] = category_stats.get(category_name, 0) + 1
        isp_stats[isp_tag] = isp_stats.get(isp_tag, 0) + 1
        
        # 每20个显示一次进度
        if i % 20 == 0 or i == len(all_channels):
            print(f"   已处理 {i}/{len(all_channels)} 个频道...")
    
    print("-" * 60)
    print("📊 分类统计：")
    for cat, count in category_stats.items():
        if count > 0:
            print(f"   {cat}: {count} 个")
    print("\n📊 运营商标记统计：")
    for isp, count in isp_stats.items():
        if count > 0:
            print(f"   {isp}: {count} 个")
    
    # 3. 按分类和频道名分组
    channels_by_category = {
        '央视': {},
        '卫视': {},
        '4K': {},
        '港澳': {},
        '海外': {},
        '其他': {}
    }
    
    for ch in all_channels:
        category = ch['category'].split(',')[0]
        if ch['name'] not in channels_by_category[category]:
            channels_by_category[category][ch['name']] = []
        channels_by_category[category][ch['name']].append(ch)
    
    # 4. 写入最终文件
    print(f"\n💾 正在写入TXT文件: {OUTPUT_FILE}")
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(f"# 自动聚合直播源 - 生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"# 总频道数: {len(all_channels)} | 分类: 央视/卫视/4K/港澳/海外/其他\n")
        f.write(f"# 运营商标记: {'开启' if ADD_ISP_TAG else '关闭'}（电信/联通/移动/海外/全网）\n\n")
        
        # 按分类顺序写入
        category_order = ['央视', '卫视', '4K', '港澳', '海外', '其他']
        
        for category in category_order:
            channels_dict = channels_by_category[category]
            if not channels_dict:
                continue
            
            # 写入分类标题
            f.write(f"\n{category},#genre#\n")
            
            # 按频道名排序写入
            for channel_name in sorted(channels_dict.keys()):
                for ch in channels_dict[channel_name]:
                    if ADD_ISP_TAG:
                        f.write(f"{ch['name']},{ch['url']} {ch['isp_tag']}\n")
                    else:
                        f.write(f"{ch['name']},{ch['url']}\n")
    
    print(f"✅ 完成！")
    print(f"   📊 总共 {len(all_channels)} 个频道")
    print(f"   📁 保存到: {OUTPUT_FILE}")
    print("=" * 60)

if __name__ == "__main__":
    fetch_and_merge()
