"""Generate redistributable dependency notices from pinned local package sources.

Only public package metadata/license text is emitted; never filesystem paths.
"""
import json
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parents[1]
metadata = json.loads(subprocess.check_output(['cargo','metadata','--manifest-path',str(root/'src-tauri/Cargo.toml'),'--format-version','1','--locked']))
sections = ['Near Dot — third-party dependency notices\n\nNear Dot code and original artwork use the MIT license.\nThis inventory includes build/test and unsupported-platform dependencies as well as shipped runtime dependencies. Each package retains its own license; its source is available from the public package registry below.\n']
count = 0

def record(name, version, license_name, registry, directory, extra=None):
    global count
    files = []
    for path in directory.iterdir():
        if path.is_file() and path.name.lower().startswith(('license','licence','copying','notice')):
            files.append(path)
    if extra and (directory/extra).is_file():
        files.append(directory/extra)
    texts = []
    for path in sorted(set(files)):
        try:
            text = path.read_text().strip()
        except UnicodeError:
            continue
        if text and text not in texts:
            texts.append(text)
    sections.append('\n'+'='*72+f'\n{name} {version}\nLicense: {license_name}\nSource: {registry}\n\n'+'\n\n'.join(texts)+'\n')
    count += 1

for package in sorted(metadata['packages'],key=lambda p:(p['name'],p['version'])):
    if not package['source']:
        continue
    record(package['name'],package['version'],package.get('license') or 'See package source',f"https://crates.io/crates/{package['name']}/{package['version']}",Path(package['manifest_path']).parent,package.get('license_file'))
lock = json.loads((root/'package-lock.json').read_text())
for relative, entry in sorted(lock['packages'].items()):
    if not relative:
        continue
    directory = root/relative
    manifest = directory/'package.json'
    if not manifest.exists():
        continue # Platform-specific build tooling not installed on this runner.
    package = json.loads(manifest.read_text())
    if package['version'] != entry['version']:
        raise SystemExit('Installed npm package does not match the lockfile.')
    record(package['name'],package['version'],package.get('license') or 'See package source',f"https://www.npmjs.com/package/{package['name']}/v/{package['version']}",directory)
(root/'THIRD-PARTY-NOTICES.txt').write_text('\n'.join(sections))
print(f'Generated public license notices for {count} pinned packages.')
