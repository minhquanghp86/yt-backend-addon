# Base image: official Python slim — gọn, ít layer
FROM python:3.12-slim

# Install system deps cần thiết cho yt-dlp
# - ffmpeg: mux/demux audio+video
# - ca-certificates: SSL trust chain
# - curl: health check
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    ca-certificates \
    curl \
  && rm -rf /var/lib/apt/lists/*

# Copy requirements trước để leverage Docker layer cache
# (chỉ rebuild layer này nếu requirements thay đổi)
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code + static UI
COPY app.py .
COPY static/ static/

# Expose port — phải match với config.json
EXPOSE 5000

# Health check: HA dùng cái này để biết container có healthy không
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD curl -sf http://localhost:${PORT:-5000}/ || exit 1

# Run app
# Dùng ENV PORT từ config.json, default 5000 nếu không set
ENV PORT=5000
ENTRYPOINT ["python", "app.py"]
