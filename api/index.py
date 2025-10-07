# 這是 index.py 的完整內容
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
            script_tag = soup.find('script', string=lambda t: t and 'window.__INITIAL_STATE__' in t)
            
            if not script_tag:
                raise ValueError("Could not find initial state script tag.")

            json_str = script_tag.string.split('window.__INITIAL_STATE__=')[1].split(';window.__INITIAL_PROPS__=')[0]
            data = json.loads(json_str)

            note_id = list(data['note']['noteDetailMap'].keys())[0]
            note_data = data['note']['noteDetailMap'][note_id]
            
            media_list = []
            
            # --- 全新的邏輯 ---
            # 優先檢查是否存在「圖片+影片」的組合
            live_photo_combo = soup.select_one('div.live-photo-contain')
            if live_photo_combo:
                img_tag = live_photo_combo.select_one('img')
                video_tag = live_photo_combo.select_one('video')
                if img_tag and video_tag:
                    # 發現組合！回傳一個新的類型 "live_photo_combo"
                    media_list.append({
                        "type": "live_photo_combo",
                        "image_url": img_tag.get('src', '').split('?')[0],
                        "video_url": video_tag.get('src', '').split('?')[0]
                    })

            # 如果不是組合，才走舊的邏輯
            elif note_data['type'] == 'video':
                duration = note_data['video'].get('duration', 99999)
                video_url = note_data['video']['media']['stream']['h264'][0]['masterUrl']
                
                if duration < 4000:
                    media_list.append({"url": video_url, "type": "live_photo"})
                else:
                    media_list.append({"url": video_url, "type": "video"})
            else:
                for image in note_data['imageList']:
                    image_url = image['info_list'][0]['url_default'].split('?')[0]
                    media_list.append({"url": image_url, "type": "image"})
            
            self._send_response({"media": media_list})

        except Exception as e:
            self._send_response({'error': str(e), 'processed_url': xhs_url}, status=500)
