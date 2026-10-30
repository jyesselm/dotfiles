# Media index: scanner + review page. Standard library only; ffprobe comes from Debian's ffmpeg;
# rsync is for drives.py queue (cold-drive moves, run in a one-off copy of this container).
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg rsync && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY index.py server.py arr.py shrink.py drives.py downloads_cap.py ./
COPY static ./static
CMD ["python", "-u", "server.py"]
