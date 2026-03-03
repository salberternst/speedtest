#!/usr/bin/env python3
"""
Network Speed & Latency Tester

Tests upload speed and measures latency during transfers
to diagnose internet connectivity problems.
"""

import argparse
import http.client
import json
import os
import ssl
import statistics
import sys
import threading
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from report_to_html import render_html


@dataclass
class SpeedResult:
    direction: str
    endpoint: str
    size_bytes: int
    duration_s: float
    success: bool
    error: str = ""

    @property
    def speed_mbps(self):
        if self.duration_s > 0:
            return (self.size_bytes * 8) / (self.duration_s * 1_000_000)
        return 0.0

    @property
    def speed_mbs(self):
        if self.duration_s > 0:
            return self.size_bytes / (self.duration_s * 1_000_000)
        return 0.0


_ssl_ctx = None


def make_ssl_context(insecure=False):
    if insecure:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx
    return ssl.create_default_context()


def get_ssl_ctx():
    return _ssl_ctx or ssl.create_default_context()


def fmt_speed(mbps):
    if mbps >= 1:
        return f"{mbps:.2f} Mbps"
    return f"{mbps * 1000:.1f} kbps"


def print_stats(transferred, total, elapsed, monitor, prefix="", samples=None):
    """Print a single-line stats update and optionally record a sample."""
    pct = transferred / total * 100 if total else 0
    speed_mbps = (transferred * 8) / (elapsed * 1_000_000) if elapsed > 0 else 0
    speed_mbs = transferred / (elapsed * 1_000_000) if elapsed > 0 else 0
    transferred_mb = transferred / 1_048_576
    total_mb = total / 1_048_576

    valid = [s for s in monitor.samples if s is not None] if monitor.samples else []
    if valid:
        lat_avg = statistics.mean(valid[-10:])
        lat_last = valid[-1]
        lat_str = f"lat={lat_last:.0f}ms avg={lat_avg:.0f}ms"
    else:
        lat_avg = None
        lat_last = None
        lat_str = "lat=--"

    line = (
        f"  {prefix} {transferred_mb:6.1f}/{total_mb:.0f} MiB  "
        f"{pct:5.1f}%  "
        f"{fmt_speed(speed_mbps):>12s} ({speed_mbs:.2f} MB/s)  "
        f"{lat_str}"
    )

    sys.stdout.write(f"\r{line:<100}")
    sys.stdout.flush()

    if samples is not None:
        samples.append(
            {
                "t": round(elapsed, 3),
                "bytes": transferred,
                "speed_mbps": round(speed_mbps, 2),
                "latency_ms": round(lat_last, 1) if lat_last is not None else None,
                "latency_avg_ms": round(lat_avg, 1) if lat_avg is not None else None,
            }
        )


def heading(text):
    print(f"\n{'─' * 60}")
    print(f"  {text}")
    print(f"{'─' * 60}")


def make_report_filename(timestamp_str):
    """Build a safe report filename from the run timestamp."""
    base = timestamp_str.replace(" ", "_").replace(":", "-")
    filename = f"{base}.json"
    if not os.path.exists(filename):
        return filename

    n = 2
    while True:
        candidate = f"{base}_{n}.json"
        if not os.path.exists(candidate):
            return candidate
        n += 1


class LatencyMonitor:
    """Measures HTTP latency in background during transfers."""

    def __init__(self, interval=0.5):
        self.interval = interval
        self.samples = []
        self._stop = threading.Event()
        self._thread = None

    def start(self):
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)

    def _run(self):
        ctx = get_ssl_ctx()
        while not self._stop.is_set():
            try:
                start = time.perf_counter()
                req = urllib.request.Request(
                    "https://cloudflare.com/cdn-cgi/trace", method="GET"
                )
                req.add_header("User-Agent", "speedtest-cli/1.0")
                with urllib.request.urlopen(req, timeout=3, context=ctx) as resp:
                    resp.read()
                elapsed = (time.perf_counter() - start) * 1000
                self.samples.append(elapsed)
            except Exception:
                self.samples.append(None)
            self._stop.wait(self.interval)

    def summary(self):
        valid = [s for s in self.samples if s is not None]
        failed = sum(1 for s in self.samples if s is None)
        if not valid:
            return {
                "avg_ms": None,
                "max_ms": None,
                "min_ms": None,
                "jitter_ms": None,
                "samples": len(self.samples),
                "loss_pct": (failed / len(self.samples) * 100) if self.samples else 0,
            }
        diffs = [abs(valid[i] - valid[i - 1]) for i in range(1, len(valid))]
        return {
            "avg_ms": statistics.mean(valid),
            "max_ms": max(valid),
            "min_ms": min(valid),
            "jitter_ms": statistics.mean(diffs) if diffs else 0,
            "samples": len(self.samples),
            "loss_pct": (failed / len(self.samples) * 100) if self.samples else 0,
        }


def generate_payload(size_mb):
    """Generate random-ish bytes for upload."""
    if size_mb <= 0:
        raise ValueError("upload size must be > 0 MiB")

    target_size = size_mb * 1_048_576
    chunk = os.urandom(min(target_size, 1_048_576))
    repeats = (target_size + len(chunk) - 1) // len(chunk)
    return (chunk * repeats)[:target_size]


def test_upload(upload_endpoints, size_mb=10, upload_limit_mbps=None):
    print(f"\n  Generating {size_mb} MiB payload...")
    data = generate_payload(size_mb)
    actual_size = len(data)

    if upload_limit_mbps:
        rate_bytes = upload_limit_mbps * 1_000_000 / 8
        print(
            f"  Bandwidth limit: {upload_limit_mbps} Mbps ({rate_bytes / 1_048_576:.1f} MiB/s)"
        )
    else:
        rate_bytes = None

    monitor = LatencyMonitor()
    samples = []
    attempted_bytes = 0
    attempted_duration_s = 0.0

    for url in upload_endpoints:
        name = urlparse(url).netloc or url
        print(f"  Uploading {size_mb} MiB to {name}...")

        if not monitor._thread:
            monitor.start()

        conn = None
        start = None
        sent = 0
        try:
            ctx = get_ssl_ctx()
            parsed = urlparse(url)
            if parsed.scheme == "https":
                conn = http.client.HTTPSConnection(
                    parsed.hostname, parsed.port or 443, context=ctx, timeout=300
                )
            else:
                conn = http.client.HTTPConnection(
                    parsed.hostname, parsed.port or 80, timeout=300
                )

            headers = {
                "User-Agent": "speedtest-cli/1.0",
                "Content-Type": "application/octet-stream",
                "Content-Length": str(actual_size),
            }
            conn.putrequest(
                "POST", parsed.path + ("?" + parsed.query if parsed.query else "")
            )
            for k, v in headers.items():
                conn.putheader(k, v)
            conn.endheaders()

            chunk_size = 65536
            start = time.perf_counter()
            last_print = start
            while sent < actual_size:
                end = min(sent + chunk_size, actual_size)
                conn.send(data[sent:end])
                sent = end
                now = time.perf_counter()
                if now - last_print >= 0.5:
                    print_stats(
                        sent,
                        actual_size,
                        now - start,
                        monitor,
                        prefix="UL",
                        samples=samples,
                    )
                    last_print = now
                if rate_bytes:
                    elapsed = now - start
                    expected = sent / rate_bytes
                    if expected > elapsed:
                        time.sleep(expected - elapsed)

            send_duration = time.perf_counter() - start
            print_stats(
                sent, actual_size, send_duration, monitor, prefix="UL", samples=samples
            )
            print()

            resp = conn.getresponse()
            resp_body = resp.read()
            if not (200 <= resp.status < 300):
                snippet = resp_body[:200].decode("utf-8", errors="replace")
                raise RuntimeError(f"HTTP {resp.status} {resp.reason}: {snippet}")
            conn.close()
            result = SpeedResult("upload", name, sent, send_duration, True)
            monitor.stop()
            return result, monitor.summary(), samples

        except Exception as e:
            if start is not None:
                attempted_duration_s += time.perf_counter() - start
            attempted_bytes += sent
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass
            print(f"\n    Failed ({name}): {e}")
            continue

    monitor.stop()
    return (
        SpeedResult(
            "upload",
            "all",
            attempted_bytes,
            attempted_duration_s,
            False,
            "All endpoints failed",
        ),
        monitor.summary(),
        samples,
    )


def run_full_test(args):
    results = {"timestamp": time.strftime("%Y-%m-%d %H:%M:%S")}

    if not args.skip_upload:
        heading("Upload Speed Test")
        ul_result, ul_latency, ul_samples = test_upload(
            upload_endpoints=args.upload_endpoint,
            size_mb=args.upload_size,
            upload_limit_mbps=args.upload_limit,
        )
        if ul_result.success:
            print(
                f"  Speed: {fmt_speed(ul_result.speed_mbps)}  ({ul_result.speed_mbs:.2f} MB/s)"
            )
            print(
                f"  Duration: {ul_result.duration_s:.2f}s  Size: {ul_result.size_bytes / 1_048_576:.1f} MiB"
            )
        else:
            print(f"  Upload FAILED: {ul_result.error}")
        if ul_latency and ul_latency.get("avg_ms"):
            print(
                f"  Latency during upload: avg={ul_latency['avg_ms']:.0f}ms  "
                f"max={ul_latency['max_ms']:.0f}ms  jitter={ul_latency['jitter_ms']:.0f}ms  "
                f"loss={ul_latency['loss_pct']:.0f}%"
            )
        results["upload"] = {
            "success": ul_result.success,
            "error": ul_result.error or None,
            "speed_mbps": ul_result.speed_mbps if ul_result.success else 0.0,
            "size_mb": ul_result.size_bytes / 1_000_000,
            "size_mib": ul_result.size_bytes / 1_048_576,
            "size_bytes": ul_result.size_bytes,
            "duration_s": ul_result.duration_s,
            "endpoint": ul_result.endpoint,
            "latency_during": ul_latency,
            "samples": ul_samples,
        }

    heading("SUMMARY")
    print(f"  Timestamp: {results['timestamp']}")
    if "upload" in results and results["upload"].get("success"):
        print(f"  Upload:    {fmt_speed(results['upload']['speed_mbps'])}")

    issues = []
    if "upload" in results and results["upload"].get("latency_during"):
        ul_lat = results["upload"]["latency_during"]
        if ul_lat.get("loss_pct", 0) > 5:
            issues.append("Packet loss during upload — possible upstream congestion")
        if ul_lat.get("jitter_ms", 0) > 50:
            issues.append("High jitter during upload — unstable upstream connection")

    if issues:
        print("\n  ISSUES DETECTED:")
        for issue in issues:
            print(f"    ! {issue}")
    else:
        print("\n  No obvious issues detected.")

    if args.report:
        report_name = make_report_filename(results["timestamp"])
        with open(report_name, "w") as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\n  JSON report saved to: {report_name}")

        html_name = str(Path(report_name).with_suffix(".html"))
        try:
            html_content = render_html(results, Path(report_name).name)
            Path(html_name).write_text(html_content, encoding="utf-8")
            print(f"  HTML report saved to: {html_name}")
        except Exception as e:
            print(f"  HTML report generation failed: {e}")

    print()
    return results


def main():
    def positive_int(value):
        value = int(value)
        if value <= 0:
            raise argparse.ArgumentTypeError("must be greater than 0")
        return value

    def non_negative_int(value):
        value = int(value)
        if value < 0:
            raise argparse.ArgumentTypeError("must be greater than or equal to 0")
        return value

    def positive_float(value):
        value = float(value)
        if value <= 0:
            raise argparse.ArgumentTypeError("must be greater than 0")
        return value

    def upload_endpoint(value):
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise argparse.ArgumentTypeError(
                "must be an absolute http(s) URL, e.g. https://example.com/up"
            )
        return value

    parser = argparse.ArgumentParser(
        description="Network Speed & Latency Tester — diagnose internet problems",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 speedtest.py --upload-endpoint https://speed.cloudflare.com/__up
  python3 speedtest.py --upload-endpoint https://speed.cloudflare.com/__up --upload-size 50
                                          Upload 50MiB test file
  python3 speedtest.py --upload-endpoint https://speed.cloudflare.com/__up --upload-limit 5
                                          Limit upload to 5 Mbps
  python3 speedtest.py --skip-upload       Skip upload test
  python3 speedtest.py --upload-endpoint https://speed.cloudflare.com/__up --report
                                          Save JSON + HTML report to timestamp filename
  python3 speedtest.py --upload-endpoint https://speed.cloudflare.com/__up --repeat 5 --interval 60
                                          Run 5 times, 60s apart
  python3 speedtest.py --upload-endpoint https://speed.cloudflare.com/__up --insecure
                                          Ignore SSL certificate errors
        """,
    )
    parser.add_argument(
        "--upload-endpoint",
        type=upload_endpoint,
        action="append",
        default=[],
        metavar="URL",
        help="Upload endpoint URL (repeatable, required unless --skip-upload)",
    )
    parser.add_argument(
        "--upload-size",
        type=positive_int,
        default=10,
        help="Upload size in MiB (default: 10)",
    )
    parser.add_argument(
        "--upload-limit",
        type=positive_float,
        default=None,
        help="Limit upload bandwidth in Mbps (e.g. 5 for 5 Mbps)",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Save JSON + HTML reports to <timestamp>.json/.html",
    )
    parser.add_argument(
        "--repeat",
        type=positive_int,
        default=1,
        help="Number of test rounds (default: 1)",
    )
    parser.add_argument(
        "--interval",
        type=non_negative_int,
        default=60,
        help="Seconds between rounds (default: 60)",
    )
    parser.add_argument("--skip-upload", action="store_true", help="Skip upload test")
    parser.add_argument(
        "--insecure",
        "-k",
        action="store_true",
        help="Ignore SSL certificate errors (like curl -k)",
    )

    args = parser.parse_args()
    if not args.skip_upload and not args.upload_endpoint:
        parser.error("--upload-endpoint is required unless --skip-upload is set")

    global _ssl_ctx
    _ssl_ctx = make_ssl_context(insecure=args.insecure)
    if args.insecure:
        import warnings

        warnings.filterwarnings("ignore", message="Unverified HTTPS request")

    print("╔══════════════════════════════════════════════════════════╗")
    print("║         Network Speed & Latency Tester                  ║")
    print("╚══════════════════════════════════════════════════════════╝")

    for i in range(args.repeat):
        if args.repeat > 1:
            print(f"\n{'=' * 60}")
            print(f"  Round {i + 1} of {args.repeat}")
            print(f"{'=' * 60}")

        run_full_test(args)

        if i < args.repeat - 1:
            print(f"\n  Waiting {args.interval}s before next round...")
            time.sleep(args.interval)

    print("Done.")


if __name__ == "__main__":
    main()
