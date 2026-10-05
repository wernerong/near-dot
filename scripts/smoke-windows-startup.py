"""Check that a Windows candidate reaches UI IPC and survives repeated launches.

Runs the supplied executable with its normal local preferences. Each launch is
stopped after the check; no destination, artwork or credentials are inspected.
"""
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time


def check_startup(executable, attempts=3, timeout=20):
    if sys.platform != "win32":
        raise SystemExit("This smoke check requires Windows.")
    executable = Path(executable).resolve(strict=True)
    for attempt in range(1, attempts + 1):
        with tempfile.TemporaryFile() as output:
            process = subprocess.Popen(
                [str(executable), "--measure-startup", "--no-unattended"],
                stdout=output,
                stderr=output,
                cwd=executable.parent,
                env={**os.environ, "RUST_BACKTRACE": "0"},
            )
            try:
                deadline = time.monotonic() + timeout
                ready_at = None
                while time.monotonic() < deadline:
                    if process.poll() is not None:
                        raise RuntimeError(
                            f"Launch {attempt} exits before verification: {process.returncode}."
                        )
                    output.seek(0)
                    log = output.read().decode("utf-8", errors="replace")
                    if "panicked at" in log:
                        raise RuntimeError(f"Launch {attempt} reports a panic.")
                    match = re.search(r"NEAR_DOT_STARTUP_MS=(\d+)", log)
                    if match:
                        if ready_at is None:
                            ready_at = time.monotonic()
                        if time.monotonic() - ready_at >= 2:
                            print(f"Launch {attempt}: UI IPC ready in {match[1]} ms; app remains running.")
                            break
                    time.sleep(0.1)
                else:
                    raise RuntimeError(f"Launch {attempt} never reaches UI IPC.")
            finally:
                if process.poll() is None:
                    process.terminate()
                process.wait(timeout=10)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python scripts/smoke-windows-startup.py PATH_TO_EXE")
    check_startup(sys.argv[1])
