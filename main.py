from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import re
import os
import time
import threading
import json

app = Flask(__name__)
CORS(app)

# ============================================================
# KEEP-ALIVE
# ============================================================
def keep_alive():
    while True:
        try:
            url = f"http://localhost:{os.environ.get('PORT', 5000)}/"
            requests.get(url, timeout=5)
        except:
            pass
        time.sleep(600)

threading.Thread(target=keep_alive, daemon=True).start()

# ============================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================

def extract_video_id(url):
    """Извлекает ID видео из URL"""
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11})(?:[?&]|$)',
        r'(?:youtu\.be\/)([0-9A-Za-z_-]{11})',
        r'(?:embed\/)([0-9A-Za-z_-]{11})',
        r'(?:shorts\/)([0-9A-Za-z_-]{11})'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

# ============================================================
# API (проверенные рабочие)
# ============================================================

def api_yt1s(video_id):
    """YT1s.com API - работает"""
    try:
        url = "https://yt1s.com/api/ajaxSearch/index"
        data = {'q': f"https://youtube.com/watch?v={video_id}", 'vt': 'home'}
        response = requests.post(url, data=data, timeout=15, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': 'https://yt1s.com',
            'Referer': 'https://yt1s.com/'
        })
        if response.status_code == 200:
            result = response.json()
            if result.get('status') == 'ok':
                links = result.get('links', {})
                return {
                    'title': result.get('title', 'Видео'),
                    'video': links.get('mp4', {}).get('720', {}).get('url') or links.get('mp4', {}).get('360', {}).get('url'),
                    'audio': links.get('mp3', {}).get('128', {}).get('url'),
                    'duration': 0
                }
    except Exception as e:
        print(f"  ⚠️ YT1s: {str(e)[:30]}")
    return None

def api_yt5s(video_id):
    """YT5s.com API - работает"""
    try:
        url = "https://yt5s.com/api/ajaxSearch/index"
        data = {'q': f"https://youtube.com/watch?v={video_id}"}
        response = requests.post(url, data=data, timeout=15, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Content-Type': 'application/x-www-form-urlencoded'
        })
        if response.status_code == 200:
            result = response.json()
            if result.get('status') == 'ok':
                links = result.get('links', {})
                return {
                    'title': result.get('title', 'Видео'),
                    'video': links.get('mp4', {}).get('720', {}).get('url') or links.get('mp4', {}).get('360', {}).get('url'),
                    'audio': links.get('mp3', {}).get('128', {}).get('url'),
                    'duration': 0
                }
    except Exception as e:
        print(f"  ⚠️ YT5s: {str(e)[:30]}")
    return None

def api_y2save(video_id):
    """Y2Save.com API - работает"""
    try:
        url = "https://y2save.com/api/ajaxSearch/index"
        data = {'q': f"https://youtube.com/watch?v={video_id}"}
        response = requests.post(url, data=data, timeout=15, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Content-Type': 'application/x-www-form-urlencoded'
        })
        if response.status_code == 200:
            result = response.json()
            if result.get('status') == 'ok':
                links = result.get('links', {})
                return {
                    'title': result.get('title', 'Видео'),
                    'video': links.get('mp4', {}).get('720', {}).get('url') or links.get('mp4', {}).get('360', {}).get('url'),
                    'audio': links.get('mp3', {}).get('128', {}).get('url'),
                    'duration': 0
                }
    except Exception as e:
        print(f"  ⚠️ Y2Save: {str(e)[:30]}")
    return None

# ============================================================
# ПРЯМОЕ СКАЧИВАНИЕ ЧЕРЕЗ yt-dlp (резервный метод)
# ============================================================
def download_with_ytdlp(video_id):
    """Использует yt-dlp для получения прямых ссылок"""
    import yt_dlp
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'socket_timeout': 20,
            'ignoreerrors': True,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"https://youtube.com/watch?v={video_id}", download=False)
            
            if not info:
                return None
            
            video_url = None
            audio_url = None
            
            for f in info.get('formats', []):
                if f.get('ext') == 'mp4' and f.get('vcodec') != 'none' and f.get('acodec') != 'none':
                    if not video_url or f.get('height', 0) > 720:
                        video_url = f.get('url')
                if f.get('acodec') != 'none' and f.get('vcodec') == 'none':
                    if not audio_url or f.get('abr', 0) > 128:
                        audio_url = f.get('url')
            
            return {
                'title': info.get('title', 'Видео'),
                'video': video_url,
                'audio': audio_url,
                'duration': info.get('duration', 0)
            }
            
    except Exception as e:
        print(f"  ⚠️ yt-dlp: {str(e)[:30]}")
        return None

# ============================================================
# ОСНОВНОЙ МАРШРУТ
# ============================================================

@app.route('/')
def index():
    return jsonify({
        'status': 'ok',
        'message': 'YouTube Downloader API',
        'time': time.ctime()
    })

@app.route('/info')
def get_info():
    url = request.args.get('url')
    if not url:
        return jsonify({'error': 'No URL'}), 400
    
    video_id = extract_video_id(url)
    if not video_id:
        return jsonify({'error': 'Invalid YouTube URL'}), 400
    
    print(f"🔍 Видео ID: {video_id}")
    
    # Список API (пробуем по очереди)
    apis = [
        ('YT1s', api_yt1s),
        ('YT5s', api_yt5s),
        ('Y2Save', api_y2save),
    ]
    
    for name, api_func in apis:
        try:
            print(f"  🌐 Пробую {name}...")
            result = api_func(video_id)
            if result and (result.get('video') or result.get('audio')):
                print(f"    ✅ Найдено на {name}")
                return jsonify({
                    'success': True,
                    'title': result.get('title', 'Видео'),
                    'video': result.get('video'),
                    'audio': result.get('audio'),
                    'duration': result.get('duration', 0)
                })
        except Exception as e:
            print(f"    ⚠️ {name}: {str(e)[:30]}")
    
    # Если API не сработали — пробуем yt-dlp
    print("  🌐 Пробую yt-dlp...")
    result = download_with_ytdlp(video_id)
    if result and (result.get('video') or result.get('audio')):
        print("    ✅ Найдено через yt-dlp")
        return jsonify({
            'success': True,
            'title': result.get('title', 'Видео'),
            'video': result.get('video'),
            'audio': result.get('audio'),
            'duration': result.get('duration', 0)
        })
    
    return jsonify({'error': 'Не удалось найти ссылки'}), 500

# ============================================================
# ЗАПУСК
# ============================================================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("=" * 50)
    print("🚀 YouTube Downloader API")
    print("📡 3 API + yt-dlp (резерв)")
    print(f"📡 Порт: {port}")
    print("=" * 50)
    app.run(host='0.0.0.0', port=port, debug=False)
