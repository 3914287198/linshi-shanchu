# -*- coding: utf-8 -*-
import requests
import json
import time
import re
from datetime import datetime

# 全局关闭警告
requests.packages.urllib3.disable_warnings()

# ===================== 核心配置 =====================
base_url = "https://myhkw.cn/action/songsheet"

# 极简标准请求头（服务器只认这个，多了反而500）
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36 Edg/148.0.0.0",
    "Referer": "https://myhkw.cn/admin/",
    "X-Requested-With": "XMLHttpRequest",
    "Accept": "application/json, text/javascript, */*; q=0.01",
}

# 【必须手动更新】去浏览器重新复制最新的 PHPSESSID
cookies = {
    "PHPSESSID": "2edfe8de111ea34a5a88b20e1554f6df"
}

# 参数顺序严格按照浏览器真实顺序（服务器校验顺序！）
params = {
    "id": "music172618394697",
    "page": 1,
    "limit": 90
}
# =====================================================

# 创建会话（必须用这个，否则必500）
session = requests.Session()
session.headers.update(headers)
session.cookies.update(cookies)

all_data = []
total_count = 0
CONTINUOUS_SAME_THRESHOLD = 3
same_data_page_count = 0
prev_total_length = 0

def resolve_location(song_id):
    """
    通过访问歌曲详情页解析真实的 location 地址
    """
    if not song_id:
        return ""
    
    detail_url = f"https://myhkw.cn/admin/song/{song_id}"
    try:
        resp = session.get(
            detail_url,
            verify=False,
            timeout=10
        )
        if resp.status_code != 200:
            return ""
            
        # 改进的正则提取逻辑
        # 1. 提取完整的 input 标签
        input_tag_match = re.search(r'<input[^>]+name="location"[^>]*>', resp.text, re.I)
        if input_tag_match:
            tag_content = input_tag_match.group(0)
            # 2. 从标签中提取 value 属性值，考虑空格和可能存在的反引号
            # 匹配 value=" 任意字符 " 或 value=' 任意字符 '
            value_match = re.search(r'value=["\'](.*?)(?=["\'])', tag_content, re.I)
            if value_match:
                real_url = value_match.group(1).strip()
                # 移除可能存在的包裹反引号
                real_url = real_url.strip("`").strip()
                # 替换 &amp; 为 &
                real_url = real_url.replace("&amp;", "&")
                return real_url
        
        # 备选方案：如果上面的没匹配到，尝试直接在全文搜包含 location 的 value
        fallback_match = re.search(r'name="location".*?value=["\']\s*`?([^"\'`\s>]+)`?\s*["\']', resp.text, re.S | re.I)
        if fallback_match:
            real_url = fallback_match.group(1).replace("&amp;", "&")
            return real_url
            
        return ""
    except Exception as e:
        print(f"解析地址失败 [{song_id}]: {e}")
        return ""

def try_request(page):
    params["page"] = page
    for attempt in range(2):
        try:
            # 极简请求，只保留必要参数
            resp = session.get(
                base_url,
                params=params,
                verify=False,
                timeout=10
            )
            # 500直接重试
            if resp.status_code == 500:
                print(f"第{page}页 服务器500，重试中...")
                time.sleep(2)
                continue
            return resp
        except:
            time.sleep(2)
    return None

# ===================== 开始爬取 =====================
try:
    print("开始获取数据...")

    for page in range(1, 20):
        print(f"正在获取第 {page} 页...")
        res = try_request(page)
        if not res:
            print("请求失败，跳过")
            time.sleep(2)
            continue

        # 解析数据
        try:
            data = res.json()
        except:
            print("返回非JSON，跳过")
            time.sleep(2)
            continue

        # 接口返回错误
        if data.get("code") != 0:
            print(f"接口错误：{data.get('msg')}")
            break

        # 追加数据
        song_list = data.get("data", [])
        
        # 遍历解析加密地址
        for i, song in enumerate(song_list):
            name = song.get("name", "未知")
            # 提取干净的歌名（去掉 HTML 标签）
            clean_name = re.sub(r'<[^>]+>', '', name).strip()
            song_db_id = song.get("id")
            if song_db_id:
                print(f"  [{i+1}/{len(song_list)}] 正在解析: {clean_name}")
                real_location = resolve_location(song_db_id)
                if real_location:
                    song["location"] = real_location
        
        all_data.extend(song_list)

        print(f"第{page}页成功 → 本次{len(song_list)}条，累计{len(all_data)}条")

        # 无数据自动停止
        if len(song_list) == 0:
            same_data_page_count +=1
            if same_data_page_count >= CONTINUOUS_SAME_THRESHOLD:
                print("连续无数据，停止爬取")
                break
        else:
            same_data_page_count =0

        time.sleep(1.5)

    # 保存文件
    filename = f"{datetime.now().strftime('%Y-%m-%d')}-{len(all_data)}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump({
            "code":0,
            "count": len(all_data),
            "data": all_data
        }, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 全部完成！共 {len(all_data)} 条，已保存到：{filename}")

except Exception as e:
    print(f"错误：{e}")
