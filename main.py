from flask import Flask, request, jsonify
from flask_cors import CORS
import yt_dlp
import os
import threading
import time
import requests
import json
import re

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
            print(f"🔄 Keep-alive ping: {time.ctime()}")
        except Exception as e:
            print(f"⚠️ Keep-alive error: {e}")
        time.sleep(600)

threading.Thread(target=keep_alive, daemon=True).start()

# ============================================================
# COOKIES (для обхода "Sign in to confirm")
# ============================================================
# Простой способ: передаем cookies через заголовки
# Более надежный: использовать файл cookies.txt

# Вариант 1: Прямая передача cookies (экспортируйте из браузера)
# Вставьте свои cookies из расширения "Get cookies.txt LOCALLY"
# Формат: name=value; name2=value2
COOKIES_STRING = os.environ.get('YOUTUBE_COOKIES', '')

# Вариант 2: Использовать cookies-файл (если есть)
# Положите файл cookies.txt в папку с приложением
COOKIES_FILE = 'cookies.txt'

def get_cookies():
    """Возвращает cookies для yt-dlp"""
    # Если есть cookies-строка из переменной окружения
    if COOKIES_STRING:
        return COOKIES_STRING
    
    # Если есть файл cookies.txt
    if os.path.exists(COOKIES_FILE):
        with open(COOKIES_FILE, 'r') as f:
            return f.read().strip()
    
    return None

# ============================================================
# ОСНОВНОЙ КОД
# ============================================================

@app.route('/')
def index():
    return jsonify({
        'status': 'ok',
        'message': 'YouTube Downloader API работает',
        'time': time.ctime(),
        'cookies_set': bool(get_cookies())
    })

@app.route('/info')
def get_info():
    url = request.args.get('url')
    if not url:
        return jsonify({'error': 'No URL'}), 400
    
    try:
        # Базовые опции yt-dlp
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'socket_timeout': 30,
            'ignoreerrors': True,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-us,en;q=0.5',
            }
        }
        
        # Добавляем cookies если есть
        cookies = get_cookies()
        if cookies:
            # Для yt-dlp используем --cookies
            ydl_opts['cookiefile'] = cookies if os.path.exists(cookies) else None
            # Или добавляем в заголовки
            ydl_opts['http_headers']['Cookie'] = cookies
        
        # Добавляем параметры для обхода ограничений
        ydl_opts['extractor_args'] = {
            'youtube': {
                'player_client': ['android', 'web'],
                'skip': ['hls', 'dash'],
            }
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            if not info:
                return jsonify({'error': 'Не удалось получить информацию'}), 500
            
            video_url = None
            audio_url = None
            
            for f in info.get('formats', []):
                if f.get('ext') == 'mp4' and f.get('vcodec') != 'none' and f.get('acodec') != 'none':
                    if not video_url or f.get('height', 0) > 720:
                        video_url = f.get('url')
                if f.get('acodec') != 'none' and f.get('vcodec') == 'none':
                    if not audio_url or f.get('abr', 0) > 128:
                        audio_url = f.get('url')
            
            return jsonify({
                'success': True,
                'title': info.get('title', 'Без названия'),
                'video': video_url,
                'audio': audio_url,
                'duration': info.get('duration', 0)
            })
            
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Ошибка: {error_msg}")
        
        # Если ошибка "Sign in" — подсказываем решение
        if "sign in" in error_msg.lower() or "bot" in error_msg.lower():
            return jsonify({
                'error': 'YouTube требует подтверждения. Добавьте cookies. Инструкция: https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp'
            }), 403
        
        return jsonify({'error': error_msg}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("=" * 50)
    print("🚀 YouTube Downloader API")
    print(f"📡 Порт: {port}")
    print(f"🍪 Cookies: {'✅ установлены' if get_cookies() else '❌ не установлены'}")
    print("🔄 Keep-alive: включён")
    print("=" * 50)
    app.run(host='0.0.0.0', port=port, debug=False)
