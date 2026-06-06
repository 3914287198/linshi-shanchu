# -*- coding: utf-8 -*-
import requests
import json
import time
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

# PHPSESSID直接写死，不再读取环境变量
cookies = {
    "PHPSESSID": "b23f9e44c1a857702b62b155d76dd0aa"
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
CONTINUOUS_SAME_THRESHOLD = 3
same_data_page_count = 0

def resolve_location(url):
    """
    解析加密的 location 地址
    通过禁止重定向获取返回协议头中的真实地址
    """
    if not url or not url.startswith("http"):
        return url
    try:
        # 极简请求，禁止重定向
        resp = session.get(
            url,
            verify=False,
            timeout=10,
            allow_redirects=False
        )
        # 从响应头中获取 Location
        real_url = resp.headers.get("Location")
        if real_url:
            return real_url
        return url
    except Exception as e:
        print(f"解析地址失败: {e}")
        return url

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
            original_url = song.get("location")
            if original_url:
                print(f"  [{i+1}/{len(song_list)}] 正在解析: {name}")
                song["location"] = resolve_location(original_url)
        
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

    # 保存文件【当前项目根目录】
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