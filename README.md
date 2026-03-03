# Network Speed & Latency Tester

Small toolkit for diagnosing unstable network behavior at work or home.

## Included

- `speedtest.py`: HTTP upload test with live latency sampling and JSON reports.
- `server/`: Minimal Python upload sink (`/up`, `/health`) plus Dockerfile for self-hosting.

## Quick Start

```bash
python3 speedtest.py --upload-endpoint https://speed.cloudflare.com/__up --report
python3 speedtest.py --upload-endpoint http://127.0.0.1:8080/up --upload-size 40 --upload-limit 1 --report
```

## Run the Test Server

```bash
cd server
docker compose up --build
```

Then point `speedtest.py` upload endpoint to your own server URL.

## Notes

- Public test endpoints may timeout or rate-limit long uploads.
