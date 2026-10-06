"""Per-user setup, Windows ACL and process lifetime regression coverage."""
import base64
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
from privacy import private_directory, private_path, write_new
from setup import configure
import setup
from relay import Relay, EVENT, MAILBOX, encode
from desktop import snapshot, dispatch


class SetupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.state = Path(self.temp.name).resolve() / 'synthetic-fixture'
        self.key = 'sk-' + 'synthetic-fixture-' * 3

    def tearDown(self):
        self.temp.cleanup()

    def test_setup_is_private_and_does_not_replace_existing_connection(self):
        configure(self.state, 'tunnel_synthetic_fixture', self.key)
        for name in ('runtime.key', 'connection.json', 'consent.json'):
            private_path(self.state / name)
        self.assertEqual((self.state / 'runtime.key').read_text(), self.key)
        with self.assertRaises(ValueError):
            configure(self.state, 'tunnel_synthetic_other', self.key)
        self.assertEqual(json.loads((self.state / 'connection.json').read_text())['tunnel_id'], 'tunnel_synthetic_fixture')

    def test_invalid_inputs_leave_no_connection_files(self):
        for tunnel, key in [('invalid', self.key), ('tunnel_synthetic fixture', self.key), ('tunnel_synthetic', 'invalid')]:
            with self.assertRaises(ValueError):
                configure(self.state, tunnel, key)
        self.assertFalse(self.state.exists())

    def test_forget_removes_credentials_and_subscription_but_preserves_messages(self):
        configure(self.state, 'tunnel_synthetic_fixture', self.key)
        mailbox = Relay(self.state)
        message = mailbox.queue('Synthetic retained message')
        mailbox.close()
        with patch('setup.state_directory', return_value=self.state), patch('setup.sys.argv', ['setup.py', 'forget']), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(setup.main(), 0)
        self.assertFalse((self.state / 'runtime.key').exists())
        self.assertFalse((self.state / 'connection.json').exists())
        self.assertFalse((self.state / 'consent.json').exists())
        mailbox = Relay(self.state)
        self.assertEqual(mailbox.tool('read_test_message', {'message_id': message})['text'], 'Synthetic retained message')
        self.assertFalse(mailbox.status()['active_subscription'])
        mailbox.close()

    def test_automatic_check_cannot_resume_paused_connection(self):
        configure(self.state, 'tunnel_synthetic_fixture', self.key)
        write_new(self.state / 'paused', 'paused')
        with patch('setup.state_directory', return_value=self.state), patch('setup.sys.argv', ['setup.py', 'automatic-check']), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(setup.main(), 1)
        self.assertTrue((self.state / 'paused').exists())

    def test_explicit_persistent_consent_allows_subscription_renewal_after_restart(self):
        configure(self.state, 'tunnel_synthetic_fixture', self.key)
        params = {'name': EVENT, 'arguments': {'mailbox': MAILBOX}, 'ttlMs': 86400000,
                  'delivery': {'mode': 'webhook', 'url': 'https://chatgpt.com/synthetic-fixture-callback',
                               'secret': 'whsec_' + base64.b64encode(bytes(range(32))).decode()}}
        receiver = lambda *args: (200, encode({'challenge': args[-1]['challenge']}))
        mailbox = Relay(self.state, receiver)
        mailbox.subscribe(params)
        self.assertIsNone(mailbox.status()['proof_seconds_remaining'])
        mailbox.close()
        with patch('relay.time.time', return_value=time.time() + 48 * 3600):
            mailbox = Relay(self.state, receiver)
            mailbox.subscribe(params)
            self.assertTrue(mailbox.status()['active_subscription'])
        mailbox.close()

    def test_pause_blocks_send_and_retry_even_with_live_health_and_subscription(self):
        private_directory(self.state)
        mailbox = Relay(self.state)
        message = mailbox.queue('Synthetic pending fixture')
        write_new(self.state / 'paused', 'paused')
        with patch('desktop.local_health', return_value={'live': True, 'startup_ready': True, 'poll_failures': 0}):
            self.assertEqual(snapshot(mailbox)['state'], 'paused')
            self.assertFalse(snapshot(mailbox)['connected'])
            with patch.object(mailbox, 'flush', side_effect=AssertionError('Must not deliver')):
                with self.assertRaises(Exception):
                    dispatch(mailbox, {'operation': 'retry', 'messageId': message})
        mailbox.close()

    @unittest.skipUnless(os.name == 'nt', 'Windows ACL fixture')
    def test_broad_windows_acl_and_reparse_points_fail_closed(self):
        private_directory(self.state)
        target = self.state / 'synthetic-file'
        write_new(target, 'synthetic')
        result = subprocess.run(['icacls', str(target), '/grant', '*S-1-1-0:(R)'], capture_output=True)
        self.assertEqual(result.returncode, 0)
        with self.assertRaises(ValueError):
            private_path(target)
        junction = Path(self.temp.name).resolve() / 'synthetic-junction'
        # This test-only Windows junction does not need symlink privileges.
        result = subprocess.run(['cmd', '/c', 'mklink', '/J', str(junction), str(self.state)], capture_output=True)
        self.assertEqual(result.returncode, 0)
        try:
            with self.assertRaises(ValueError):
                private_path(junction / 'synthetic-file')
        finally:
            junction.rmdir()

    @unittest.skipUnless(os.name == 'nt', 'Windows process ownership fixture')
    def test_parent_exit_terminates_owned_descendant(self):
        helper_dir = str(Path(__file__).parent.resolve())
        code = "import sys,subprocess; sys.path.insert(0,sys.argv[1]); from processes import own_process_tree; job=own_process_tree(); p=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)']); print(p.pid,flush=True); sys.stdin.readline()"
        parent = subprocess.Popen([sys.executable, '-I', '-u', '-c', code, helper_dir], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            line = parent.stdout.readline()
            self.assertTrue(line, 'Owned helper must start before the descendant check')
            pid = int(line)
            parent.kill()
            parent.wait(timeout=5)
            import ctypes as c
            from ctypes import wintypes as w
            kernel = c.WinDLL('kernel32')
            kernel.OpenProcess.argtypes = [w.DWORD, w.BOOL, w.DWORD]
            kernel.OpenProcess.restype = w.HANDLE
            kernel.WaitForSingleObject.argtypes = [w.HANDLE, w.DWORD]
            kernel.CloseHandle.argtypes = [w.HANDLE]
            handle = kernel.OpenProcess(0x100000, False, pid)
            if handle:
                try:
                    self.assertEqual(kernel.WaitForSingleObject(handle, 5000), 0)
                finally:
                    kernel.CloseHandle(handle)
        finally:
            if parent.poll() is None:
                parent.kill()
                parent.wait()
            parent.stdin.close()
            parent.stdout.close()
            parent.stderr.close()

    @unittest.skipUnless(os.name == 'nt', 'Windows portable runtime fixture')
    def test_packaged_python_runs_isolated_helper_with_correct_arguments(self):
        runtime = Path(__file__).resolve().parents[2] / 'src-tauri/relay-runtime/python/python.exe'
        self.assertTrue(runtime.is_file(), 'Prepare the pinned runtime before Windows tests')
        env = dict(os.environ, LOCALAPPDATA=self.temp.name, PYTHONPATH='synthetic-invalid-injection')
        boot = "import sys,runpy; from pathlib import Path; p=Path(sys.argv.pop(1)); sys.path.insert(0,str(p.parent)); runpy.run_path(str(p),run_name='__main__')"
        result = subprocess.run([str(runtime), '-I', '-u', '-c', boot, str(Path(__file__).parent / 'connect.py'), 'status'], env=env, capture_output=True)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stdout), {'tunnel_configured': False, 'key_file_present': False})
        self.assertEqual(result.stderr, b'')
