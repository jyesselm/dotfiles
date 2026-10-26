# Home dashboard. Standard library only.
FROM python:3.12-slim
WORKDIR /app
COPY server.py ./
COPY static ./static
CMD ["python", "-u", "server.py"]
