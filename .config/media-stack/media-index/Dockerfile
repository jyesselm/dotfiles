# Media index: scanner + review page. Standard library only; ffprobe comes from Debian's ffmpeg.
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY index.py server.py arr.py ./
COPY static ./static
CMD ["python", "-u", "server.py"]
