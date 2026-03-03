#!/usr/bin/env python3
"""
Convert a speedtest JSON report into a self-contained interactive HTML file.

The generated HTML includes inline CSS and JavaScript so it can be opened
directly from the filesystem (file://) without a local web server.
"""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert a speedtest JSON report into an interactive HTML plot.",
        epilog="""
Examples:
  python3 report_to_html.py 2026-03-03_11-36-52.json
  python3 report_to_html.py report.json --output report.html
        """,
    )
    parser.add_argument("report", help="Path to input report JSON file")
    parser.add_argument(
        "-o",
        "--output",
        help="Path to output HTML file (default: same name as input, .html)",
    )
    return parser.parse_args()


def load_report(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("Report JSON must be an object at top level")
    return data


def output_path_for(input_path: Path, output_arg: str | None) -> Path:
    if output_arg:
        return Path(output_arg)
    return input_path.with_suffix(".html")


def render_html(report: dict[str, Any], source_name: str) -> str:
    report_json = json.dumps(report, separators=(",", ":"), ensure_ascii=False)
    report_json = report_json.replace("</", "<\\/")
    source_name_escaped = html.escape(source_name)

    template = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Speedtest Report Plot</title>
  <style>
    :root {
      --bg: #0f172a;
      --panel: #111827;
      --panel-2: #0b1222;
      --text: #e5e7eb;
      --muted: #9ca3af;
      --line: #1f2937;
      --accent: #22d3ee;
      --accent-2: #f97316;
      --accent-3: #a78bfa;
      --ok: #22c55e;
      --fail: #ef4444;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: ui-sans-serif, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif;
      color: var(--text);
      background:
        radial-gradient(1200px 500px at 10% -20%, #1e293b 0%, transparent 60%),
        radial-gradient(800px 400px at 90% -10%, #312e81 0%, transparent 55%),
        var(--bg);
    }
    .page {
      max-width: 1200px;
      margin: 0 auto;
      padding: 28px 18px 40px;
    }
    .hero {
      background: linear-gradient(135deg, #0b1222 0%, #101b33 100%);
      border: 1px solid #1f2a44;
      border-radius: 14px;
      padding: 18px 18px 14px;
      margin-bottom: 16px;
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
    }
    .hero h1 {
      margin: 0 0 6px;
      font-size: 1.4rem;
      letter-spacing: 0.2px;
    }
    .hero .meta {
      color: var(--muted);
      font-size: 0.95rem;
    }
    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
      gap: 10px;
      margin-top: 14px;
    }
    .card {
      background: var(--panel);
      border: 1px solid #1f2937;
      border-radius: 10px;
      padding: 10px;
    }
    .label {
      color: var(--muted);
      font-size: 0.78rem;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      margin-bottom: 4px;
    }
    .value {
      font-weight: 600;
      font-size: 1.03rem;
      word-break: break-word;
    }
    .ok { color: var(--ok); }
    .fail { color: var(--fail); }
    .section {
      position: relative;
      margin-top: 18px;
      background: var(--panel-2);
      border: 1px solid #1f2937;
      border-radius: 12px;
      padding: 14px;
    }
    .section h2 {
      margin: 2px 0 12px;
      font-size: 1.08rem;
      letter-spacing: 0.3px;
    }
    .controls {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
      margin-bottom: 10px;
    }
    .control {
      background: #0d1528;
      border: 1px solid #1f2937;
      border-radius: 8px;
      padding: 8px;
    }
    .control-row {
      display: flex;
      justify-content: space-between;
      gap: 8px;
      align-items: center;
      margin-bottom: 5px;
      color: var(--muted);
      font-size: 0.84rem;
    }
    input[type="range"] {
      width: 100%;
      accent-color: var(--accent);
    }
    .legend {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      font-size: 0.85rem;
      color: var(--muted);
      margin: 8px 0 8px;
    }
    .legend span {
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }
    .dot {
      width: 10px;
      height: 10px;
      border-radius: 999px;
      display: inline-block;
    }
    .chart-wrap {
      border: 1px solid #1f2937;
      background: #080f1f;
      border-radius: 8px;
      padding: 8px;
      margin-bottom: 10px;
    }
    canvas {
      display: block;
      width: 100%;
      height: 240px;
    }
    .tooltip {
      position: absolute;
      pointer-events: none;
      background: rgba(10, 15, 26, 0.95);
      border: 1px solid #334155;
      border-radius: 8px;
      padding: 8px 10px;
      font-size: 0.82rem;
      color: #f8fafc;
      transform: translate(10px, 10px);
      white-space: nowrap;
      z-index: 9;
      display: none;
      box-shadow: 0 10px 28px rgba(0, 0, 0, 0.35);
    }
    .empty {
      color: var(--muted);
      font-size: 0.95rem;
      padding: 6px 0 2px;
    }
    @media (max-width: 760px) {
      .controls {
        grid-template-columns: 1fr;
      }
      canvas {
        height: 200px;
      }
    }
  </style>
</head>
<body>
  <main class="page" id="app"></main>
  <script id="report-data" type="application/json">__REPORT_JSON__</script>
  <script>
    const report = JSON.parse(document.getElementById("report-data").textContent);
    const app = document.getElementById("app");

    const SPEED_COLOR = "#22d3ee";
    const LAT_COLOR = "#f97316";
    const LAT_AVG_COLOR = "#a78bfa";

    function el(tag, attrs = {}, children = []) {
      const node = document.createElement(tag);
      for (const [k, v] of Object.entries(attrs)) {
        if (k === "class") node.className = v;
        else if (k === "text") node.textContent = v;
        else node.setAttribute(k, v);
      }
      for (const child of children) {
        node.append(child);
      }
      return node;
    }

    function isNum(value) {
      return typeof value === "number" && Number.isFinite(value);
    }

    function fmtSeconds(value) {
      if (!isNum(value)) return "-";
      if (value < 60) return value.toFixed(2) + " s";
      const min = Math.floor(value / 60);
      const sec = value % 60;
      return min + "m " + sec.toFixed(1) + "s";
    }

    function fmtMbps(value) {
      if (!isNum(value)) return "-";
      if (value >= 1) return value.toFixed(2) + " Mbps";
      return (value * 1000).toFixed(1) + " kbps";
    }

    function fmtMs(value) {
      if (!isNum(value)) return "-";
      return value.toFixed(1) + " ms";
    }

    function fmtSizeBytes(bytes) {
      if (!isNum(bytes)) return "-";
      const mib = bytes / 1048576;
      if (mib >= 1024) return (mib / 1024).toFixed(2) + " GiB";
      return mib.toFixed(2) + " MiB";
    }

    function fmtPct(value) {
      if (!isNum(value)) return "-";
      return value.toFixed(1) + "%";
    }

    function nearestByTime(samples, t) {
      if (!samples.length) return null;
      let lo = 0;
      let hi = samples.length - 1;
      while (lo < hi) {
        const mid = Math.floor((lo + hi) / 2);
        if (samples[mid].t < t) lo = mid + 1;
        else hi = mid;
      }
      const a = samples[Math.max(0, lo - 1)];
      const b = samples[lo];
      if (!a) return b;
      if (!b) return a;
      return Math.abs(a.t - t) <= Math.abs(b.t - t) ? a : b;
    }

    function setupCanvas(canvas) {
      const ratio = window.devicePixelRatio || 1;
      const cssW = Math.max(320, canvas.clientWidth);
      const cssH = Math.max(170, canvas.clientHeight);
      canvas.width = Math.floor(cssW * ratio);
      canvas.height = Math.floor(cssH * ratio);
      const ctx = canvas.getContext("2d");
      ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
      return { ctx, width: cssW, height: cssH };
    }

    function drawChart(opts) {
      const { canvas, xMin, xMax, series, xLabel, yLabel } = opts;
      const activeSeries = series.filter((s) => s.enabled && s.points.length > 0);
      const { ctx, width, height } = setupCanvas(canvas);

      const margin = { top: 10, right: 14, bottom: 28, left: 54 };
      const plotW = width - margin.left - margin.right;
      const plotH = height - margin.top - margin.bottom;
      const xToPx = (x) => margin.left + ((x - xMin) / (xMax - xMin || 1)) * plotW;

      let yMin = Infinity;
      let yMax = -Infinity;
      for (const s of activeSeries) {
        for (const p of s.points) {
          if (p.t < xMin || p.t > xMax) continue;
          if (p.v < yMin) yMin = p.v;
          if (p.v > yMax) yMax = p.v;
        }
      }

      if (!Number.isFinite(yMin) || !Number.isFinite(yMax)) {
        yMin = 0;
        yMax = 1;
      }
      if (Math.abs(yMax - yMin) < 1e-9) {
        yMin = Math.max(0, yMin - 0.5);
        yMax = yMax + 0.5;
      }
      const pad = (yMax - yMin) * 0.08;
      yMin = Math.max(0, yMin - pad);
      yMax = yMax + pad;

      const yToPx = (y) => margin.top + (1 - (y - yMin) / (yMax - yMin || 1)) * plotH;

      ctx.clearRect(0, 0, width, height);
      ctx.fillStyle = "#080f1f";
      ctx.fillRect(0, 0, width, height);

      ctx.strokeStyle = "#1f2937";
      ctx.lineWidth = 1;
      for (let i = 0; i <= 4; i += 1) {
        const y = margin.top + (plotH * i) / 4;
        ctx.beginPath();
        ctx.moveTo(margin.left, y);
        ctx.lineTo(width - margin.right, y);
        ctx.stroke();
      }
      for (let i = 0; i <= 5; i += 1) {
        const x = margin.left + (plotW * i) / 5;
        ctx.beginPath();
        ctx.moveTo(x, margin.top);
        ctx.lineTo(x, height - margin.bottom);
        ctx.stroke();
      }

      ctx.strokeStyle = "#334155";
      ctx.beginPath();
      ctx.moveTo(margin.left, margin.top);
      ctx.lineTo(margin.left, height - margin.bottom);
      ctx.lineTo(width - margin.right, height - margin.bottom);
      ctx.stroke();

      for (const s of activeSeries) {
        ctx.strokeStyle = s.color;
        ctx.lineWidth = 2;
        ctx.beginPath();
        let moved = false;
        for (const p of s.points) {
          if (p.t < xMin || p.t > xMax) continue;
          const x = xToPx(p.t);
          const y = yToPx(p.v);
          if (!moved) {
            ctx.moveTo(x, y);
            moved = true;
          } else {
            ctx.lineTo(x, y);
          }
        }
        ctx.stroke();
      }

      ctx.fillStyle = "#9ca3af";
      ctx.font = "12px sans-serif";
      ctx.textAlign = "left";
      ctx.fillText(yLabel, margin.left, 12);
      ctx.textAlign = "right";
      ctx.fillText(xLabel, width - margin.right, height - 8);

      ctx.textAlign = "right";
      for (let i = 0; i <= 4; i += 1) {
        const y = margin.top + (plotH * i) / 4;
        const value = yMax - ((yMax - yMin) * i) / 4;
        ctx.fillText(value.toFixed(2), margin.left - 6, y + 4);
      }

      ctx.textAlign = "center";
      for (let i = 0; i <= 5; i += 1) {
        const x = margin.left + (plotW * i) / 5;
        const value = xMin + ((xMax - xMin) * i) / 5;
        ctx.fillText(value.toFixed(1), x, height - margin.bottom + 16);
      }

      return { xToPx, yToPx, xMin, xMax, margin, plotW, plotH };
    }

    function renderSection(direction, result) {
      const title = direction[0].toUpperCase() + direction.slice(1);
      const section = el("section", { class: "section" });
      section.append(el("h2", { text: title + " Test" }));

      const cards = el("div", { class: "grid" });
      const statusText = result.success ? "SUCCESS" : "FAILED";
      const statusClass = result.success ? "ok" : "fail";

      const metrics = [
        ["Status", statusText, statusClass],
        ["Endpoint", result.endpoint || "-"],
        ["Avg Speed", fmtMbps(result.speed_mbps)],
        ["Duration", fmtSeconds(result.duration_s)],
        ["Transferred", fmtSizeBytes(result.size_bytes)],
        ["Loss", fmtPct(result.latency_during && result.latency_during.loss_pct)],
        ["Latency Avg", fmtMs(result.latency_during && result.latency_during.avg_ms)],
        ["Latency Max", fmtMs(result.latency_during && result.latency_during.max_ms)],
      ];
      if (result.error) metrics.push(["Error", String(result.error)]);

      for (const item of metrics) {
        const label = item[0];
        const value = item[1];
        const cls = item[2] || "";
        const card = el("div", { class: "card" }, [
          el("div", { class: "label", text: label }),
          el("div", { class: "value " + cls, text: value }),
        ]);
        cards.append(card);
      }
      section.append(cards);

      const samples = Array.isArray(result.samples)
        ? result.samples
            .filter((s) => s && isNum(s.t))
            .map((s) => ({
              t: Number(s.t),
              speed: isNum(s.speed_mbps) ? Number(s.speed_mbps) : null,
              latency: isNum(s.latency_ms) ? Number(s.latency_ms) : null,
              latencyAvg: isNum(s.latency_avg_ms) ? Number(s.latency_avg_ms) : null,
              bytes: isNum(s.bytes) ? Number(s.bytes) : null,
            }))
            .sort((a, b) => a.t - b.t)
        : [];

      if (!samples.length) {
        section.append(el("div", { class: "empty", text: "No sample timeline found in this report." }));
        return section;
      }

      const maxT = samples[samples.length - 1].t;
      const minWindow = Math.max(0.1, maxT / 1000);

      const controls = el("div", { class: "controls" });
      const startWrap = el("div", { class: "control" });
      const endWrap = el("div", { class: "control" });
      const startValue = el("span", { text: "0.0s" });
      const endValue = el("span", { text: maxT.toFixed(1) + "s" });

      const startInput = el("input", {
        type: "range",
        min: "0",
        max: String(maxT),
        step: "any",
        value: "0",
      });
      const endInput = el("input", {
        type: "range",
        min: "0",
        max: String(maxT),
        step: "any",
        value: String(maxT),
      });

      startWrap.append(
        el("div", { class: "control-row" }, [el("span", { text: "Window Start" }), startValue]),
        startInput
      );
      endWrap.append(
        el("div", { class: "control-row" }, [el("span", { text: "Window End" }), endValue]),
        endInput
      );
      controls.append(startWrap, endWrap);
      section.append(controls);

      const legend = el("div", { class: "legend" }, [
        el("span", {}, [el("i", { class: "dot", style: "background:" + SPEED_COLOR }), document.createTextNode("Speed (Mbps)")]),
        el("span", {}, [el("i", { class: "dot", style: "background:" + LAT_COLOR }), document.createTextNode("Latency (ms)")]),
        el("span", {}, [el("i", { class: "dot", style: "background:" + LAT_AVG_COLOR }), document.createTextNode("Latency Avg (ms)")]),
      ]);
      section.append(legend);

      const speedWrap = el("div", { class: "chart-wrap" });
      const latencyWrap = el("div", { class: "chart-wrap" });
      const speedCanvas = el("canvas");
      const latencyCanvas = el("canvas");
      speedWrap.append(speedCanvas);
      latencyWrap.append(latencyCanvas);
      section.append(speedWrap, latencyWrap);

      const tooltip = el("div", { class: "tooltip" });
      section.append(tooltip);

      function getWindow(changedTarget) {
        let start = Number.parseFloat(startInput.value);
        let end = Number.parseFloat(endInput.value);

        if (!Number.isFinite(start)) start = 0;
        if (!Number.isFinite(end)) end = maxT;

        start = Math.max(0, Math.min(start, maxT));
        end = Math.max(0, Math.min(end, maxT));

        if (start > end - minWindow) {
          if (changedTarget === startInput) end = Math.min(maxT, start + minWindow);
          else start = Math.max(0, end - minWindow);
        }

        startInput.value = String(start);
        endInput.value = String(end);
        startValue.textContent = start.toFixed(1) + "s";
        endValue.textContent = end.toFixed(1) + "s";
        return { start, end };
      }

      function redraw(changedTarget = null) {
        const win = getWindow(changedTarget);

        drawChart({
          canvas: speedCanvas,
          xMin: win.start,
          xMax: win.end,
          xLabel: "Time (s)",
          yLabel: "Speed (Mbps)",
          series: [
            {
              enabled: true,
              color: SPEED_COLOR,
              points: samples.filter((s) => isNum(s.speed)).map((s) => ({ t: s.t, v: s.speed })),
            },
          ],
        });

        drawChart({
          canvas: latencyCanvas,
          xMin: win.start,
          xMax: win.end,
          xLabel: "Time (s)",
          yLabel: "Latency (ms)",
          series: [
            {
              enabled: true,
              color: LAT_COLOR,
              points: samples.filter((s) => isNum(s.latency)).map((s) => ({ t: s.t, v: s.latency })),
            },
            {
              enabled: true,
              color: LAT_AVG_COLOR,
              points: samples.filter((s) => isNum(s.latencyAvg)).map((s) => ({ t: s.t, v: s.latencyAvg })),
            },
          ],
        });
      }

      function bindHover(canvas, kind) {
        canvas.addEventListener("mousemove", (ev) => {
          const win = getWindow(null);
          const rect = canvas.getBoundingClientRect();
          const x = ev.clientX - rect.left;
          const t = win.start + (x / rect.width) * (win.end - win.start);
          const subset = samples.filter((s) => s.t >= win.start && s.t <= win.end);
          const hit = nearestByTime(subset, t);
          if (!hit) return;

          let htmlText = "t: " + hit.t.toFixed(2) + " s";
          htmlText += "<br>bytes: " + (isNum(hit.bytes) ? hit.bytes.toLocaleString() : "-");
          htmlText += "<br>speed: " + fmtMbps(hit.speed);
          htmlText += "<br>latency: " + fmtMs(hit.latency);
          htmlText += "<br>lat avg: " + fmtMs(hit.latencyAvg);
          tooltip.innerHTML = htmlText;
          tooltip.style.display = "block";
          tooltip.style.left = ev.offsetX + "px";
          tooltip.style.top = (ev.offsetY + (kind === "speed" ? 0 : 260)) + "px";
        });
        canvas.addEventListener("mouseleave", () => {
          tooltip.style.display = "none";
        });
      }

      startInput.addEventListener("input", () => redraw(startInput));
      endInput.addEventListener("input", () => redraw(endInput));
      window.addEventListener("resize", () => redraw(null));
      bindHover(speedCanvas, "speed");
      bindHover(latencyCanvas, "latency");

      if (typeof ResizeObserver !== "undefined") {
        const observer = new ResizeObserver(() => redraw(null));
        observer.observe(speedWrap);
        observer.observe(latencyWrap);
      }

      redraw(null);
      requestAnimationFrame(() => requestAnimationFrame(() => redraw(null)));

      return section;
    }

    function render() {
      const hero = el("section", { class: "hero" });
      hero.append(
        el("h1", { text: "Speedtest Report Viewer" }),
        el("div", { class: "meta", text: "Source: __SOURCE_NAME__" }),
        el("div", { class: "meta", text: "Timestamp: " + (report.timestamp || "-") })
      );
      app.append(hero);

      const keys = ["download", "upload"].filter((k) => report[k] && typeof report[k] === "object");
      if (!keys.length) {
        app.append(el("div", { class: "section empty", text: "No upload/download result blocks found in this JSON file." }));
        return;
      }
      for (const key of keys) {
        app.append(renderSection(key, report[key]));
      }
    }

    render();
  </script>
</body>
</html>
"""

    return template.replace("__REPORT_JSON__", report_json).replace(
        "__SOURCE_NAME__", source_name_escaped
    )


def main() -> int:
    args = parse_args()
    input_path = Path(args.report)
    if not input_path.exists():
        print(f"Error: input file not found: {input_path}")
        return 1

    try:
        report = load_report(input_path)
    except Exception as e:
        print(f"Error: failed to load report JSON: {e}")
        return 1

    out_path = output_path_for(input_path, args.output)
    try:
        html_content = render_html(report, input_path.name)
        out_path.write_text(html_content, encoding="utf-8")
    except Exception as e:
        print(f"Error: failed to write HTML: {e}")
        return 1

    print(f"Wrote interactive report: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
