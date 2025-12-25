import requests
import pandas as pd
import time
import json

def get_shareholders_direct(symbol):
    """
    不透過 akshare，直接向東方財富 API 請求前十大股東數據
    """
    # 1. 判斷市場後綴 (SH/SZ/BJ)
    if symbol.startswith('6'):
        secu_code = f"{symbol}.SH"
    elif symbol.startswith('0') or symbol.startswith('3'):
        secu_code = f"{symbol}.SZ"
    elif symbol.startswith('4') or symbol.startswith('8'):
        secu_code = f"{symbol}.BJ"
    else:
        secu_code = f"{symbol}.SH" # 默認

    # 2. 設定 API URL (這是東方財富的標準公開接口)
    # RPT_F10_EH_TOP10SHAREHOLDER = 前十大股東
    url = "https://datacenter-web.eastmoney.com/api/data/v1/get"
    
    params = {
        'reportName': 'RPT_F10_EH_TOP10SHAREHOLDER',
        'columns': 'ALL',
        'filter': f'(SECUCODE="{secu_code}")',
        'pageNumber': '1',
        'pageSize': '50',         # 一次抓 50 筆，通常夠涵蓋最近幾期
        'sortTypes': '-1',        # 降序
        'sortColumns': 'REPORT_DATE', # 按日期排
        'source': 'Web',
        'client': 'WEB',
    }

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    try:
        # 發送請求
        resp = requests.get(url, params=params, headers=headers, timeout=5)
        
        # 解析 JSON
        data_json = resp.json()
        
        # 3. 提取數據
        if data_json['result'] is not None and 'data' in data_json['result']:
            raw_data = data_json['result']['data']
            df = pd.DataFrame(raw_data)
            
            # 挑選我們需要的欄位並改名 (中英對照)
            # HOLDER_NAME: 股東名稱, HOLD_NUM: 持股數, HOLD_RATIO: 比例
            # REPORT_DATE: 報告期, HOLDER_RANK: 排名
            wanted_cols = {
                'SECUCODE': '股票代碼',
                'REPORT_DATE': '報告期',
                'HOLDER_RANK': '排名',
                'HOLDER_NAME': '股東名稱',
                'HOLD_NUM': '持股數量',
                'HOLD_RATIO': '持股比例',
                'HOLDER_NATURE': '股東性質',
                'SHARES_TYPE': '股份類型'
            }
            
            # 只保留存在的欄位
            existing_cols = [c for c in wanted_cols.keys() if c in df.columns]
            df = df[existing_cols].rename(columns=wanted_cols)
            
            # 格式化日期 (去掉時間部分)
            if '報告期' in df.columns:
                df['報告期'] = df['報告期'].apply(lambda x: str(x).split(' ')[0])
                
            return df
        else:
            return None

    except Exception as e:
        print(f"  [Error] 請求失敗: {e}")
        return None

def run_direct_crawler():
    print("=== 獨立版直連爬蟲啟動 ===")
    print("說明：繞過 akshare，直接請求東方財富 API")
    print("------------------------------------------------------")
    
    # 測試股票：茅台(600519), 平安(000001), 寧德時代(300750)
    target_codes = ['600519', '000001', '300750']
    
    all_data = []

    for code in target_codes:
        print(f"正在抓取 {code} ...", end=" ")
        
        df = get_shareholders_direct(code)
        
        if df is not None and not df.empty:
            # 這裡我們只取「最新一期」的數據來演示
            latest_date = df.iloc[0]['報告期']
            df_latest = df[df['報告期'] == latest_date]
            
            all_data.append(df_latest)
            print(f"成功！(日期: {latest_date})")
        else:
            print("無數據或失敗。")
            
        time.sleep(1) # 禮貌延遲

    print("------------------------------------------------------")
    if all_data:
        final_df = pd.concat(all_data, ignore_index=True)
        print("爬取成果預覽：")
        # 顯示前幾行
        print(final_df[['股票代碼', '報告期', '排名', '股東名稱', '持股比例']].head(5))
        
        filename = "direct_shareholders_result.csv"
        final_df.to_csv(filename, index=False, encoding="utf-8-sig")
        print(f"\nSUCCESS: 檔案已儲存為 {filename}")
    else:
        print("未能獲取數據。")

if __name__ == "__main__":
    run_direct_crawler()