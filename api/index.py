# 這是 index.py 的最終智慧版程式碼
from http.server import BaseHTTPRequestHandler
import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs
import re

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
            
            if 'xhslink.com' in xhs_url:
                head_response = requests.head(xhs_url, headers=headers, allow_redirects=True, timeout=10)
                xhs_url = head_response.url

            response = requests.get(xhs_url, headers=headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            
            # --- 全新的智慧邏輯 ---
            download_urls = []
            
            # 優先檢查「圖片+影片」的組合
            live_photo_combo = soup.select_one('div.live-photo-contain')
            if live_photo_combo:
                img_tag = live_photo_combo.select_one('img')
                video_tag = live_photo_combo.select_one('video')
                if img_tag and video_tag:
                    # 直接把兩個網址都加到下載列表
                    download_urls.append(img_tag.get('src', '').split('?')[0])
                    download_urls.append(video_tag.get('src', '').split('?')[0])
            else:
                # 如果不是組合，才解析 JSON
                script_tag = soup.find('script', string=lambda t: t and 'window.__INITIAL_STATE__' in t)
                if not script_tag:
                    raise ValueError("Could not find initial state script tag.")

                json_str = script_tag.string.split('window.__INITIAL_STATE__=')[1].split(';window.__INITIAL_PROPS__=')[0]
                data = json.loads(json_str)

                note_id = list(data['note']['noteDetailMap'].keys())[0]
                note_data = data['note']['noteDetailMap'][note_id]
                
                if note_data['type'] == 'video':
                    video_url = note_data['video']['media']['stream']['h24'][0]['masterUrl']
                    download_urls.append(video_url)
                else:
                    for image in note_data['imageList']:
                        image_url = image['info_list'][0]['url_default'].split('?')[0]
                        download_urls.append(image_url)
            
            # 回傳最終的、超級簡單的下載列表
            self._send_response({"urls_to_download": download_urls})

        except Exception as e:
            self._send_response({'error': str(e), 'processed_url': xhs_url}, status=500)

    def _send_response(self, message, status=200):
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(message).encode('utf-8'))

