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

## Run (Docker Compose, published image)

```bash
cd server
cp .env.example .env
# edit .env and set TRAEFIK_HOST + TRAEFIK_ACME_EMAIL
docker compose -f docker-compose.yml up -d
```

## Run (Docker Compose, local build override)

```bash
cd server
docker compose -f docker-compose.yml -f docker-compose.override.yml up --build
```

### Environment variables

- `TRAEFIK_HOST`: domain Traefik should route to (for example `speedtest.example.com`)
- `TRAEFIK_ACME_EMAIL`: email used for Let's Encrypt registration
- `TRAEFIK_HTTPS_PORT`: optional host-side HTTPS port (default `443`)
- `TRAEFIK_READ_TIMEOUT`: max time Traefik reads request (body) from client (default `10m`)
- `TRAEFIK_WRITE_TIMEOUT`: max time Traefik writes response to client (default `10m`)
- `TRAEFIK_IDLE_TIMEOUT`: keep-alive idle timeout (default `10m`)

## Quick test

```bash
dd if=/dev/zero bs=1M count=50 | \
curl -sS -o /dev/null -w "code=%{http_code} bytes=%{size_upload} time=%{time_total}\n" \
  --data-binary @- https://yourdomain.com/up
```
