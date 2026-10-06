"""Synthetic credential-helper tests; never read real credentials."""

import contextlib
import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import warnings

import connect


class ConnectTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.state = Path(self.temp.name)
        if os.name == "nt":
            from privacy import protect_new_directory
            protect_new_directory(self.state)
        self.fake = "sk-" + "synthetic-fixture-" * 3

    def tearDown(self):
        self.temp.cleanup()

    def test_key_saved_privately_without_echo_and_never_overwritten(self):
        output = io.StringIO()
        with patch.object(connect, "STATE", self.state), patch("connect.sys.stdin.isatty", return_value=True), \
                patch("connect.getpass.getpass", return_value=self.fake), contextlib.redirect_stdout(output):
            connect.store_key()
            with self.assertRaises(ValueError):
                connect.store_key()
        self.assertNotIn(self.fake, output.getvalue())
        self.assertEqual((self.state / "runtime.key").read_text(), self.fake)
        connect.private_path(self.state / "runtime.key")
        if os.name != "nt":
            self.assertEqual((self.state / "runtime.key").stat().st_mode & 0o777, 0o600)

    def test_echo_fallback_cannot_collect_key(self):
        def unsafe_prompt(*args):
            warnings.warn("Synthetic echo fallback", connect.getpass.GetPassWarning)
            raise AssertionError("Input must never be read after the warning")

        with patch.object(connect, "STATE", self.state), patch("connect.sys.stdin.isatty", return_value=True), \
                patch("connect.getpass.getpass", unsafe_prompt), contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(connect.getpass.GetPassWarning):
                connect.store_key()
        self.assertFalse((self.state / "runtime.key").exists())

    @unittest.skipIf(os.name == "nt", "POSIX mode fixture; Windows ACLs have separate tests")
    def test_symlinks_and_public_permissions_rejected(self):
        target = self.state / "target"
        target.touch(mode=0o600)
        link = self.state / "runtime.key"
        link.symlink_to(target)
        with self.assertRaises(ValueError):
            connect.private_path(link)
        os.chmod(target, 0o644)
        with self.assertRaises(ValueError):
            connect.private_path(target)

    def test_health_evidence_omits_identity_payload_and_urls(self):
        source = {"live": True, "ready": True, "tunnel_id": "synthetic-private-id",
                  "url": "https://synthetic.example/secret", "message": "synthetic-private-body",
                  "components": {"queue": {"details": {"enqueued": 3}},
                                 "dispatcher": {"details": {"completed": 3, "failures": 0}}}}
        summary = connect.health_summary(source)
        self.assertEqual(summary["requests_received"], 3)
        self.assertEqual(summary["requests_completed"], 3)
        self.assertFalse(any("synthetic-private" in str(v) for v in summary.values()))
        self.assertNotIn("url", summary)


if __name__ == "__main__":
    unittest.main()
