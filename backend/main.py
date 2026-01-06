from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import sys
import io
import os
import re
import time
import random
import requests
import pandas as pd
from datetime import datetime, timedelta
from urllib.parse import unquote
import gdown
from bs4 import BeautifulSoup
import yfinance as yf
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Fix Windows console encoding
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Cache directory
CACHE_DIR = "etf_data_cache"

class ETFProcessor:
    def __init__(self):
        self.file_map = {
            "00981A": "https://drive.google.com/drive/folders/1mK6gf2kYPA2Mkh-JqG5J197nJQ8KONOd",
            "00980A": "https://drive.google.com/drive/folders/1OpCjYlQJaO6nE0PTpddXz8AmXN3-hEZF",
            "00982A": "https://drive.google.com/drive/folders/1moHqmiJdPLxfaH7jJjYd_WFRN2fbgwla",
            "00985A": "https://drive.google.com/drive/folders/1DAK6cKsIAKRPB7gjgTrjZ5K9rqXKdhH8"
        }
        self.price_cache = {}
        os.makedirs(CACHE_DIR, exist_ok=True)
        
        # Configure robust session with retries
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    # ---------------- Price Fetching ----------------
    def get_mis_prices(self, code, date_str):
        """TWSE MIS API for today's price."""
        today_str = datetime.now().strftime("%Y%m%d")
        if date_str != today_str:
            return None
        try:
            for prefix in ('tse_', 'otc_'):
                url = f'https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch={prefix}{code}.tw&json=1&delay=0'
                time.sleep(random.uniform(0.5, 1.0))  # Increased delay to be nicer to the API
                r = self.session.get(url, timeout=10)
                try:
                    data = r.json()
                except ValueError:
                     # If response is not JSON (e.g. empty or HTML error page), skip
                    continue
                
                if 'msgArray' in data:
                    for item in data['msgArray']:
                        if item.get('c') != code:
                            continue
                        c_val = item.get('z') or item.get('oz') or item.get('ob')
                        if not c_val or c_val == '-' or float(item.get('y') or 0) == 0:
                            continue
                        return float(c_val)
        except Exception as e:
            print(f"[MIS] {code} MIS API 請求失敗: {e}")
        return None

    def get_twse_prices(self, code, date_str):
        """TWSE Stock Day Report API for historical prices."""
        today_str = datetime.now().strftime("%Y%m%d")
        if date_str >= today_str:
            return None
        try:
            y, m = int(date_str[:4]), int(date_str[4:6])
            month_first = f"{y}{m:02d}01"
            url = f'https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&date={month_first}&stockNo={code}'
            r = self.session.get(url, timeout=10)
            data = r.json()
            if data.get('stat') == 'OK' and data.get('data'):
                def to_roc_date(s):
                    yy, mm, dd = s.split('/')
                    return f"{int(yy) + 1911:04d}{mm}{dd}"
                for row in data['data']:
                    if to_roc_date(row[0]) == date_str:
                        close_str = row[6]
                        try:
                            return float(close_str.replace(',', ''))
                        except:
                            return None
        except Exception as e:
            print(f"[TWSE] {code} TWSE API 請求失敗: {e}")
        return None

    def get_yf_prices(self, code, date_str):
        """Yahoo Finance as a fallback."""
        def try_yf(ticker):
            try:
                d = datetime.strptime(date_str, "%Y%m%d")
                df = yf.Ticker(ticker).history(
                    start=d.strftime('%Y-%m-%d'),
                    end=(d + timedelta(days=1)).strftime('%Y-%m-%d')
                )
                if df.empty:
                    return None
                df = df.reset_index()
                df['Date'] = df['Date'].dt.strftime('%Y%m%d')
                idx_list = df.index[df['Date'] == date_str].tolist()
                if not idx_list:
                    return None
                idx = idx_list[0]
                return float(df.loc[idx, 'Close'])
            except:
                return None
        
        result = try_yf(f"{code}.TWO")
        if result: return result
        result = try_yf(f"{code}.TW")
        if result: return result
        
        try:
            ticker = yf.Ticker(f"{code}.TW")
            return ticker.fast_info['lastPrice']
        except:
            return None

    def get_stock_price(self, code, date_str=None):
        """Fetches the latest price for a symbol using multiple sources."""
        if not code:
            return 0
        
        if not date_str:
            date_str = datetime.now().strftime("%Y%m%d")
            
        cache_key = f"{code}_{date_str}"
        if cache_key in self.price_cache:
            return self.price_cache[cache_key]
        
        # Sequence: MIS -> TWSE -> YF
        p = self.get_mis_prices(code, date_str)
        if p is None:
            p = self.get_twse_prices(code, date_str)
        if p is None:
            p = self.get_yf_prices(code, date_str)
            
        if p is not None:
            # Cache it
            self.price_cache[cache_key] = p
            return p
            
        return 0

    def format_twd_amount(self, n: float) -> str:
        """User preferred TWD formatting (1.2億, 345萬, etc.)."""
        if n is None or pd.isna(n): return "—"
        try:
            n = float(n)
        except:
            return "—"
            
        absn = abs(n)
        sign = "-" if n < 0 else ""
        if absn >= 100_000_000:
            return f"{sign}{absn/100_000_000:.1f}億"
        elif absn >= 10_000:
            return f"{sign}{int(round(absn/10_000))}萬"
        else:
            return f"{sign}{int(round(absn))}"

    # ---------------- Drive Helpers ----------------
    def _extract_folder_id(self, folder_url: str) -> str:
        m = re.search(r'/folders/([a-zA-Z0-9_-]+)', folder_url)
        if not m:
            print(f"Error extracting folder ID from {folder_url}")
            return ""
        return m.group(1)

    def _normalize_name(self, s: str) -> str:
        return re.sub(r'\s+', ' ', (s or '').strip()).lower()

    def _list_from_embedded(self, folder_id: str):
        url = f"https://drive.google.com/embeddedfolderview?id={folder_id}#list"
        try:
            resp = self.session.get(url, timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            out = []
            for a in soup.select("div#folder-view a[href*='?id=']"):
                href = a.get("href", "")
                name = (a.text or "").strip()
                if "id=" in href:
                    fid = href.split("id=")[-1]
                    if fid and name:
                        out.append({"name": name, "id": fid})
            for a in soup.select("a"):
                href = a.get("href", "") or ""
                name = (a.text or "").strip()
                m = re.search(r"/file/d/([a-zA-Z0-9_-]+)/", href)
                if m and name:
                    out.append({"name": name, "id": m.group(1)})
            return out
        except Exception as e:
            print(f"[list_from_embedded] Parse failed: {e}")
            return []

    def _list_from_drive_page(self, folder_id: str):
        url = f"https://drive.google.com/drive/folders/{folder_id}"
        try:
            resp = self.session.get(url, timeout=15)
            resp.raise_for_status()
            html = resp.text
            soup = BeautifulSoup(html, "html.parser")
            out = []
            for a in soup.select("a"):
                href = a.get("href", "") or ""
                text = (a.text or "").strip()
                m = re.search(r"/file/d/([a-zA-Z0-9_-]+)/", href)
                if m:
                    fid = m.group(1)
                    name = text or a.get("aria-label") or a.get("title") or ""
                    if name:
                        out.append({"name": name, "id": fid})
            for m in re.finditer(r'"doc_id"\s*:\s*"(?P<id>[a-zA-Z0-9_-]+)".{0,200}?"title"\s*:\s*"(?P<name>[^"]+)"', html, re.DOTALL):
                fid = m.group("id")
                name = unquote(m.group("name"))
                out.append({"name": name, "id": fid})
            return out
        except Exception as e:
            print(f"[list_from_drive_page] Parse failed: {e}")
            return []

    def list_folder_files(self, folder_url: str):
        folder_id = self._extract_folder_id(folder_url)
        if not folder_id: return []
        
        items = []
        seen = set()
        for getter in (self._list_from_embedded, self._list_from_drive_page):
            lst = getter(folder_id)
            for it in lst:
                name = it.get("name") or ""
                fid = it.get("id") or ""
                key = (name, fid)
                if name and fid and key not in seen:
                    seen.add(key)
                    items.append({"name": name, "id": fid})
        return items

    def find_latest_two_files(self, files):
        valid_files = []
        for f in files:
            name = f['name']
            match = re.search(r'(202[0-9])[-]?([0-1][0-9])[-]?([0-3][0-9])', name)
            if match:
                date_str = "".join(match.groups())  # 20260105
                valid_files.append({
                    "name": name,
                    "id": f['id'],
                    "date": date_str
                })
        
        valid_files.sort(key=lambda x: x['date'], reverse=True)
        return valid_files[:2]

    def download_file(self, file_info):
        fname = file_info['name']
        fid = file_info['id']
        path = os.path.join(CACHE_DIR, fname)
        
        if not os.path.exists(path):
            print(f"⬇️ Downloading {fname}...")
            url = f'https://drive.google.com/uc?id={fid}'
            gdown.download(url, path, quiet=False)
        return path

    def find_stock_header_index(self, df_raw):
        ticker_keywords = ['股票代號', '股票代碼', '證券代號', 'Code', 'Symbol', 'Ticker']
        shares_keywords = ['股數', 'Shares', 'Vol', 'Volume', '持股', '持有股數', 'Units', 'Quantity']
        
        for idx, row in df_raw.iterrows():
            cells = row.astype(str).tolist()
            has_ticker = any(any(k in c for k in ticker_keywords) for c in cells)
            has_shares = any(any(k in c for k in shares_keywords) for c in cells)
            
            if has_ticker and has_shares:
                return idx
        return None
    
    def _parse_weight_to_float(self, x):
        try:
            s = str(x).strip()
            if s.endswith('%'): s = s[:-1]
            s = s.replace(',', '')
            return float(s)
        except: return 0.0

    def clean_dataframe(self, df):
        pass

    def get_real_data(self):
        results = {}
        dates_info = {"new": "", "old": ""}
        
        for etf_code, folder_url in self.file_map.items():
            print(f"Processing {etf_code} from {folder_url}...")
            
            # 1. List files
            all_files = self.list_folder_files(folder_url)
            if not all_files:
                print(f"Warning: No files found for {etf_code}")
                results[etf_code] = []
                continue
            
            # 2. Pick top 2 by date
            target_files = self.find_latest_two_files(all_files)
            if len(target_files) < 2:
                print(f"Warning: Need at least 2 dated files for comparison, found {len(target_files)} for {etf_code}")
                results[etf_code] = []
                continue
                
            latest = target_files[0]
            previous = target_files[1]
            print(f"  Comparing {latest['date']} vs {previous['date']}")
            
            dates_info["new"] = latest['date']
            dates_info["old"] = previous['date']
            
            # 3. Download
            path_latest = self.download_file(latest)
            path_old = self.download_file(previous)
            
            comp_result = self.compare_files(path_old, path_latest, latest['date'])
            if "error" in comp_result:
                print(f"  Error comparing {etf_code}: {comp_result['error']}")
                results[etf_code] = []
            else:
                results[etf_code] = comp_result['data']
        
        # Clean up cache
        self.cleanup_cache() 
        return results, dates_info

    def cleanup_cache(self, keep_count=20):
        if not os.path.exists(CACHE_DIR):
            return

        all_files = [os.path.join(CACHE_DIR, f) for f in os.listdir(CACHE_DIR) if os.path.isfile(os.path.join(CACHE_DIR, f))]
        
        # Keep latest X files
        all_files.sort(key=os.path.getmtime, reverse=True)
        if len(all_files) > keep_count:
            for trash in all_files[keep_count:]:
                try:
                    os.remove(trash)
                except: pass

    def compare_files(self, path_old, path_latest, date_latest_str):
        try:
            def load_valid_sheet(path):
                xl = pd.ExcelFile(path)
                for sheet in xl.sheet_names:
                    df_raw = pd.read_excel(path, sheet_name=sheet, header=None)
                    idx = self.find_stock_header_index(df_raw)
                    if idx is not None:
                        return pd.read_excel(path, sheet_name=sheet, header=idx)
                return None

            df_old = load_valid_sheet(path_old)
            df_latest = load_valid_sheet(path_latest)

            if df_old is None or df_latest is None:
                return {"error": "Excel format error: Header not found in any sheet"}

            df_old.columns = [str(c).strip() for c in df_old.columns]
            df_latest.columns = [str(c).strip() for c in df_latest.columns]

            def find_col(df, candidates, exclude=None):
                for c in df.columns:
                    if exclude and any(ex in c for ex in exclude):
                        continue
                    if any(cand in c for cand in candidates):
                        return c
                return None

            id_candidates = ['股票代號', '股票代碼', '證券代號', 'Code', 'Symbol', 'Ticker']
            name_candidates = ['股票名稱', 'Name', 'Security Name', '證券名稱', '名稱', 'Security']
            shares_candidates = ['股數', 'Shares', 'Volume', '持股', '持有股數', 'Units', 'Quantity']
            
            col_id_old = find_col(df_old, id_candidates)
            col_id_new = find_col(df_latest, id_candidates)
            col_name_old = find_col(df_old, name_candidates)
            col_name_new = find_col(df_latest, name_candidates)
            
            weight_exclusions = ['權重', '%', 'Rate', 'Ratio', '比例']
            col_shares_old = find_col(df_old, shares_candidates, exclude=weight_exclusions)
            col_shares_new = find_col(df_latest, shares_candidates, exclude=weight_exclusions)
            
            if not all([col_id_old, col_id_new, col_shares_old, col_shares_new]):
                missing = []
                if not col_id_new: missing.append("Ticker")
                if not col_shares_new: missing.append("Shares")
                return {"error": f"Missing required columns. Missing: {missing}"}

            df_old = df_old[[col_id_old, col_name_old, col_shares_old]].copy()
            df_old.columns = ['股票代號', '股票名稱', '股數']
            
            col_weight = find_col(df_latest, ['持股權重', 'Weight', '持股權重(%)', '持股比例(%)'])
            cols_needed_new = [col_id_new, col_name_new, col_shares_new]
            if col_weight: cols_needed_new.append(col_weight)
            
            df_latest = df_latest[cols_needed_new].copy()
            renames = {col_id_new: '股票代號', col_name_new: '股票名稱', col_shares_new: '股數'}
            if col_weight: renames[col_weight] = '持股權重'
            df_latest.rename(columns=renames, inplace=True)

            for df in [df_old, df_latest]:
                df['股票代號'] = df['股票代號'].astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
                df['股票名稱'] = df['股票名稱'].astype(str).str.strip()

            df_old = df_old.rename(columns={'股數': '股數_old', '股票名稱': '股票名稱_old'})
            df_latest = df_latest.rename(columns={'股數': '股數_new', '股票名稱': '股票名稱_new'})
            
            merged = pd.merge(df_old, df_latest, on='股票代號', how='outer')
            merged['股票名稱'] = merged['股票名稱_new'].combine_first(merged['股票名稱_old'])
            
            merged['股數_old'] = pd.to_numeric(merged['股數_old'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
            merged['股數_new'] = pd.to_numeric(merged['股數_new'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
            merged['delta_shares'] = merged['股數_new'] - merged['股數_old']

            df_changes = merged[merged['delta_shares'] != 0].copy()
            df_holdings = merged[merged['股數_new'] > 1000].copy()

            def process_rows(df, is_change_list=True):
                result = []
                for _, row in df.iterrows():
                    code = row['股票代號']
                    price = self.get_stock_price(code, date_latest_str)
                    
                    base_share = row['delta_shares'] if is_change_list else row['股數_new']
                    monetary = base_share * price
                    
                    action = "Changed"
                    if is_change_list:
                        if row['股數_old'] == 0: action = "Added"
                        elif row['股數_new'] <= 1000: action = "Removed"
                    else:
                        action = "Holding"

                    item = {
                        "ticker": code,
                        "name": row['股票名稱'],
                        "old_shares": int(row['股數_old']),
                        "new_shares": int(row['股數_new']),
                        "delta_shares": int(row['delta_shares']),
                        "price": price,
                        "monetary_value": monetary,
                        "monetary_value_str": self.format_twd_amount(monetary),
                        "action": action
                    }
                    result.append(item)
                return result

            list_changes = process_rows(df_changes, is_change_list=True)
            list_holdings = process_rows(df_holdings, is_change_list=False)

            return {
                "data": {
                    "changes": list_changes,
                    "holdings": list_holdings
                }
            }

        except Exception as e:
            import traceback
            print(traceback.format_exc())
            return {"error": str(e)}

processor = ETFProcessor()

def cleanup_real_cache():
    # Deprecated fallback, handled in class now
    pass

@app.get("/api/holdings/changes")
def get_holding_changes():
    try:
        data, dates = processor.get_real_data()
        
        # Calculate aggregate changes
        summary = {
            "total_value_change": 0,
            "count_added": 0,
            "count_removed": 0
        }
        
        for etf_code, etf_data in data.items():
            if not etf_data: continue
            
            # Access 'changes' list safely
            changes = etf_data.get('changes', []) if isinstance(etf_data, dict) else []
            
            for item in changes:
                summary["total_value_change"] += item["monetary_value"]
                if item["action"] == "Added":
                    summary["count_added"] += 1
                elif item["action"] == "Removed":
                    summary["count_removed"] += 1
                    
        return {
            "dates": dates,
            "summary": {
                "total_value_change": processor.format_twd_amount(summary["total_value_change"]),
                "count_added": summary["count_added"],
                "count_removed": summary["count_removed"]
            },
            "etf_details": data
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
