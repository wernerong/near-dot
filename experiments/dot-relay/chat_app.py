"""An external default-browser app window for the saved ChatGPT dot address.

Normal ChatGPT web UI owns messages, history, authentication and plan limits.
No inference requests, scraping, token reads, debugging port or embedded webview.
"""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import time
from urllib.parse import urlsplit
import uuid

from privacy import private_directory, private_path, write_new


class AppError(Exception):
    pass


def browser_kind(prog_id):
    if isinstance(prog_id, str):
        value = prog_id.lower()
        if value == 'chromehtml' or value.startswith('chromehtml.'):
            return 'chrome'
        if value == 'msedgehtm':
            return 'edge'
    raise AppError('The dedicated chat window supports Chrome and Edge. Set either as your default browser, or choose Default browser in Near Dot Settings.')


def default_browser():
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r'Software\Microsoft\Windows\Shell\Associations\UrlAssociations\https\UserChoice') as key:
            prog_id = winreg.QueryValueEx(key, 'ProgId')[0]
    except OSError:
        raise AppError('Windows could not identify your default HTTPS browser. Choose Chrome or Edge in Windows default apps, then try again.') from None
    return browser_kind(prog_id)


def browser_binary(kind):
    relatives = {'chrome': 'Google/Chrome/Application/chrome.exe',
                 'edge': 'Microsoft/Edge/Application/msedge.exe'}
    if kind not in relatives:
        raise AppError('Unsupported chat browser.')
    candidates = [Path(os.environ[name]) / relatives[kind]
                  for name in ('ProgramFiles', 'ProgramFiles(x86)', 'LOCALAPPDATA') if name in os.environ]
    binary = next((path for path in candidates if path.is_file()), None)
    if not binary:
        label = 'Google Chrome' if kind == 'chrome' else 'Microsoft Edge'
        raise AppError(label + ' is your selected browser but could not be found. Install or repair it, then try again.')
    return binary


def browser_directory(directory, kind):
    # Keep the existing Edge profile/cache intact. Browser cookie encryption and
    # profile formats are not interchangeable; Chrome gets its own private store.
    if kind not in ('chrome', 'edge'):
        raise AppError('Unsupported chat browser.')
    return directory / 'chrome' if kind == 'chrome' else directory


def validate_url(value):
    if not isinstance(value, str) or len(value) > 2048 or any(c.isspace() or ord(c) < 32 for c in value) or '\\' in value:
        raise AppError('Use your tested HTTPS ChatGPT dot address.')
    try:
        parsed = urlsplit(value)
        if parsed.scheme != 'https' or parsed.netloc != 'chatgpt.com' or not parsed.path.startswith('/'):
            raise ValueError()
    except ValueError:
        raise AppError('Only HTTPS addresses on chatgpt.com are allowed.') from None
    return value


def identity(window):
    return hashlib.sha256(':'.join(str(window[k]) for k in ('handle', 'pid', 'created', 'marker')).encode()).hexdigest()


if os.name == 'nt':
    import ctypes as c
    from ctypes import wintypes as w

    class Windows:
        def __init__(self, profile, kind=None):
            self.profile = profile
            self.kind = kind or default_browser()
            self.binary = browser_binary(self.kind)
            self.process_name = self.binary.name.lower()
            self.user = c.WinDLL('user32', use_last_error=True)
            self.kernel = c.WinDLL('kernel32', use_last_error=True)
            self.callback = c.WINFUNCTYPE(w.BOOL, w.HWND, w.LPARAM)
            signatures = {
                'EnumWindows': ([self.callback, w.LPARAM], w.BOOL),
                'IsWindowVisible': ([w.HWND], w.BOOL),
                'GetWindowThreadProcessId': ([w.HWND, c.POINTER(w.DWORD)], w.DWORD),
                'GetWindowRect': ([w.HWND, c.POINTER(w.RECT)], w.BOOL),
                'IsIconic': ([w.HWND], w.BOOL),
                'ShowWindowAsync': ([w.HWND, c.c_int], w.BOOL),
                'SetWindowPos': ([w.HWND, w.HWND, c.c_int, c.c_int, c.c_int, c.c_int, w.UINT], w.BOOL),
                'SetForegroundWindow': ([w.HWND], w.BOOL),
                'GetForegroundWindow': ([], w.HWND),
                'GetPropW': ([w.HWND, w.LPCWSTR], w.HANDLE),
                'SetPropW': ([w.HWND, w.LPCWSTR, w.HANDLE], w.BOOL),
            }
            for name, (arguments, result) in signatures.items():
                function = getattr(self.user, name)
                function.argtypes, function.restype = arguments, result
            self.kernel.OpenProcess.argtypes = [w.DWORD, w.BOOL, w.DWORD]
            self.kernel.OpenProcess.restype = w.HANDLE
            self.kernel.CloseHandle.argtypes = [w.HANDLE]
            self.kernel.CloseHandle.restype = w.BOOL
            self.kernel.QueryFullProcessImageNameW.argtypes = [w.HANDLE, w.DWORD, w.LPWSTR, c.POINTER(w.DWORD)]
            self.kernel.QueryFullProcessImageNameW.restype = w.BOOL
            self.kernel.GetProcessTimes.argtypes = [w.HANDLE] + [c.POINTER(w.FILETIME)] * 4
            self.kernel.GetProcessTimes.restype = w.BOOL
            self.user.SetProcessDpiAwarenessContext.argtypes = [c.c_void_p]
            self.user.SetProcessDpiAwarenessContext.restype = w.BOOL
            self.user.SetProcessDpiAwarenessContext(c.c_void_p(-4))

        def roots(self):
            # CIM reads process launch arguments only to identify our browser
            # profile. It returns PIDs, never command lines or other private data.
            script = r'''$ErrorActionPreference='Stop'
            [Console]::InputEncoding=New-Object System.Text.UTF8Encoding($false)
            [Console]::OutputEncoding=New-Object System.Text.UTF8Encoding($false)
            $request=[Console]::In.ReadToEnd()|ConvertFrom-Json
            $profile=$request.profile
            $name=$request.name
            if($name -notin @('chrome.exe','msedge.exe')){throw 'Unsupported browser'}
            $escaped=[Regex]::Escape($profile)
            $pattern='(?i)(?:^|\s)(?:"--user-data-dir='+$escaped+'"|--user-data-dir="'+$escaped+'"|--user-data-dir='+$escaped+')(?:\s|$)'
            $ids=@(Get-CimInstance Win32_Process -Filter "Name='$name'" | Where-Object {
                $_.CommandLine -and $_.CommandLine -match $pattern -and
                $_.CommandLine -notmatch '(?:^|\s)"?--type='
            } | ForEach-Object { [int]$_.ProcessId })
            ConvertTo-Json -Compress -InputObject $ids'''
            powershell = Path(os.environ['WINDIR']) / 'System32/WindowsPowerShell/v1.0/powershell.exe'
            try:
                # A cold CIM provider can take longer than eight seconds to
                # initialize. Keep discovery bounded within the native caller's
                # 45-second deadline; subsequent queries are normally warm.
                result = subprocess.run([str(powershell), '-NoProfile', '-NonInteractive', '-EncodedCommand',
                                         base64.b64encode(script.encode('utf-16le')).decode()],
                                        input=json.dumps({'profile': str(self.profile), 'name': self.process_name}).encode('utf-8'), stdout=subprocess.PIPE,
                                        stderr=subprocess.DEVNULL, timeout=20, creationflags=0x08000000)
            except subprocess.TimeoutExpired:
                raise AppError('Windows is still finding this companion’s browser profile. Try again.') from None
            try:
                values = json.loads(result.stdout.decode('utf-8-sig'))
                if result.returncode or not isinstance(values, list) or not all(type(v) is int for v in values):
                    raise ValueError()
                return set(values)
            except (UnicodeError, ValueError):
                raise AppError('Windows could not find this companion’s browser profile. Try again.') from None

        def windows(self):
            roots = self.roots()
            result = []

            def visit(handle, _):
                if not self.user.IsWindowVisible(handle):
                    return True
                pid = w.DWORD()
                self.user.GetWindowThreadProcessId(handle, c.byref(pid))
                if pid.value not in roots:
                    return True
                process = self.kernel.OpenProcess(0x1000, False, pid.value)
                if not process:
                    return True
                try:
                    path = c.create_unicode_buffer(32768)
                    size = w.DWORD(len(path))
                    if not self.kernel.QueryFullProcessImageNameW(process, 0, path, c.byref(size)) or Path(path.value).name.lower() != self.process_name:
                        return True
                    created, exited, kernel, user = (w.FILETIME() for _ in range(4))
                    if not self.kernel.GetProcessTimes(process, *[c.byref(x) for x in (created, exited, kernel, user)]):
                        return True
                    result.append({'handle': int(handle), 'pid': pid.value,
                                   'created': (created.dwHighDateTime << 32) | created.dwLowDateTime,
                                   'marker': self.user.GetPropW(handle, 'NearDot.ChatApp') or 0})
                finally:
                    self.kernel.CloseHandle(process)
                return True

            callback = self.callback(visit)
            if not self.user.EnumWindows(callback, 0):
                raise AppError('The ChatGPT app window could not be found. Try again.')
            return result

        def launch(self, url, rect):
            # A real, separate browser window. No remote debugging or injected
            # extensions; the browser handles login and encrypted cookies.
            subprocess.Popen([str(self.binary), '--user-data-dir=' + str(self.profile),
                              '--app=' + url, '--no-first-run', '--no-default-browser-check',
                              '--window-size=' + str(rect[2]) + ',' + str(rect[3]),
                              '--window-position=' + str(rect[0]) + ',' + str(rect[1])],
                             stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL, creationflags=0x08000000)

        def mark(self, window):
            marker = secrets.randbits(63) | 1
            if not self.user.SetPropW(window['handle'], 'NearDot.ChatApp', w.HANDLE(marker)):
                raise AppError('The chat opened, but its window could not be registered. Run Near Dot as your normal user.')
            window['marker'] = marker

        def foreground(self):
            return self.user.GetForegroundWindow()

        def show(self, window, rect, topmost):
            handle = window['handle']
            if self.user.IsIconic(handle):
                self.user.ShowWindowAsync(handle, 9)
            self.user.ShowWindowAsync(handle, 5)
            if not self.user.SetWindowPos(handle, w.HWND(-1 if topmost else -2), *rect, 0x4000 | 0x0040):
                raise AppError('ChatGPT opened, but its window could not move beside the pet.')
            if not self.user.SetForegroundWindow(handle):
                raise AppError('ChatGPT is visible beside the pet. Windows blocked keyboard focus; click the chat to type.')


class ChatApp:
    def __init__(self, directory, desktop):
        self.directory = private_directory(directory)
        self.file = private_path(self.directory / 'app.json')
        self.desktop = desktop
        self.saved = None
        if self.file.exists():
            try:
                if self.file.stat().st_size > 16384:
                    raise ValueError()
                value = json.loads(self.file.read_text(encoding='utf-8'))
                if value['schema'] != 1:
                    raise ValueError()
                validate_url(value['url'])
                if not all(type(value['window'][k]) is int for k in ('handle', 'pid', 'created', 'marker')):
                    raise ValueError()
                self.saved = value
            except (OSError, ValueError, KeyError, TypeError, AppError):
                raise AppError('Chat window settings are invalid or need a newer release. The file was preserved.') from None

    def save(self, value):
        staging = self.directory / ('.app-' + uuid.uuid4().hex + '.json')
        try:
            write_new(staging, json.dumps(value, ensure_ascii=False))
            os.replace(staging, self.file)
            private_path(self.file)
            self.saved = value
        finally:
            if staging.exists():
                staging.unlink()

    def open(self, url, rect, topmost):
        url = validate_url(url)
        if not isinstance(rect, list) or len(rect) != 4 or not all(type(n) is int and -100000 <= n <= 100000 for n in rect):
            raise AppError('Invalid chat position.')
        if not 200 <= rect[2] <= 4000 or not 120 <= rect[3] <= 4000 or type(topmost) is not bool:
            raise AppError('Invalid chat size.')
        windows = self.desktop.windows()
        target = next((window for window in windows if self.saved and self.saved['url'] == url
                       and identity(window) == identity(self.saved['window']) and window['marker']), None)
        if target is None:
            previous = {(w['handle'], w['pid'], w['created']) for w in windows}
            self.desktop.launch(url, rect)
            deadline = time.monotonic() + 12
            while time.monotonic() < deadline:
                current = self.desktop.windows()
                target = next((w for w in current if (w['handle'], w['pid'], w['created']) not in previous), None)
                if target:
                    break
                # The browser may reuse its own existing app window when reopening.
                focused = self.desktop.foreground()
                target = next((w for w in current if w['handle'] == focused), None)
                if target:
                    break
                time.sleep(0.2)
            if target is None:
                raise AppError('ChatGPT was asked to open. If your browser is still starting, click the pet again in a moment.')
            self.desktop.mark(target)
            self.save({'schema': 1, 'url': url, 'window': target})
        self.desktop.show(target, rect, topmost)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--state', type=Path, required=True)
    args = parser.parse_args()
    os.umask(0o077)
    try:
        if os.name != 'nt':
            raise AppError('The dedicated chat app window is currently available on Windows.')
        data = sys.stdin.buffer.read(16385)
        if len(data) > 16384:
            raise AppError('Chat app request is too large.')
        value = json.loads(data)
        if not isinstance(value, dict) or value.get('operation') != 'open':
            raise AppError('Unknown chat app action.')
        kind = default_browser()
        directory = private_directory(browser_directory(args.state, kind))
        profile = private_directory(directory / 'browser')
        ChatApp(directory, Windows(profile, kind)).open(value.get('url'), value.get('rect'), value.get('topmost'))
        result = {'ok': True}
    except AppError as error:
        result = {'error': str(error)}
    except (OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired):
        result = {'error': 'The chat app window could not open. Its profile and settings were preserved.'}
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
