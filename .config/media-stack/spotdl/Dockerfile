# spotDL's image with the newest yt-dlp (YouTube breaks old ones within weeks) and Deno, which yt-dlp needs
# for YouTube's player challenges. Refresh both with: docker-compose build --pull spotdl && docker-compose up -d spotdl
FROM spotdl/spotify-downloader:latest
USER root
COPY --from=denoland/deno:bin /deno /usr/local/bin/deno
RUN uv pip install --python /app/.venv/bin/python --upgrade "yt-dlp[default]" && deno --version
