from flask import Flask, request, jsonify
from flask_cors import CORS
import yt_dlp
import requests
import os
import time
import threading

app = Flask(__name__)
CORS(app)

def keep_alive():
    while True:
        try:
            requests.get(f"http://localhost:{os.environ.get('PORT', 5000)}/", timeout=5)
        except:
            pass
        time.sleep(600)

threading.Thread(target=keep_alive, daemon=True).start()

@app.route('/')
def index():
    return jsonify({'status': 'ok', 'message': 'YouTube Downloader API (yt-dlp)'})

@app.route('/info')
def get_info():
    url = request.args.get('url')
    if not url:
        return jsonify({'error': 'No URL'}), 400
    
    try:
        ydl_opts = {'format': 'best', 'noplaylist': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return jsonify({
                'success': True,
                'title': info.get('title', 'Видео'),
                'video': info.get('url'),
                'audio': info.get('url'),
                'duration': info.get('duration', 0)
            })
    except Exception as e:
        print(f"⚠️ Ошибка yt-dlp: {e}")
        return jsonify({'error': 'Не удалось получить ссылку'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
