from flask import Flask, request, jsonify, send_from_directory, Response, stream_with_context
import yt_dlp
import os
from dotenv import load_dotenv
import requests
from urllib.parse import quote, unquote

# Load environment
load_dotenv()

API_KEY = os.getenv("API_KEY", "mqsmarthome")
PORT = int(os.getenv("PORT", 5000))
GO2RTC_URL = os.getenv("GO2RTC_URL", "http://localhost:1985")

app = Flask(__name__, static_folder="static")

# Simple API key auth
def auth(req):
    if not API_KEY:
        return True
    return req.headers.get("X-API-Key") == API_KEY


# ======================
# CONFIG ENDPOINT
# ======================

@app.route('/config', methods=['GET'])
def get_config():
    """Frontend gọi endpoint này để lấy API_KEY — không cần hardcode trong JS"""
    return jsonify({"api_key": API_KEY})


# ======================
# PROXY ENDPOINTS
# ======================

@app.route('/proxy', methods=['GET', 'OPTIONS'])
def proxy_stream():
    """Proxy video/audio stream"""
    if request.method == 'OPTIONS':
        response = Response()
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Range, Content-Type, Accept'
        response.headers['Access-Control-Max-Age'] = '3600'
        return response
    
    url = request.args.get('url')
    if not url:
        return jsonify({"error": "missing url parameter"}), 400
    
    try:
        url = unquote(url)
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.youtube.com/',
            'Origin': 'https://www.youtube.com',
            'Sec-Fetch-Dest': 'video',
            'Sec-Fetch-Mode': 'no-cors',
            'Sec-Fetch-Site': 'cross-site',
        }
        
        # Range request support
        range_header = request.headers.get('Range')
        if range_header:
            headers['Range'] = range_header
        
        # Tăng timeout và thêm retry logic
        session = requests.Session()
        session.mount('https://', requests.adapters.HTTPAdapter(max_retries=3))
        
        resp = session.get(
            url, 
            headers=headers, 
            stream=True, 
            timeout=60,
            allow_redirects=True
        )
        
        # Check status
        if resp.status_code not in [200, 206]:
            print(f"Proxy error: Status {resp.status_code}")
            return jsonify({"error": f"Upstream returned {resp.status_code}"}), resp.status_code
        
        @stream_with_context
        def generate():
            try:
                for chunk in resp.iter_content(chunk_size=16384):
                    if chunk:
                        yield chunk
            except Exception as e:
                print(f"Stream error: {e}")
        
        response = Response(generate(), status=resp.status_code)
        
        # CORS headers
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Range'
        response.headers['Access-Control-Expose-Headers'] = 'Content-Length, Content-Range, Accept-Ranges, Content-Type'
        
        # Content headers
        response.headers['Content-Type'] = resp.headers.get('Content-Type', 'video/mp4')
        
        if 'Content-Length' in resp.headers:
            response.headers['Content-Length'] = resp.headers['Content-Length']
        if 'Content-Range' in resp.headers:
            response.headers['Content-Range'] = resp.headers['Content-Range']
        
        response.headers['Accept-Ranges'] = 'bytes'
        response.headers['Cache-Control'] = 'public, max-age=3600'
            
        return response
        
    except requests.exceptions.Timeout:
        print("Proxy timeout")
        return jsonify({"error": "Request timeout"}), 504
    except requests.exceptions.ConnectionError as e:
        print(f"Connection error: {e}")
        return jsonify({"error": "Connection failed"}), 502
    except Exception as e:
        print(f"Proxy error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/proxy_m3u8', methods=['GET', 'OPTIONS'])
def proxy_m3u8():
    """Proxy m3u8 playlist và rewrite URLs"""
    if request.method == 'OPTIONS':
        response = Response()
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return response
    
    url = request.args.get('url')
    if not url:
        return jsonify({"error": "missing url parameter"}), 400
    
    try:
        url = unquote(url)
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://www.youtube.com/',
            'Origin': 'https://www.youtube.com',
            'Accept': '*/*'
        }
        
        resp = requests.get(url, headers=headers, timeout=15)
        
        if resp.status_code != 200:
            print(f"M3U8 fetch error: {resp.status_code}")
            return jsonify({"error": f"Failed to fetch m3u8: {resp.status_code}"}), resp.status_code
        
        content = resp.text
        lines = content.split('\n')
        new_lines = []
        base_url = '/'.join(url.split('/')[:-1])
        
        for line in lines:
            stripped = line.strip()
            
            # Skip empty lines and comments
            if not stripped or stripped.startswith('#'):
                new_lines.append(line)
                continue
            
            # Process URL lines
            if stripped.startswith('http'):
                # Absolute URL
                proxied_url = f"/proxy?url={quote(stripped)}"
            else:
                # Relative URL
                full_url = f"{base_url}/{stripped}"
                proxied_url = f"/proxy?url={quote(full_url)}"
            
            new_lines.append(proxied_url)
        
        modified_content = '\n'.join(new_lines)
        
        response = Response(modified_content, mimetype='application/vnd.apple.mpegurl')
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response.headers['Cache-Control'] = 'no-cache'
        
        return response
        
    except requests.exceptions.Timeout:
        print("M3U8 timeout")
        return jsonify({"error": "M3U8 fetch timeout"}), 504
    except Exception as e:
        print(f"M3U8 proxy error: {e}")
        return jsonify({"error": str(e)}), 500


# ======================
# SEARCH ENDPOINT (legacy, giữ để backward compatible)
# ======================

@app.route('/search', methods=['POST'])
def search_video():
    """Legacy endpoint - trả về proxy URLs cho frontend"""
    if not auth(request):
        return jsonify({"error": "unauthorized"}), 401
        
    data = request.get_json(silent=True) or {}
    query = data.get("query", "").strip()

    if not query:
        return jsonify({"success": False, "error": "missing query"}), 400

    ydl_opts = {
        "quiet": True,
        "default_search": "ytsearch1",
        "skip_download": True,
        "noplaylist": True,
        "format": "bestaudio/best",
        "extractor_args": {
            "youtube": {
                "player_client": ["web", "android", "ios", "web_creator"],
                "player_skip": ["js", "web"],
            }
        },
        "no_warnings": False,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(query, download=False)
            if "entries" in info:
                info = info["entries"][0]

        # Extract audio stream - proxy qua backend
        stream_url = None
        for f in info.get("formats", []):
            url = f.get("url")
            if url and "googlevideo.com" in url and f.get("acodec") != "none" and f.get("vcodec") == "none":
                stream_url = f"/proxy?url={quote(url)}"
                break

        # Extract video
        video_url = None
        best_video = None
        best_height = 0
        
        for f in info.get("formats", []):
            url = f.get("url", "")
            if "googlevideo.com" in url and f.get("vcodec") != "none":
                height = f.get("height", 0) or 0
                if height > best_height:
                    best_height = height
                    best_video = url
        
        if best_video:
            video_url = f"/proxy?url={quote(best_video)}"

        if not stream_url and not video_url:
            return jsonify({"success": False, "error": "no playable stream"}), 200

        result = {
            "success": True,
            "title": info.get("title"),
            "duration": info.get("duration"),
            "stream_url": stream_url or video_url,
            "video_url": video_url,
            "thumbnail": f"https://i.ytimg.com/vi/{info.get('id')}/hqdefault.jpg",
            "artist": info.get("channel", ""),
        }
        return jsonify(result)

    except Exception as e:
        print(f"Search error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/get_video_stream', methods=['POST'])
def get_video_stream():
    """Legacy endpoint - trả về proxy URLs cho frontend"""
    if not auth(request):
        return jsonify({"error": "unauthorized"}), 401
        
    data = request.get_json(silent=True) or {}
    query = data.get("query", "").strip()

    if not query:
        return jsonify({"success": False, "error": "missing query"}), 400

    ydl_opts = {
        "quiet": True,
        "default_search": "ytsearch1",
        "skip_download": True,
        "noplaylist": True,
        "format": "best[ext=mp4][height<=1080]/best[height<=1080]/best",
        "live_from_start": True,
        "extractor_retries": 10,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(query, download=False)

            if "entries" in info and info["entries"]:
                info = info["entries"][0]

            is_live = info.get("is_live") or info.get("live_status") == "is_live"

            video_url = None
            best_format = None
            best_height = 0
            
            for f in info.get("formats", []):
                url = f.get("url", "")
                protocol = f.get("protocol", "")
                vcodec = f.get("vcodec", "none")
                acodec = f.get("acodec", "none")
                
                if ("googlevideo.com" in url and 
                    vcodec != "none" and 
                    acodec != "none" and
                    not protocol.startswith("m3u8")):
                    
                    height = f.get("height", 0) or 0
                    if height <= 1080 and height > best_height:
                        best_height = height
                        best_format = f
            
            if best_format:
                video_url = f"/proxy?url={quote(best_format['url'])}"
                print(f"✓ Selected format: {best_format.get('format_id')} - {best_height}p")

            if not video_url and 'url' in info:
                video_url = f"/proxy?url={quote(info['url'])}"

            if not video_url:
                return jsonify({
                    "success": False, 
                    "error": "Không tìm thấy stream video có âm thanh"
                }), 200

            result = {
                "success": True,
                "title": info.get("title"),
                "duration": info.get("duration"),
                "video_url": video_url,
                "is_live": is_live,
                "thumbnail": f"https://i.ytimg.com/vi/{info.get('id')}/hqdefault.jpg",
                "artist": info.get("channel", ""),
            }
            return jsonify(result)

    except yt_dlp.utils.DownloadError as de:
        print(f"yt-dlp error: {de}")
        return jsonify({"success": False, "error": f"yt-dlp error: {str(de)}"}), 500
    except Exception as e:
        print(f"Get video error: {e}")
        return jsonify({"success": False, "error": f"Unexpected error: {str(e)}"}), 500


# ======================
# CẢI TIẾN 3: ENDPOINT /PLAY - Trả về direct YouTube URLs
# ======================

@app.route('/play', methods=['POST'])
def play_direct():
    """
    CẢI TIẾN 3: All-in-one endpoint
    - Search YouTube
    - Extract direct stream URLs (không qua proxy)
    - Trả về URLs ready cho go2rtc pull trực tiếp
    """
    if not auth(request):
        return jsonify({"error": "unauthorized"}), 401
    
    data = request.get_json(silent=True) or {}
    query = data.get("query", "").strip()

    if not query:
        return jsonify({"success": False, "error": "missing query"}), 400

    print(f"[/play] Query: {query}")

    ydl_opts = {
        "quiet": True,
        "default_search": "ytsearch1",
        "skip_download": True,
        "noplaylist": True,
        "format": "best[ext=mp4][height<=1080]/best[height<=1080]/best",
        "extractor_args": {
            "youtube": {
                "player_client": ["web", "android", "ios"],
            }
        },
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(query, download=False)
            if "entries" in info:
                info = info["entries"][0]

        # Extract best video URL (có audio)
        video_url = None
        audio_url = None
        
        for f in info.get("formats", []):
            url = f.get("url", "")
            vcodec = f.get("vcodec", "none")
            acodec = f.get("acodec", "none")
            
            # Video có cả âm thanh
            if vcodec != "none" and acodec != "none" and not video_url:
                video_url = url
            
            # Audio only
            if vcodec == "none" and acodec != "none" and not audio_url:
                audio_url = url

        if not video_url and not audio_url:
            return jsonify({"success": False, "error": "no stream found"}), 200

        # Fallback: nếu không có audio riêng, dùng video URL cho cả 2
        if not audio_url:
            audio_url = video_url

        result = {
            "success": True,
            "title": info.get("title"),
            "artist": info.get("channel", ""),
            "thumbnail": f"https://i.ytimg.com/vi/{info.get('id')}/hqdefault.jpg",
            "duration": info.get("duration"),
            # Direct URLs - go2rtc pull trực tiếp từ YouTube
            "video_url": video_url,
            "audio_url": audio_url,
        }
        
        print(f"[/play] Found: {result['title']} by {result['artist']}")
        return jsonify(result)

    except Exception as e:
        print(f"[/play] Error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# ======================
# CẢI TIẾN 5: ENDPOINT /PLAY_ON_GO2RTC - Tích hợp go2rtc
# ======================

@app.route('/play_on_go2rtc', methods=['POST'])
def play_on_go2rtc():
    """
    CẢI TIẾN 5: All-in-one endpoint với go2rtc integration
    1. Search YouTube
    2. Extract direct stream URLs
    3. Tự động update go2rtc streams
    4. Return metadata + stream endpoints
    """
    if not auth(request):
        return jsonify({"error": "unauthorized"}), 401
    
    data = request.get_json(silent=True) or {}
    query = data.get("query", "").strip()

    if not query:
        return jsonify({"success": False, "error": "missing query"}), 400

    print(f"[play_on_go2rtc] Query: {query}")

    # Step 1: Search YouTube
    ydl_opts = {
        "quiet": True,
        "default_search": "ytsearch1",
        "skip_download": True,
        "noplaylist": True,
        "format": "best[ext=mp4][height<=1080]/best[height<=1080]/best",
        "extractor_args": {
            "youtube": {
                "player_client": ["web", "android", "ios"],
            }
        },
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(query, download=False)
            if "entries" in info:
                info = info["entries"][0]

        # Step 2: Extract URLs
        video_url = None
        audio_url = None
        
        for f in info.get("formats", []):
            url = f.get("url", "")
            vcodec = f.get("vcodec", "none")
            acodec = f.get("acodec", "none")
            
            # Best video with audio
            if vcodec != "none" and acodec != "none" and not video_url:
                video_url = url
            
            # Best audio only
            if vcodec == "none" and acodec != "none" and not audio_url:
                audio_url = url

        if not video_url and not audio_url:
            return jsonify({"success": False, "error": "no stream found"}), 200

        # Fallback
        if not audio_url:
            audio_url = video_url

        metadata = {
            "title": info.get("title", "Unknown"),
            "artist": info.get("channel", "Unknown"),
            "thumbnail": f"https://i.ytimg.com/vi/{info.get('id')}/hqdefault.jpg",
            "duration": info.get("duration", 0),
        }

        print(f"[play_on_go2rtc] Found: {metadata['title']} by {metadata['artist']}")

        # Step 3: Ghi URLs vào file cho go2rtc đọc
        try:
            # File paths - go2rtc sẽ đọc từ đây qua exec command
            video_url_file = "/config/youtube_url.txt"
            audio_url_file = "/config/youtube_audio_url.txt"
            
            # Ghi video URL
            with open(video_url_file, 'w') as f:
                f.write(video_url)
            print(f"[play_on_go2rtc] Written video URL to {video_url_file}")
            
            # Ghi audio URL
            with open(audio_url_file, 'w') as f:
                f.write(audio_url)
            print(f"[play_on_go2rtc] Written audio URL to {audio_url_file}")
            
        except Exception as e:
            print(f"[play_on_go2rtc] File write error: {e}")
            return jsonify({
                "success": False,
                "error": f"Cannot write URL files: {str(e)}"
            }), 500

        # Step 4: Return success với metadata + go2rtc stream URLs
        video_stream_name = "youtube_video"
        audio_stream_name = "youtube_audio"
        
        return jsonify({
            "success": True,
            "metadata": metadata,
            "streams": {
                # go2rtc stream URLs - đã config sẵn trong go2rtc.yaml
                "video_mjpeg": f"{GO2RTC_URL}/api/stream.mjpeg?src={video_stream_name}",
                "audio_mp3": f"{GO2RTC_URL}/api/stream.mp3?src={audio_stream_name}",
                "video_hls": f"{GO2RTC_URL}/api/stream.m3u8?src={video_stream_name}",
            },
            "go2rtc_stream_names": {
                "video": video_stream_name,
                "audio": audio_stream_name
            },
            "note": "URLs written to /config/youtube_url.txt and /config/youtube_audio_url.txt"
        })

    except yt_dlp.utils.DownloadError as de:
        print(f"[yt-dlp] Error: {de}")
        return jsonify({"success": False, "error": f"yt-dlp error: {str(de)}"}), 500
    except Exception as e:
        print(f"[play_on_go2rtc] Error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# ======================
# Serve UI
# ======================

@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


if __name__ == "__main__":
    print(f"YT Backend Server running on 0.0.0.0:{PORT}")
    print(f"  API_KEY: {API_KEY}")
    print(f"  go2rtc URL: {GO2RTC_URL}")
    print("Endpoints:")
    print("  Legacy: /search, /get_video_stream (proxy URLs)")
    print("  New: /play (direct URLs)")
    print("  Integrated: /play_on_go2rtc (auto update go2rtc)")
    app.run(host="0.0.0.0", port=PORT, threaded=True, debug=False)
