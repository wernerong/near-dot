"""Build-time pinned portable runtime. No downloads or package installs at app startup."""
import hashlib
import json
from pathlib import Path
import sys
import urllib.request
import zipfile
import io

ROOT = Path(__file__).resolve().parents[1]
FILES = [
    ('https://www.python.org/ftp/python/3.13.12/python-3.13.12-embed-amd64.zip',
     '76f238f606250c87c6beac75dccd35ee99070a13490555936abb6cb64ecce3d0', 'python'),
    ('https://github.com/openai/tunnel-client/releases/download/v0.0.15/tunnel-client-v0.0.15-windows-amd64.zip',
     '3b53133a1e24d43f63088d843860cb1701a4c3ed6390de2e19f69089e43bddc1', 'tunnel'),
]


def main():
    destination = ROOT / 'src-tauri/relay-runtime'
    destination.mkdir(exist_ok=True)
    manifest = {}
    for url, digest, folder in FILES:
        cached = ROOT / ('local-evidence/tools/' + ('python-embed.zip' if folder == 'python' else 'tunnel-windows.zip'))
        data = cached.read_bytes() if cached.exists() else urllib.request.urlopen(url, timeout=90).read(80000000)
        if hashlib.sha256(data).hexdigest() != digest:
            raise ValueError('Portable runtime checksum mismatch.')
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            for member in archive.infolist():
                path = Path(member.filename)
                if member.is_dir():
                    continue
                if path.is_absolute() or '..' in path.parts:
                    raise ValueError('Unsafe archive member.')
                if folder == 'tunnel' and path.name.lower() == 'cloudflared.exe':
                    continue  # The stdio route does not use Cloudflare.
                relative = Path(folder) / path
                target = destination / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                contents = archive.read(member)
                target.write_bytes(contents)
                manifest[relative.as_posix()] = hashlib.sha256(contents).hexdigest()
    for name in ('desktop.py', 'relay.py', 'connect.py', 'privacy.py', 'setup.py', 'processes.py'):
        contents = (ROOT / 'experiments/dot-relay' / name).read_bytes()
        relative = 'relay/' + name
        target = destination / relative
        target.parent.mkdir(exist_ok=True)
        target.write_bytes(contents)
        manifest[relative] = hashlib.sha256(contents).hexdigest()
    (destination / 'runtime-manifest.json').write_text(json.dumps(manifest, sort_keys=True), encoding='utf-8')
    config = {'bundle': {'resources': {'relay-runtime/': 'relay-runtime/'}}}
    (ROOT / 'relay-runtime-config.json').write_text(json.dumps(config), encoding='utf-8')
    print('Pinned relay runtime prepared; manifest covers every packaged runtime file.')


if __name__ == '__main__':
    main()
