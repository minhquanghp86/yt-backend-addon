# YouTube Backend Add-on

Self-hosted YouTube streaming backend sử dụng `yt-dlp`. Cung cấp API để search, extract và proxy video/audio stream từ YouTube.

---

## Cấu hình

### API_KEY
- **Mặc định:** `mqsmarthome`
- **Khuyến khích:** Đổi thành giá trị riêng của bạn
- String bất kỳ để authenticate API requests
- Để trống nếu không muốn dùng authentication

### PORT
- **Mặc định:** `5000`
- Port mà backend listen
- Thường không cần thay đổi

---

## Sử dụng

### Giao diện web

Mở tab **Open Web UI** trên add-on này để access giao diện tìm kiếm và phát YouTube.

### API Endpoints

#### POST /search
Tìm kiếm và extract audio stream.

**Request:**
```bash
curl -X POST http://homeassistant.local:5000/search \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY" \
  -d '{"query": "tên bài hát hoặc URL"}'
Response:
{
  "success": true,
  "title": "...",
  "stream_url": "/proxy?url=...",
  "video_url": "/proxy?url=...",
  "thumbnail": "https://...",
  "artist": "...",
  "duration": 240
}
POST /get_video_stream
Extract video stream (có cả audio) lên đến 1080p.
Request: tương tự /search
Response: tương tự /search nhưng prioritize video
Troubleshooting
"no playable stream" error
YouTube có thể đang rate-limit requests
Đợi vài phút rồi thử lại
Đây là giới hạn của yt-dlp, không phải lỗi add-on
Video/audio không phát được
Stream URLs từ YouTube có thời hạn (thường 6 giờ)
Tìm kiếm lại để lấy URL mới
Không kết nối được backend
Check add-on đang chạy: Log tab phải hiện "YT Audio Server running..."
Verify API_KEY trong config khớp với header request
Source Code
Repository: https://github.com/minhquanghp86/yt-backend-addon
Issues & feedback welcome!
