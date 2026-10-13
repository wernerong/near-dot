"""Lifecycle contracts for the external browser window; no ChatGPT requests."""
import copy
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from chat_app import AppError, ChatApp, browser_kind, browser_directory, browser_binary, validate_url
from privacy import write_new

URL = 'https://chatgpt.com/c/synthetic-app'
RECT = [100, 200, 430, 580]


class DesktopFixture:
    def __init__(self):
        self.items = []
        self.launches = []
        self.shown = []
        self.serial = 100

    def windows(self):
        return copy.deepcopy(self.items)

    def launch(self, url, rect):
        self.launches.append((url, rect))
        self.serial += 1
        self.items.append({'handle': self.serial, 'pid': 20, 'created': 30, 'marker': 0})

    def mark(self, window):
        window['marker'] = 123
        next(w for w in self.items if w['handle'] == window['handle'])['marker'] = 123

    def foreground(self):
        return self.items[-1]['handle'] if self.items else 0

    def show(self, window, rect, topmost):
        self.shown.append((window['handle'], rect, topmost))


class ChatAppTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name).resolve() / 'state'
        self.desktop = DesktopFixture()
        self.app = ChatApp(self.directory, self.desktop)

    def open(self, url=URL):
        self.app.open(url, RECT, True)

    def test_repeated_pet_clicks_focus_the_same_window(self):
        self.open()
        self.open()
        self.assertEqual(self.desktop.launches, [(URL, RECT)])
        self.assertEqual(self.desktop.shown, [(101, RECT, True), (101, RECT, True)])

    def test_default_browser_selection_does_not_silently_substitute_edge(self):
        self.assertEqual(browser_kind('ChromeHTML'), 'chrome')
        self.assertEqual(browser_kind('ChromeHTML.synthetic'), 'chrome')
        self.assertEqual(browser_kind('MSEdgeHTM'), 'edge')
        for value in ('FirefoxURL', 'unknown', None, 'chrome.exe --synthetic-flag'):
            with self.assertRaises(AppError):
                browser_kind(value)

    def test_chrome_profile_and_cache_do_not_replace_the_existing_edge_store(self):
        self.open()
        original = self.app.file.read_bytes()
        chrome = ChatApp(browser_directory(self.directory, 'chrome'), DesktopFixture())
        chrome.open(URL, RECT, True)
        self.assertEqual(self.app.file.read_bytes(), original)
        self.assertNotEqual(chrome.file, self.app.file)
        self.assertEqual(browser_directory(self.directory, 'edge'), self.directory)

    def test_browser_binary_selection_uses_only_fixed_install_paths(self):
        with patch.dict('chat_app.os.environ', {'ProgramFiles': '/synthetic/apps'}, clear=True), patch('chat_app.Path.is_file', return_value=True):
            self.assertEqual(browser_binary('chrome'), Path('/synthetic/apps/Google/Chrome/Application/chrome.exe'))
            self.assertEqual(browser_binary('edge'), Path('/synthetic/apps/Microsoft/Edge/Application/msedge.exe'))
            with self.assertRaises(AppError):
                browser_binary('synthetic-custom-command')

    def test_near_dot_restart_reuses_window_without_any_selection(self):
        self.open()
        self.app = ChatApp(self.directory, self.desktop)
        self.open()
        self.assertEqual(len(self.desktop.launches), 1)
        if os.name != 'nt':
            self.assertEqual(self.app.file.stat().st_mode & 0o777, 0o600)

    def test_closing_chat_or_restarting_windows_automatically_reopens_saved_dot(self):
        self.open()
        self.desktop.items.clear()
        self.app = ChatApp(self.directory, self.desktop)
        self.open()
        self.assertEqual(self.desktop.launches, [(URL, RECT), (URL, RECT)])
        self.assertEqual(self.desktop.shown[-1][0], 102)

    def test_reused_handle_or_process_never_redirects_to_stale_window(self):
        self.open()
        for key in ('marker', 'pid', 'created'):
            self.desktop.items[0][key] += 1
        self.open()
        self.assertEqual(len(self.desktop.launches), 2)
        self.assertEqual(self.desktop.shown[-1][0], 102)

    def test_changing_saved_dot_opens_the_new_address(self):
        self.open()
        other = 'https://chatgpt.com/c/synthetic-other'
        self.open(other)
        self.assertEqual(self.desktop.launches[-1], (other, RECT))
        self.assertEqual(self.desktop.shown[-1][0], 102)

    def test_unsafe_addresses_and_geometry_never_launch_any_process(self):
        for url in ['http://chatgpt.com/c/synthetic', 'https://chatgpt.com.evil.test/c/synthetic',
                    'https://user:pass@chatgpt.com/c/synthetic', 'https://chatgpt.com:444/c/synthetic',
                    'https://chatgpt.com/c/synthetic --remote-debugging-port=9222']:
            with self.assertRaises(AppError):
                self.open(url)
        for rect in [[0, 0, 1, 1], [0, 0, 400, '580'], [0, 0, 400, True], [0, 0, 400, 500, 1]]:
            with self.assertRaises(AppError):
                self.app.open(URL, rect, True)
        self.assertEqual(self.desktop.launches, [])

    def test_corrupt_and_future_cache_are_preserved(self):
        for raw in ['broken', json.dumps({'schema': 99})]:
            if self.app.file.exists():
                self.app.file.unlink()
            write_new(self.app.file, raw)
            with self.assertRaises(AppError):
                ChatApp(self.directory, self.desktop)
            self.assertEqual(self.app.file.read_text(), raw)

    def test_slow_browser_can_be_retried_without_binding(self):
        launch = self.desktop.launch
        self.desktop.launch = lambda url, rect: None
        with patch('chat_app.time.monotonic', side_effect=[0, 13]):
            with self.assertRaises(AppError):
                self.open()
        self.desktop.launch = launch
        self.open()
        self.assertEqual(len(self.desktop.shown), 1)

    @unittest.skipUnless(os.name == 'nt', 'Windows public APIs and browser-profile identification')
    def test_windows_profile_query_excludes_unrelated_edge_windows(self):
        from chat_app import Windows
        from privacy import private_directory
        desktop = Windows(private_directory(self.directory / 'synthetic-unused-profile'), 'edge')
        self.assertEqual(desktop.windows(), [])

    @unittest.skipUnless(os.name == 'nt', 'Windows profile discovery timeout diagnostics')
    def test_windows_profile_query_timeout_has_no_launch_arguments_or_profile_path(self):
        from chat_app import Windows
        from privacy import private_directory
        import subprocess
        desktop = Windows(private_directory(self.directory / 'synthetic-timeout-profile'), 'edge')
        failure = subprocess.TimeoutExpired(['synthetic-private-command'], 20)
        with patch('chat_app.subprocess.run', side_effect=failure):
            with self.assertRaises(AppError) as raised:
                desktop.roots()
        message = str(raised.exception)
        self.assertIn('Try again', message)
        self.assertNotIn(str(desktop.profile), message)
        self.assertNotIn('synthetic-private-command', message)

    @unittest.skipUnless(os.name == 'nt', 'Native synthetic Edge app window; no ChatGPT login or inference')
    def test_windows_creates_registers_and_restores_an_external_app_window(self):
        self.native_browser_window('edge')

    @unittest.skipUnless(os.name == 'nt', 'Native synthetic Chrome app window; no ChatGPT login or inference')
    def test_windows_chrome_creates_registers_and_restores_an_external_app_window(self):
        self.native_browser_window('chrome')

    def native_browser_window(self, kind):
        from chat_app import Windows
        from privacy import private_directory
        import ctypes as c
        from ctypes import wintypes as w
        desktop = Windows(private_directory(self.directory / ('synthetic-' + kind + '-window-profile')), kind)
        desktop.launch('data:text/html,<title>Synthetic Near Dot test</title><p>Local native window fixture</p>', RECT)
        try:
            deadline = time.monotonic() + 20
            windows = []
            retried_discovery = False
            while not windows and time.monotonic() < deadline:
                try:
                    windows = desktop.windows()
                except AppError as error:
                    # Exercise the published retry path for a cold Windows CIM
                    # lookup. Each attempt keeps its existing 20-second bound;
                    # a repeated timeout or any different failure still fails.
                    if retried_discovery or str(error) != 'Windows is still finding this companion’s browser profile. Try again.':
                        raise
                    retried_discovery = True
                    deadline = time.monotonic() + 20
                    continue
                if not windows:
                    time.sleep(0.2)
            self.assertTrue(windows, 'Synthetic browser app did not create an OS window.')
            target = windows[0]
            desktop.mark(target)
            self.assertTrue(target['marker'])
            desktop.user.ShowWindowAsync(target['handle'], 6)
            time.sleep(0.2)
            try:
                desktop.show(target, RECT, True)
            except AppError as error:
                # Hosted Windows workers may refuse foreground focus. Creation,
                # registration, placement and restoration still must succeed.
                self.assertIn('blocked keyboard focus', str(error))
            time.sleep(0.2)
            self.assertFalse(desktop.user.IsIconic(target['handle']))
            self.assertTrue(any(window['marker'] == target['marker'] for window in desktop.windows()))
        finally:
            desktop.kernel.TerminateProcess.argtypes = [w.HANDLE, w.UINT]
            desktop.kernel.TerminateProcess.restype = w.BOOL
            for pid in desktop.roots():
                process = desktop.kernel.OpenProcess(1, False, pid)
                if process:
                    desktop.kernel.TerminateProcess(process, 0)
                    desktop.kernel.CloseHandle(process)
            time.sleep(1)


if __name__ == '__main__':
    unittest.main()
