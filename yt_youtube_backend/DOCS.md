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