from flask import Flask, request, jsonify
from flask_cors import CORS
import yt_dlp
import os

app = Flask(__name__)
CORS(app)

@app.route('/info')
def get_info():
    url = request.args.get('url')
    if not url:
        return jsonify({'error': 'No URL'}), 400
    
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
            info = ydl.extract_info(url, download=False)
            
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
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
