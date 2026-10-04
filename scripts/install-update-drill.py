"""Disposable runner-only install/update/recovery/uninstall check; no user data.

Uses real prior installers and the maintained Tauri updater over local HTTPS.
The release key only verifies packages; this script never receives private keys.
"""
import functools
import hashlib
import http.server
import json
import os
from pathlib import Path
import plistlib
import shutil
import ssl
import subprocess
import sys
import tempfile
import threading
import time

if os.environ.get('GITHUB_ACTIONS') != 'true':
    raise SystemExit('Run only on a disposable GitHub-hosted release runner.')
platform, target = sys.argv[1:]
version = json.loads(Path('package.json').read_text())['version']
windows = sys.platform == 'win32'
artifacts = Path('release-artifacts').resolve()
prior = Path('previous').resolve()
package = artifacts / f'NearDot-{version}-{platform}{".exe" if windows else ".app.tar.gz"}'
signature = Path(str(package)+'.sig').read_text().strip()
public_key = os.environ['NEAR_DOT_UPDATER_PUBLIC_KEY']

def run(args, **kwargs):
    return subprocess.run([str(x) for x in args], check=True, **kwargs)

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *_):
        pass

with tempfile.TemporaryDirectory(prefix='neardot-release-drill-') as temp:
    root = Path(temp)
    installed = root/'installed'
    installed.mkdir()
    preferences = (Path(os.environ['APPDATA']) if windows else Path.home()/'Library/Application Support')/'org.neardot.companion'/'preferences.json'
    if preferences.exists():
        raise SystemExit('Runner already has preferences; refusing to overwrite.')
    preferences.parent.mkdir(parents=True, exist_ok=True)
    seed = {'schema':1,'destination':'https://chatgpt.com/c/synthetic-drill','verified':True,'setupCompleted':True,'shortcut':'','size':180,'opacity':0.8,'alwaysOnTop':True,'paused':True,'replyPreview':False,'startup':False,'autoCheck':False,'unattendedNextLaunch':False,'channel':'stable','skippedVersion':'','position':None,'cohort':42}
    preferences.write_text(json.dumps(seed))
    before_preferences = digest(preferences)
    mount = root/'mounted'
    def install_mac(dmg):
        run(['hdiutil','attach','-nobrowse','-readonly','-mountpoint',mount,dmg], stdout=subprocess.DEVNULL)
        try:
            if (installed/'Near Dot.app').exists():
                shutil.rmtree(installed/'Near Dot.app')
            run(['ditto',mount/'Near Dot.app',installed/'Near Dot.app'])
        finally:
            run(['hdiutil','detach',mount], stdout=subprocess.DEVNULL)
    try:
        if windows:
            old = list(prior.rglob('*-setup.exe'))
            assert len(old)==1, 'Expected one baseline Windows installer'
            run([old[0],'/S',f'/D={installed}'])
            executable = installed/'near-dot.exe'
        else:
            old = list(prior.rglob('*.dmg'))
            assert len(old)==1, 'Expected one baseline Mac installer'
            install_mac(old[0])
            executable = installed/'Near Dot.app/Contents/MacOS/near-dot'
        assert executable.is_file(), 'Baseline executable missing'
        before_executable = digest(executable)
        # The TLS private key is ephemeral test material, unrelated to updater signing.
        run([sys.executable, 'scripts/create-test-tls.py', root])
        (root/'public-key.txt').write_text(public_key)
        feed = {'version':version,'platforms':{platform:{'url':'','signature':signature}}}
        server = http.server.ThreadingHTTPServer(('127.0.0.1',0), functools.partial(QuietHandler,directory=root))
        tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        tls.load_cert_chain(root/'server.pem',root/'tls.key')
        server.socket=tls.wrap_socket(server.socket,server_side=True)
        endpoint=f'https://127.0.0.1:{server.server_port}'
        feed['platforms'][platform]['url']=endpoint+'/package'
        (root/'feed.json').write_text(json.dumps(feed))
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        harness = Path('src-tauri/target')/target/'release/examples'/('update-drill.exe' if windows else 'update-drill')
        command=[str(harness.resolve()),endpoint+'/feed.json',str(root/'ca.pem'),str(executable),str(root/'public-key.txt')]
        original=package.read_bytes()
        # Both a complete altered package and an interrupted/truncated download must be rejected.
        for invalid in [bytes([original[0]^1])+original[1:],original[:64]]:
            (root/'package').write_bytes(invalid)
            result=subprocess.run(command,timeout=120,capture_output=True,text=True)
            assert result.returncode == 1 and 'Minisign(InvalidSignature)' in result.stderr, f'Expected cryptographic rejection, not a runner failure: exit {result.returncode}; {result.stderr}'
            print('Confirmed Tauri rejection: Minisign(InvalidSignature)')
            assert digest(executable)==before_executable, 'Invalid update replaced the app'
            assert digest(preferences)==before_preferences, 'Invalid update changed preferences'
        (root/'package').write_bytes(original)
        run(command,timeout=150)
        deadline=time.monotonic()+120
        while time.monotonic()<deadline and digest(executable)==before_executable:
            time.sleep(0.5)
        assert digest(executable)!=before_executable, 'Updater did not replace the baseline executable'
        assert digest(preferences)==before_preferences, 'Updater changed preferences'
        if windows:
            expected=Path('src-tauri/target')/target/'release/near-dot.exe'
            assert digest(executable)==digest(expected), 'Installed executable differs from candidate'
            # Recovery after rejected download: reinstall the newer trusted candidate.
            run([package,'/S',f'/D={installed}'])
            assert digest(executable)==digest(expected)
            uninstall=installed/'uninstall.exe'
            assert uninstall.exists(), 'Uninstaller missing'
            run([uninstall,'/S',f'_?={installed}'])
            deadline=time.monotonic()+30
            while executable.exists() and time.monotonic()<deadline:time.sleep(0.5)
            assert not executable.exists(), 'Uninstall left executable behind'
        else:
            bundle=installed/'Near Dot.app'
            info=plistlib.loads((bundle/'Contents/Info.plist').read_bytes())
            assert info['CFBundleShortVersionString']==version
            run(['codesign','--verify','--deep','--strict',bundle])
            install_mac(artifacts/f'NearDot-{version}-{platform}.dmg')
            run(['codesign','--verify','--deep','--strict',bundle])
            shutil.rmtree(bundle)
            assert not bundle.exists()
        assert digest(preferences)==before_preferences, 'Recovery or uninstall deleted preferences'
        server.shutdown()
        print(f'PASS {platform}: baseline install, tampered/truncated rejection, Tauri upgrade to {version}, preferences preserved, manual recovery reinstall and executable removal.')
    finally:
        preferences.unlink(missing_ok=True)
