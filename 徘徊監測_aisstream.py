import asyncio
import websockets
import json
import csv
import os
from datetime import datetime
from dotenv import load_dotenv  # 新增這一行

# 1. 載入 .env 檔案
load_dotenv()

# 2. 從環境變數讀取 Key
API_KEY = os.getenv("AIS_KEY")

# 檢查是否有讀到，沒讀到就報錯提醒
if API_KEY is None:
    raise ValueError("❌ 找不到 API Key！請確認資料夾內是否有 .env 檔案")

# 設定監測範圍 (格式: [[min_lat, min_lon], [max_lat, max_lon]])
# 範例：馬六甲海峽周邊
BOUNDING_BOX = [[[-5.0, 100.0], [5.0, 110.0]]]

# 輸出檔案名稱
OUTPUT_FILE = "ais_data.csv"
# ==========================================

async def connect_ais_stream():
    async with websockets.connect("wss://stream.aisstream.io/v0/stream") as websocket:
        
        # 1. 發送訂閱請求
        subscribe_message = {
            "APIKey": API_KEY,
            "BoundingBoxes": BOUNDING_BOX,
            "FilterMessageTypes": ["PositionReport"] 
        }
        await websocket.send(json.dumps(subscribe_message))
        print(f"✅ 已連線！正在監聽訊號，數據將寫入 {OUTPUT_FILE} ...")
        print("按 Ctrl + C 可停止程式")

        async for message in websocket:
            try:
                data = json.loads(message)
                
                # 2. 解析數據
                if "PositionReport" in data["Message"]:
                    report = data["Message"]["PositionReport"]
                    
                    # 提取關鍵欄位
                    mmsi = report["UserID"]
                    lat = report["Latitude"]
                    lon = report["Longitude"]
                    # 有些訊號可能沒有航速資料，預設為 0
                    speed = report.get("Sog", 0) 
                    
                    # 獲取當前時間
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                    # 3. 顯示在螢幕上
                    print(f"[{timestamp}] 📡 MMSI: {mmsi} | 速度: {speed}節 | 位置: {lat}, {lon}")

                    # 4. 寫入 CSV 檔案
                    # 檢查檔案是否存在 (若不存在則先寫入表頭)
                    file_exists = os.path.isfile(OUTPUT_FILE)
                    
                    with open(OUTPUT_FILE, mode='a', newline='', encoding='utf-8-sig') as f:
                        writer = csv.writer(f)
                        
                        # 如果是新檔案，先寫入欄位名稱
                        if not file_exists:
                            writer.writerow(["Timestamp", "MMSI", "Latitude", "Longitude", "Speed"])
                        
                        # 寫入數據
                        writer.writerow([timestamp, mmsi, lat, lon, speed])

            except Exception as e:
                print(f"⚠️ 發生錯誤: {e}")
                continue

if __name__ == "__main__":
    try:
        asyncio.run(connect_ais_stream())
    except KeyboardInterrupt:
        print("\n🛑 程式已停止。數據已保存。")