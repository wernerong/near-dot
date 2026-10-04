"""Public-source guard, complementary to a full Gitleaks history scan.

Reports file/line/category only: never prints the suspected secret or URL.
"""
import pathlib
import re
import subprocess
import sys

root = pathlib.Path(__file__).resolve().parents[1]
paths = subprocess.check_output(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=root).decode().split("\0")
rules = {
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "provider token": re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|sk-[A-Za-z0-9_-]{30,})\b"),
    "credential URL": re.compile(r"https?://[^/\s]+:[^/\s]+@"),
    "personal chat URL": re.compile(r"https://chatgpt\.com/(?:c|dots|share)/[a-zA-Z0-9-]{20,}"),
    "machine path": re.compile(r"/Users/[^/\s]+/|C:\\Users\\[^\\\s]+\\"),
}
failures = []
for relative in paths:
    path = root / relative
    if not path.is_file() or path.suffix.lower() in {".png", ".ico", ".icns", ".gif", ".jpg"}:
        continue
    # Deliberately synthetic hostile-input fixtures are permitted only in validation tests.
    fixture = relative in {"src-tauri/src/destination.rs", "tests/validation.test.ts"}
    try:
        lines = path.read_text().splitlines()
    except (UnicodeError, OSError):
        continue
    for number, line in enumerate(lines, 1):
        for category, pattern in rules.items():
            if relative == "scripts/scan-public.py" and category == "machine path":
                continue  # The scanner's literal machine-path pattern is not a user path.
            if fixture and category == "credential URL" and "user:pass@" in line:
                continue
            if pattern.search(line):
                failures.append(f"{relative}:{number}: {category}")
if failures:
    print("Public-source scan blocked:\n" + "\n".join(failures))
    sys.exit(1)
print(f"Public-source guard passed ({len(paths)-1} paths). Run Gitleaks for full secret detection.")
