import requests
import time
import re
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ================ 🔧 配置区域 ================
# 1. 您的蓝本文件地址 (zb.txt)
MASTER_FILE_URL = "https://raw.githubusercontent.com/chenmo77/iptvindex/refs/heads/main/zb.txt"
# 2. 您自定义的其他直播源列表
CUSTOM_SOURCES = [
    ("中国", "https://raw.githubusercontent.com/iptv-org/iptv/refs/heads/master/streams/cn.m3u"),
    ("TW", "https://raw.githubusercontent.com/iptv-org/iptv/refs/heads/master/streams/tw.m3u"),
    ("HK", "https://raw.githubusercontent.com/iptv-org/iptv/refs/heads/master/streams/hk.m3u"),
    ("漂亮国", "https://raw.githubusercontent.com/iptv-org/iptv/refs/heads/master/streams/us.m3u"),
    ("大毛子", "https://raw.githubusercontent.com/iptv-org/iptv/refs/heads/master/streams/ru.m3u"),
    ("大不列", "https://raw.githubusercontent.com/iptv-org/iptv/refs/heads/master/streams/uk_bbc.m3u"),
    ("小日子", "https://raw.githubusercontent.com/iptv-org/iptv/refs/heads/master/streams/jp.m3u"),
    ("samsung", "https://raw.githubusercontent.com/iptv-org/iptv/refs/heads/master/streams/uk_samsung.m3u"),
    ("先锋", "http://ge.html-5.me//ii/%E9%BB%84%E8%9A%82%E8%9A%81%E5%85%88%E9%94%8B%E6%8E%A8%E6%B5%81%E6%BA%90.txt"),
    ("iptvz", "https://raw.githubusercontent.com/q1017673817/iptvz/refs/heads/main/zubo_all.txt"),
    ("zbds", "https://live.zbds.org/tv/iptv4.txt"),
    ("咪咕", "https://raw.githubusercontent.com/develop202/migu_video/refs/heads/main/interface.txt"),
    ("Guovin", "https://raw.githubusercontent.com/Guovin/iptv-api/gd/output/result.txt"),
    ("alan", "https://raw.githubusercontent.com/alantang1977/aTV/refs/heads/master/output/result.txt"),
    ("YY", "https://raw.githubusercontent.com/mursor1985/LIVE/refs/heads/main/yylunbo.m3u"),
    ("虎牙", "https://raw.githubusercontent.com/mursor1985/LIVE/refs/heads/main/huyayqk.m3u"),
    ("斗鱼", "https://raw.githubusercontent.com/mursor1985/LIVE/refs/heads/main/douyuyqk.m3u")
]
# 3. 输出文件配置
OUTPUT_TXT = "live.txt"
OUTPUT_M3U = "live.m3u"
# 4. EPG配置（双EPG源，逗号分隔）
EPG_URLS = "http://epg.cdn.loc.cc,https://diyp.epg.qzz.io/"
# =============================================

# 模拟浏览器的请求头，解决反爬虫问题
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Cache-Control": "max-age=0"
}

def create_session_with_retry(retries=3, backoff_factor=0.3):
    """创建带有重试机制的requests会话"""
    session = requests.Session()
    
    # 配置重试策略
    retry_strategy = Retry(
        total=retries,
        backoff_factor=backoff_factor,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"]
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    # 设置全局请求头
    session.headers.update(HEADERS)
    
    return session

# 创建全局会话
session = create_session_with_retry()

def fetch_file_content(url):
    """获取远程文件内容（增强版：支持反爬虫、重试和自动编码检测）"""
    try:
        print(f"📡 正在抓取: {url}")
        
        # 使用带有重试机制的会话发送请求
        response = session.get(url, timeout=15)  # 延长超时时间到15秒
        response.raise_for_status()  # 抛出HTTP错误状态码异常
        
        # 自动检测编码，避免乱码
        if response.encoding == 'ISO-8859-1':
            response.encoding = response.apparent_encoding
        
        return response.text
    except requests.exceptions.HTTPError as e:
        print(f"   ❌ HTTP错误: {e.response.status_code} {e.response.reason}")
        return None
    except requests.exceptions.ConnectionError:
        print(f"   ❌ 连接错误：无法连接到服务器")
        return None
    except requests.exceptions.Timeout:
        print(f"   ❌ 请求超时：服务器响应时间过长")
        return None
    except Exception as e:
        print(f"   ❌ 抓取失败: {str(e)}")
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

def convert_to_m3u(txt_lines):
    """
    将TXT格式的直播源转换为标准精简M3U格式
    支持双EPG源，自动处理分组和分类，无台标图片
    """
    # M3U文件头，包含双EPG配置
    m3u_lines = [f'#EXTM3U x-tvg-url="{EPG_URLS}"']
    
    current_group = "未分类"
    current_genre = ""
    
    for line in txt_lines:
        line = line.strip()
        if not line:
            continue
            
        # 处理分组标记（跳过日期格式的分组）
        if ",#group#" in line:
            group_name = line.split(",#group#")[0].strip()
            # 跳过6位数字的日期分组（如260527）
            if group_name.isdigit() and len(group_name) == 6:
                continue
            current_group = group_name
            current_genre = ""
            continue
            
        # 处理分类标记
        if ",#genre#" in line:
            current_genre = line.split(",#genre#")[0].strip()
            continue
            
        # 处理频道行（只分割第一个逗号，避免URL中包含逗号的情况）
        parts = line.split(",", 1)
        if len(parts) != 2:
            continue
            
        channel_name = parts[0].strip().replace('"', "'")  # 替换双引号避免格式错误
        channel_url = parts[1].strip()
        
        if not channel_name or not channel_url:
            continue
            
        # 构建分组标题（分组/分类）
        if current_genre:
            group_title = f"{current_group}/{current_genre}"
        else:
            group_title = current_group
            
        # 生成标准M3U行（无台标，精简属性）
        m3u_lines.append(f'#EXTINF:-1 tvg-id="{channel_name}" tvg-name="{channel_name}" group-title="{group_title}",{channel_name}')
        m3u_lines.append(channel_url)
    
    return '\n'.join(m3u_lines)

def main():
    print("=" * 70)
    print("🚀 开始合并直播源（智能解析M3U分类 + 双格式输出）...")
    print("=" * 70)
    
    # 1. 获取蓝本文件
    master_content = fetch_file_content(MASTER_FILE_URL)
    if not master_content:
        print("❌ 无法获取蓝本文件，程序终止")
        return
    
    # 2. 构建最终TXT格式内容
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
                    valid_lines = [l.rstrip() for l in source_lines if l.strip()]
                    final_lines.extend(valid_lines)
                    print(f"   ✅ 添加 {len(valid_lines)} 行有效内容")
                else:
                    print(f"   ⚠️ 该源无有效内容")
            
            final_lines.append("温馨提示,#group#")
            custom_inserted = True
            print(f"\n📝 已插入 {len(CUSTOM_SOURCES)} 个自定义源")
    
    # 3. 将“温馨提示”改为“生成日期”
    current_date = time.strftime('%y%m%d')
    final_lines = [line.replace("温馨提示,#group#", f"{current_date},#group#") for line in final_lines]
    
    # 4. 写入TXT文件
    print(f"\n💾 正在写入TXT文件: {OUTPUT_TXT}")
    with open(OUTPUT_TXT, 'w', encoding='utf-8') as f:
        f.write('\n'.join(final_lines))
    
    txt_channel_count = len([l for l in final_lines if ',' in l and not l.endswith(('#group#', '#genre#'))])
    print(f"   ✅ TXT文件生成完成")
    print(f"   📊 TXT频道数: {txt_channel_count}")
    
    # 5. 生成并写入M3U文件
    print(f"\n💾 正在生成M3U文件: {OUTPUT_M3U}")
    m3u_content = convert_to_m3u(final_lines)
    with open(OUTPUT_M3U, 'w', encoding='utf-8') as f:
        f.write(m3u_content)
    
    m3u_channel_count = len([l for l in m3u_content.split('\n') if l.startswith('#EXTINF:')])
    print(f"   ✅ M3U文件生成完成")
    print(f"   📊 M3U频道数: {m3u_channel_count}")
    print(f"   📡 EPG源: {EPG_URLS}")
    
    # 6. 最终统计
    print(f"\n✅ 全部任务完成！")
    print(f"   📁 输出文件: {OUTPUT_TXT}, {OUTPUT_M3U}")
    print(f"   🕐 生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

if __name__ == "__main__":
    main()
