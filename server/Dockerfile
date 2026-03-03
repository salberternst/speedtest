FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=8080 \
    CHUNK_SIZE=65536 \
    MAX_BODY_BYTES=0

WORKDIR /app
COPY app.py /app/app.py

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=2).read()"

CMD ["python", "/app/app.py"]
