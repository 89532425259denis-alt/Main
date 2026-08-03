from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import re
import os
import time
import threading

app = Flask(__name__)
CORS(app)

# ============================================================
# KEEP-ALIVE (чтобы Render не засыпал)
# ============================================================
def keep_alive():
    while True:
        try:
            url = f"http://localhost:{os.environ.get('PORT', 5000)}/"
            requests.get(url, timeout=5)
            print(f"🔄 Keep-alive: {time.ctime()}")
        except:
            pass
        time.sleep(600)

threading.Thread(target=keep_alive, daemon=True).start()

# ============================================================
# INVIDIOUS API (БЕЗ КУК, БЕЗ ПРОКСИ)
# ============================================================
INVIDIOUS_INSTANCES = [
    "https://invidious.fdn.fr",
    "https://invidious.nerdvpn.de",
    "https://invidious.osi.kr",
    "https://invidious.tube",
    "https://inv.vern.cc",
    "https://invidious.jing.rocks",
    "https://inv.tech.ameri.net",
]

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

def get_video_info_invidious(video_id):
    """Получает информацию о видео через Invidious (без кук)"""
    for instance in INVIDIOUS_INSTANCES:
        try:
            api_url = f"{instance}/api/v1/videos/{video_id}"
            print(f"  🌐 Пробую: {instance}")
            
            response = requests.get(api_url, timeout=10, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            
            if response.status_code == 200:
                data = response.json()
                
                # Получаем ссылки на видео и аудио
                video_url = None
                audio_url = None
                
                # Видео (лучшее качество)
                formats = data.get('formatStreams', [])
                for f in formats:
                    if f.get('type', '').startswith('video/mp4'):
                        if not video_url or f.get('qualityLabel', '') == '720p':
                            video_url = f.get('url')
                
                # Аудио
                audio_formats = data.get('adaptiveFormats', [])
                for f in audio_formats:
                    if f.get('type', '').startswith('audio/mp4'):
                        if not audio_url:
                            audio_url = f.get('url')
                
                # Если не нашли через API, пробуем прямую ссылку
                if not video_url:
                    video_url = f"{instance}/latest_version?id={video_id}&itag=22"
                
                return {
                    'success': True,
                    'title': data.get('title', 'Без названия'),
                    'video': video_url,
                    'audio': audio_url,
                    'duration': data.get('lengthSeconds', 0)
                }
                
        except Exception as e:
            print(f"    ⚠️ Ошибка: {str(e)[:40]}")
            continue
    
    return None

# ============================================================
# ЗАПАСНЫЕ API (если Invidious не работает)
# ============================================================
def api_savefrom(video_id):
    """SaveFrom.net API (без кук)"""
    try:
        url = f"https://en.savefrom.net/1/?url=https://youtube.com/watch?v={video_id}&lang=en"
        response = requests.get(url, timeout=10, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        if response.status_code == 200:
            data = response.json()
            if data.get('url'):
                return {
                    'title': data.get('title', 'Видео'),
                    'video': data.get('url'),
                    'audio': data.get('url'),
                    'duration': 0
                }
    except:
        pass
    return None

def api_vevioz(video_id):
    """Vevioz API (без кук)"""
    try:
        url = f"https://api.vevioz.com/api/button/mp3/{video_id}"
        response = requests.get(url, timeout=10, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        if response.status_code == 200:
            data = response.json()
            if data.get('download'):
                return {
                    'title': data.get('title', 'Видео'),
                    'video': data.get('download'),
                    'audio': data.get('download'),
                    'duration': 0
                }
    except:
        pass
    return None

# ============================================================
# ОСНОВНОЙ МАРШРУТ
# ============================================================

@app.route('/')
def index():
    return jsonify({
        'status': 'ok',
        'message': 'YouTube Downloader API (без кук, без прокси)',
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
    
    # 1. Пробуем Invidious (основной метод)
    result = get_video_info_invidious(video_id)
    if result and (result.get('video') or result.get('audio')):
        return jsonify(result)
    
    # 2. Если Invidious не работает, пробуем запасные API
    apis = [
        ('SaveFrom', api_savefrom),
        ('Vevioz', api_vevioz),
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
    
    return jsonify({'error': 'Не удалось найти ссылки'}), 500

# ============================================================
# ЗАПУСК
# ============================================================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("=" * 50)
    print("🚀 YouTube Downloader API")
    print("📡 Без кук, без прокси")
    print("📡 Invidious + запасные API")
    print(f"📡 Порт: {port}")
    print("=" * 50)
    app.run(host='0.0.0.0', port=port, debug=False)
