import os
import time
import requests
import cloudinary
import cloudinary.uploader

# ── 環境變數 ──────────────────────────────────────────
NOTION_TOKEN          = os.environ["NOTION_API_KEY"]
DATABASE_ID           = "344c699d3b59801a9c01d7d074633983"   # 限時動態資料庫
IG_USER_ID            = os.environ["IG_USER_ID"]
IG_ACCESS_TOKEN       = os.environ["IG_ACCESS_TOKEN"]
CLOUDINARY_CLOUD_NAME = os.environ["CLOUDINARY_CLOUD_NAME"]
CLOUDINARY_API_KEY    = os.environ["CLOUDINARY_API_KEY"]
CLOUDINARY_API_SECRET = os.environ["CLOUDINARY_API_SECRET"]
TELEGRAM_TOKEN        = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID      = os.environ["TELEGRAM_CHAT_ID"]

cloudinary.config(
    cloud_name=CLOUDINARY_CLOUD_NAME,
    api_key=CLOUDINARY_API_KEY,
    api_secret=CLOUDINARY_API_SECRET
)

headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

# ── Notion：取得待發項目 ──────────────────────────────
def get_pending_stories():
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    res = requests.post(url, headers=headers, json={
        "filter": {
            "property": "狀態",
            "status": { "equals": "待發" }
        },
        "page_size": 1
    })
    results = res.json().get("results", [])
    print(f"找到 {len(results)} 筆待發限時動態")
    return results[0] if results else None

# ── Notion：取得圖片 URL 清單 ─────────────────────────
def get_image_urls(post):
    files = post["properties"].get("圖片", {}).get("files", [])
    urls = []
    for f in files:
        if f["type"] == "file":
            urls.append(f["file"]["url"])
        elif f["type"] == "external":
            urls.append(f["external"]["url"])
    print(f"取得 {len(urls)} 張圖片")
    return urls

# ── Cloudinary：上傳圖片 ──────────────────────────────
def upload_images(image_urls):
    uploaded = []
    for i, url in enumerate(image_urls):
        result = cloudinary.uploader.upload(url)
        cdn_url = result.get("secure_url")
        if cdn_url:
            print(f"✅ 圖片 {i+1} 上傳成功：{cdn_url}")
            uploaded.append(cdn_url)
        else:
            print(f"❌ 圖片 {i+1} 上傳失敗")
    return uploaded

# ── IG：發布單張 Story ────────────────────────────────
def publish_story(image_url):
    # Step 1：建立 Story 容器
    url = f"https://graph.facebook.com/v19.0/{IG_USER_ID}/media"
    res = requests.post(url, params={
        "image_url": image_url,
        "media_type": "STORIES",
        "access_token": IG_ACCESS_TOKEN
    })
    data = res.json()
    container_id = data.get("id")
    print(f"Story 容器建立：{container_id}，回應：{data}")
    if not container_id:
        return None

    # Step 2：等待容器準備
    time.sleep(5)

    # Step 3：發布
    pub_url = f"https://graph.facebook.com/v19.0/{IG_USER_ID}/media_publish"
    pub_res = requests.post(pub_url, params={
        "creation_id": container_id,
        "access_token": IG_ACCESS_TOKEN
    })
    pub_data = pub_res.json()
    print(f"Story 發布結果：{pub_data}")
    return pub_data.get("id")

# ── Notion：更新狀態 ──────────────────────────────────
def update_status(page_id, status):
    url = f"https://api.notion.com/v1/pages/{page_id}"
    requests.patch(url, headers=headers, json={
        "properties": {
            "狀態": { "status": { "name": status } }
        }
    })
    print(f"✅ Notion 狀態更新為：{status}")

# ── Telegram 通知 ─────────────────────────────────────
def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": message})

# ── 主流程 ────────────────────────────────────────────
def main():
    post = get_pending_stories()
    if not post:
        print("沒有待發限時動態，結束")
        return

    page_id = post["id"]

    image_urls = get_image_urls(post)
    if not image_urls:
        send_telegram("❌ IG Story 發文失敗！\n原因：Notion 沒有圖片")
        update_status(page_id, "失敗")
        return

    cdn_urls = upload_images(image_urls)
    if not cdn_urls:
        send_telegram("❌ IG Story 發文失敗！\n原因：圖片上傳 Cloudinary 失敗")
        update_status(page_id, "失敗")
        return

    # 逐張發布（Story 不支援輪播，每張獨立發）
    success_count = 0
    for i, cdn_url in enumerate(cdn_urls):
        print(f"⏳ 發布第 {i+1} 張 Story...")
        story_id = publish_story(cdn_url)
        if story_id:
            success_count += 1
            print(f"✅ 第 {i+1} 張發布成功")
        else:
            print(f"❌ 第 {i+1} 張發布失敗")
        time.sleep(3)

    if success_count > 0:
        update_status(page_id, "已發")
        send_telegram(f"✅ IG Story 發布成功！共 {success_count} 張")
    else:
        update_status(page_id, "失敗")
        send_telegram("❌ IG Story 發布失敗！所有圖片都發布失敗")

if __name__ == "__main__":
    main()
