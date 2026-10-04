"""Run a checksum-pinned official Gitleaks on the public source inventory.

No data is uploaded. After an initial commit exists, also scan full Git history.
"""
import hashlib
import io
import pathlib
import platform
import shutil
import subprocess
import tarfile
import tempfile
import urllib.request
import zipfile

root = pathlib.Path(__file__).resolve().parents[1]
targets = {
    ("Darwin", "arm64"): ("darwin_arm64.tar.gz", "b40ab0ae55c505963e365f271a8d3846efbc170aa17f2607f13df610a9aeb6a5"),
    ("Darwin", "x86_64"): ("darwin_x64.tar.gz", "dfe101a4db2255fc85120ac7f3d25e4342c3c20cf749f2c20a18081af1952709"),
    ("Windows", "AMD64"): ("windows_x64.zip", "d29144deff3a68aa93ced33dddf84b7fdc26070add4aa0f4513094c8332afc4e"),
}
name, digest = targets[(platform.system(), platform.machine())]
url = "https://github.com/gitleaks/gitleaks/releases/download/v8.30.1/gitleaks_8.30.1_" + name
data = urllib.request.urlopen(url, timeout=60).read()
if hashlib.sha256(data).hexdigest() != digest:
    raise SystemExit("Gitleaks download checksum mismatch.")
with tempfile.TemporaryDirectory(prefix="near-dot-secret-scan-") as temporary:
    temp = pathlib.Path(temporary)
    executable = "gitleaks.exe" if platform.system() == "Windows" else "gitleaks"
    if name.endswith(".zip"):
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            binary = archive.read(executable)
    else:
        with tarfile.open(fileobj=io.BytesIO(data)) as archive:
            binary = archive.extractfile(executable).read()
    tool = temp / executable
    tool.write_bytes(binary)
    tool.chmod(0o755)
    source = temp / "source"
    source.mkdir()
    inventory = subprocess.check_output(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=root).decode().split("\0")
    for relative in inventory:
        path = root / relative
        if not relative or not path.is_file():
            continue
        target = source / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
    result = subprocess.run([str(tool), "dir", str(source), "--redact", "--no-banner"], cwd=root)
    if result.returncode:
        raise SystemExit(result.returncode)
    head = subprocess.run(["git", "rev-parse", "--verify", "HEAD"], cwd=root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if head.returncode == 0:
        result = subprocess.run([str(tool), "git", str(root), "--redact", "--no-banner"], cwd=root)
        raise SystemExit(result.returncode)
