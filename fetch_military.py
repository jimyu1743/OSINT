import os
import csv
import json
from datetime import datetime, timezone

import requests


# ==== 需要依照實際觀察結果修改的設定 ====

# 1. 從瀏覽器 F12 找到的「基礎 API URL」
API_URL = "https://globe.adsbexchange.com/data/aircraft"  # TODO: 改成實際 API

# 2. 預設查詢參數（若 API 需要）
DEFAULT_PARAMS = {
    # 範例：
    # "lat": "24",
    # "lon": "121",
    # "radius": "500",
    # 或 "bounds": "N,S,W,E"
}


def is_military(record: dict) -> bool:
    """
    依照實際欄位調整軍機判斷邏輯。
    建議先檢視 last_raw.json 後，再針對 operator/type/category 等欄位調整。
    """
    op = (record.get("operator") or record.get("owner") or "").upper()
    typ = (record.get("type") or record.get("typeDesc") or "").upper()
    cat = (record.get("category") or "").upper()

    keywords = [
        "AIR FORCE",
        "NAVY",
        "ARMY",
        "MARINES",
        "USAF",
        "PLAAF",
        "ROCAF",
        "MIL",
    ]

    if any(keyword in op for keyword in keywords):
        return True
    if "MIL" in typ or "MIL" in cat:
        return True

    # 若 API 有明確欄位（例如 record.get("military") == True），可直接回傳
    return False


# ==== 下面邏輯基本不用改 ====

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def fetch_aircraft_raw():
    """向 ADS-B Exchange 背後 API 送出請求，取得原始 JSON。"""
    try:
        resp = requests.get(API_URL, params=DEFAULT_PARAMS, timeout=20)
        resp.raise_for_status()
    except requests.RequestException as exc:
        print(f"[{datetime.now()}] 請求失敗: {exc}")
        return None

    try:
        return resp.json()
    except json.JSONDecodeError:
        print(f"[{datetime.now()}] 回應不是合法 JSON，前 200 字: {resp.text[:200]!r}")
        return None


def extract_records(raw_json):
    """
    把「每一架飛機」拉成列表。
    若 API 結構不同，請依照 raw_json 實際內容微調。
    """
    if raw_json is None:
        return []

    if isinstance(raw_json, list):
        return raw_json

    if isinstance(raw_json, dict):
        for key in ("ac", "aircraft", "data"):
            if isinstance(raw_json.get(key), list):
                return raw_json[key]

    return [raw_json]


def filter_military(records):
    """套用 is_military() 過濾軍機。"""
    return [
        record
        for record in records
        if isinstance(record, dict) and is_military(record)
    ]


def save_to_csv(records):
    """
    以「日期+時間」命名 CSV，例如: military_2025-11-25_120000Z.csv
    欄位名稱使用所有 record key 的 union。
    """
    if not records:
        print(f"[{datetime.now()}] 沒有符合條件的軍機，略過寫檔。")
        return

    fieldnames = sorted({key for record in records for key in record.keys()})

    now_utc = datetime.now(timezone.utc)
    filename = f"military_{now_utc:%Y-%m-%d_%H%M%SZ}.csv"
    filepath = os.path.join(OUTPUT_DIR, filename)

    with open(filepath, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            writer.writerow(record)

    print(f"[{datetime.now()}] 已寫入 {len(records)} 筆軍機資料到 {filepath}")


def main():
    print(f"[{datetime.now()}] 開始抓取 ADS-B Exchange 軍機資料...")
    raw = fetch_aircraft_raw()
    records = extract_records(raw)

    debug_path = os.path.join(OUTPUT_DIR, "last_raw.json")
    try:
        with open(debug_path, "w", encoding="utf-8") as file:
            json.dump(raw, file, ensure_ascii=False, indent=2)
        print(f"已將原始回應存到 {debug_path}。")
    except Exception as exc:
        print(f"寫入 debug JSON 失敗: {exc}")

    military_records = filter_military(records)
    save_to_csv(military_records)
    print(f"[{datetime.now()}] 任務結束。")


if __name__ == "__main__":
    main()
