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
# РАБОЧИЕ API (БЕЗ КУК, БЕЗ ПРОКСИ)
# ============================================================

def api_savefrom(video_id):
    """SaveFrom.net API (работает)"""
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
    except Exception as e:
        print(f"  ⚠️ SaveFrom: {str(e)[:30]}")
    return None

def api_vevioz(video_id):
    """Vevioz API (работает)"""
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
    except Exception as e:
        print(f"  ⚠️ Vevioz: {str(e)[:30]}")
    return None

def api_yt1s(video_id):
    """YT1s.com API (работает)"""
    try:
        url = "https://yt1s.com/api/ajaxSearch/index"
        data = {'q': f"https://youtube.com/watch?v={video_id}", 'vt': 'home'}
        response = requests.post(url, data=data, timeout=10, headers={
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
        print(f"  ⚠️ YT1s: {str(e)[:30]}")
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
    
    # Пробуем API по очереди (все работают без кук)
    apis = [
        ('SaveFrom', api_savefrom),
        ('Vevioz', api_vevioz),
        ('YT1s', api_yt1s),
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
    
    return jsonify({'error': 'Не найдено ссылок'}), 500

# ============================================================
# ЗАПУСК
# ============================================================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("=" * 50)
    print("🚀 YouTube Downloader API")
    print("📡 3 рабочих API (без кук)")
    print(f"📡 Порт: {port}")
    print("=" * 50)
    app.run(host='0.0.0.0', port=port, debug=False)
