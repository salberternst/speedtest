# Network Speed & Latency Tester

Small toolkit for diagnosing unstable network behavior at work or home.

## Included

- `speedtest.py`: HTTP upload test with live latency sampling and JSON + HTML reports.
- `report_to_html.py`: Convert a JSON report into a self-contained interactive HTML plot.
- `server/`: Minimal Python upload sink (`/up`, `/health`) plus Dockerfile for self-hosting.

## Quick Start

```bash
python3 speedtest.py --upload-endpoint https://speed.cloudflare.com/__up --report
python3 speedtest.py --upload-endpoint http://127.0.0.1:8080/up --upload-size 40 --upload-limit 1 --report
```

`--report` now exports both `<timestamp>.json` and `<timestamp>.html`.

## Run the Test Server

```bash
cd server
docker compose up --build
```

Then point `speedtest.py` upload endpoint to your own server URL.

## Interactive Report Plot

```bash
python3 report_to_html.py 2026-03-03_11-36-52.json
```

This writes `2026-03-03_11-36-52.html` next to the JSON file. You can open it by double-clicking the HTML file in your file manager.

## Similar Testing with iperf3

If you want a lower-level throughput baseline, run `iperf3` between two hosts:

```bash
# on the remote/server host
iperf3 -s

# from your test machine (upload-like test: client -> server)
iperf3 -c <server-host-or-ip> -t 30 -i 1 -P 4

# from your test machine (download-like test: server -> client)
iperf3 -c <server-host-or-ip> -t 30 -i 1 -P 4 -R
```

`-i 1` prints per-second stats, `-P 4` uses parallel streams, and `-R` reverses direction.

## Notes

- Public test endpoints may timeout or rate-limit long uploads.
