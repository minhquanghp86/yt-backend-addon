Yêu cầu
Home Assistant OS hoặc Home Assistant Supervised
HA Core (chạy trong Docker standalone) không hỗ trợ add-on
Cài đặt
1. Thêm repository:

Vào Settings → Add-ons → Add-on Store → click ⋮ (menu) → Add Repository → paste URL:

https://github.com/minhquanghp86/yt-backend-addon
2. Install add-on:

Tìm "YouTube Backend" trong danh sách → Install → Start.

Configuration
Đây là các environment variable có thể thay đổi trong UI của add-on:

Variable	Default	Mô tả
API_KEY	mqsmarthome	API key để authenticate requests. Đặt rỗng nếu không muốn auth.
PORT	5000	Port mà backend listen. Thường không cần đổi.
Quan trọng: Đổi API_KEY thành giá trị custom của bạn trước khi start. Không để default.

API Endpoints
POST /search
Search và extract audio stream từ YouTube.

curl -X POST http://localhost:5000/search \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY" \
  -d '{"query": "tên bài hát hoặc URL YouTube"}'
Response:

{
  "success": true,
  "title": "...",
  "duration": 240,
  "stream_url": "/proxy?url=...",
  "video_url": "/proxy?url=...",
  "thumbnail": "https://i.ytimg.com/vi/.../hqdefault.jpg",
  "artist": "..."
}
POST /get_video_stream
Extract video stream (có cả audio) up to 1080p.

curl -X POST http://localhost:5000/get_video_stream \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY" \
  -d '{"query": "tên video hoặc URL YouTube"}'
Response:

{
  "success": true,
  "title": "...",
  "duration": 240,
  "video_url": "/proxy?url=...",
  "is_live": false,
  "thumbnail": "https://i.ytimg.com/vi/.../hqdefault.jpg",
  "artist": "..."
}
GET /proxy?url=<encoded_url>
Proxy video/audio stream từ YouTube. Hỗ trợ Range requests cho seek.

Endpoint này được gọi internally bởi stream_url / video_url trong response của /search và /get_video_stream. Thường không cần gọi trực tiếp.

GET /proxy_m3u8?url=<encoded_url>
Proxy m3u8 playlist và rewrite URLs về /proxy. Được dùng cho live streams.

Khắc phục sự cố
Add-on start nhưng không respond:

Kiểm tra log trong UI của add-on. Thường gặp lỗi yt-dlp nếu YouTube thay đổi API.
Đảm bảo port 5000 không bị block bởi firewall.
"no playable stream" error:

YouTube đang rate-limit hoặc block requests. Đây là giới hạn của yt-dlp, không phải lỗi của add-on.
Thử lại sau một lúc.
API_KEY không đúng:

Check lại giá trị API_KEY trong config. Header cần gửi là X-API-Key.
Ingress
Add-on này hỗ trợ HA Ingress, nghĩa là bạn có thể access nó qua HA UI mà không cần expose port ra ngoài network. URL sẽ có dạng:

http://[HA_IP]:8123/hassio_ingress/[SLUG]/
HA tự generate slug khi install.