# 這是 index.py 的 Regex 復活版程式碼
from http.server import BaseHTTPRequestHandler
import json
import requests
import re
from urllib.parse import urlparse, parse_qs

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        query_params = parse_qs(urlparse(self.path).query)
        text_input = query_params.get('text', [None])[0]

        if not text_input:
            self._send_response({'error': 'text parameter is missing'}, status=400)
            return

        match = re.search(r'https?://[a-zA-Z0-9./?=&_~%-]+', text_input)
        if not match:
            self._send_response({'error': 'No URL found in the provided text'}, status=400)
            return
        
        xhs_url = match.group(0)

        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1'
            }
            
            # 取得跳轉後的最終網址
            response = requests.get(xhs_url, headers=headers, allow_redirects=True, timeout=10)
            response.raise_for_status()
            
            # 取得網頁的全部 HTML 內容
            html_content = response.text
            
            # --- 全新的 Regex 偵測邏輯 ---
            # 使用 Regex 尋找所有可能的圖片和影片 CDN 網址
            # 這個正則表達式會尋找所有 "sns-webpic-qc.xhscdn.com" 或 "sns-video-bd.xhscdn.com" 開頭的網址
            pattern = r'(https?://(?:sns-webpic-qc\.xhscdn\.com|sns-video-bd\.xhscdn\.com)[^\s"\']+)'
            
            found_urls = re.findall(pattern, html_content)
            
            # 去除重複的網址並保持順序
            unique_urls = list(dict.fromkeys(found_urls))
            
            # 將結尾的 "?imageView2/..." 等參數移除，取得最高畫質的原圖
            cleaned_urls = [url.split('?')[0] for url in unique_urls]

            # 沿用我們之前的極簡格式回傳
            self._send_response({"urls_to_download": cleaned_urls})

        except Exception as e:
            self._send_response({'error': str(e), 'processed_url': xhs_url}, status=500)

    def _send_response(self, message, status=200):
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(message).encode('utf-8'))

