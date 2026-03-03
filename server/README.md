# Upload Sink Server

Simple Python server for speed test uploads.

## Endpoints

- `GET /health` -> `200 ok`
- `POST|PUT|PATCH /up` -> reads full body, discards it, returns `204`

## Run (local Python)

```bash
cd server
PORT=8080 python app.py
```

## Run (Docker Compose)

```bash
cd server
docker compose up --build
```

## Quick test

```bash
dd if=/dev/zero bs=1M count=50 | \
curl -sS -o /dev/null -w "code=%{http_code} bytes=%{size_upload} time=%{time_total}\n" \
  --data-binary @- http://127.0.0.1:8080/up
```
