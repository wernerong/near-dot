"""Measure the running launcher's main process (no private data or screenshots).

Usage: python3 scripts/measure-macos.py PID visible|paused|hidden [SECONDS]
WebKit helper memory is not attributable with this simple process sampler.
"""
import json
import statistics
import subprocess
import sys
import time

pid = int(sys.argv[1])
mode = sys.argv[2]
seconds = int(sys.argv[3]) if len(sys.argv) > 3 else 30
if mode not in {"visible", "paused", "hidden"} or not 1 <= seconds <= 120:
    raise SystemExit("Invalid sampling parameters.")

def sample():
    raw = subprocess.check_output(["ps", "-p", str(pid), "-o", "time=,rss=,%cpu="], text=True).strip().split()
    clock = raw[0].split(":")
    elapsed = sum(float(part) * 60 ** power for power, part in enumerate(reversed(clock)))
    return elapsed, int(raw[1]), float(raw[2])

first = sample()
started = time.monotonic()
samples = [first]
for _ in range(seconds):
    time.sleep(1)
    samples.append(sample())
wall = time.monotonic() - started
cpu = max(0, (samples[-1][0] - first[0]) / wall * 100)
print(json.dumps({"platform": "macOS arm64", "mode": mode, "samples": len(samples), "wallSeconds": round(wall,2), "mainProcessCpuPercentOfOneCore": round(cpu,3), "mainProcessRssMiBMedian": round(statistics.median(s[1] for s in samples)/1024,2), "mainProcessRssMiBPeak": round(max(s[1] for s in samples)/1024,2), "scope": "Main process only; WebKit helpers excluded."}, indent=2))
