"""Synthetic protocol/unit tests. Passing these does NOT prove a dot exchange."""

import base64
import hashlib
import hmac
import json
from pathlib import Path
import tempfile
import subprocess
import sys
import unittest
from unittest.mock import patch

import relay


class RelayTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.calls = []

        def receiver(url, secret, sid, event_id, body):
            self.calls.append(body)
            return 200, relay.encode({"challenge": body.get("challenge")})

        self.r = relay.Relay(self.temp.name, receiver)
        self.params = {"name": relay.EVENT, "arguments": {"mailbox": relay.MAILBOX},
                       "delivery": {"mode": "webhook", "url": "https://chatgpt.com/synthetic-fixture-callback",
                                    "secret": "whsec_" + base64.b64encode(bytes(range(32))).decode()}}

    def tearDown(self):
        self.r.close()
        self.temp.cleanup()

    def test_discovery_has_events_and_two_narrow_tools(self):
        self.assertEqual(self.r.dispatch("server/discover", {})["supportedVersions"], [relay.PROTOCOL])
        self.assertEqual([t["name"] for t in self.r.dispatch("tools/list", {})["tools"]],
                         ["read_test_message", "reply_to_test_message"])
        self.assertEqual(len(self.r.dispatch("events/list", {})["events"]), 1)

    def test_only_explicit_local_extension_changes_deadline(self):
        self.r.subscribe(self.params)
        first = self.r.db.execute("SELECT deadline FROM proof_window").fetchone()[0]
        with self.assertRaises(relay.RelayError):
            self.r.dispatch("extend", {"hours": 24})
        with self.assertRaises(relay.RelayError):
            self.r.extend_local_window(25)
        self.assertEqual(first, self.r.db.execute("SELECT deadline FROM proof_window").fetchone()[0])
        result = self.r.extend_local_window(24)
        self.assertTrue(result['runtime_key_unchanged'])
        check = self.r.tool('read_test_message', {'message_id':'connection-check'})
        self.assertTrue(check['owner_controlled_deadline'])
        self.assertIsNotNone(check['connection_deadline'])
        self.assertGreater(check['remaining_seconds'], 23 * 3600)
        self.assertGreater(self.r.db.execute("SELECT deadline FROM proof_window").fetchone()[0], first + 22 * 3600)

    def test_connection_check_creates_no_message_or_reply(self):
        health = self.r.tool("read_test_message", {"message_id": "connection-check"})
        self.assertTrue(health["relay_reachable"])
        self.assertFalse(health["is_message"])
        self.assertEqual(self.r.status()["messages"], 0)
        self.assertEqual(self.r.status()["tool_replies"], 0)
        with self.assertRaises(relay.RelayError):
            self.r.tool("reply_to_test_message", {"message_id": "connection-check", "reply": "Synthetic"})

    def test_real_stdio_process_discovery_and_redacted_errors(self):
        requests = [
            {"jsonrpc": "2.0", "id": 1, "method": "server/discover"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
             "params": {"name": "synthetic-sensitive-error-text", "arguments": {}}},
        ]
        process = subprocess.run([sys.executable, str(Path(relay.__file__)), "--state", self.temp.name, "serve"],
                                 input=b"\n".join(relay.encode(r) for r in requests) + b"\n",
                                 capture_output=True, check=True)
        results = [json.loads(line) for line in process.stdout.splitlines()]
        self.assertEqual(results[0]["result"]["supportedVersions"], [relay.PROTOCOL])
        self.assertIn("error", results[1])
        self.assertNotIn(b"synthetic-sensitive-error-text", process.stdout + process.stderr)

    def test_webhook_ack_is_never_a_dot_reply(self):
        self.r.subscribe(self.params)
        mid = self.r.queue("Synthetic transport fixture; no assistant is involved.")
        self.r.flush()
        self.assertEqual(self.r.status()["acknowledged_events"], 1)
        self.assertEqual(self.r.status()["tool_replies"], 0)
        self.assertFalse(self.r.status()["origin_attested_by_transport"])
        self.assertEqual(self.calls[-1]["data"], {"mailbox": relay.MAILBOX, "message_id": mid})
        self.assertNotIn("text", self.calls[-1]["data"])

    def test_targeted_delivery_does_not_send_other_queued_messages(self):
        self.r.subscribe(self.params)
        other = self.r.queue("Synthetic message that should stay queued")
        chosen = self.r.queue("Synthetic selected message")
        self.r.flush(chosen)
        delivered_ids = [c["data"]["message_id"] for c in self.calls if "data" in c]
        self.assertEqual(delivered_ids, [chosen])
        self.assertEqual(self.r.db.execute("SELECT delivered FROM messages WHERE id=?", (other,)).fetchone()[0], 0)

    def test_challenge_failure_cannot_activate_subscription(self):
        self.r.post = lambda *args: (200, b'{"challenge":"wrong"}')
        with self.assertRaises(relay.RelayError):
            self.r.subscribe(self.params)
        self.assertFalse(self.r.status()["active_subscription"])

    def test_restart_and_duplicate_tool_calls(self):
        mid = self.r.queue("Explicit synthetic fixture")
        self.r.tool("reply_to_test_message", {"message_id": mid, "reply": "Synthetic fixture reply"})
        self.r.close()
        self.r = relay.Relay(self.temp.name)
        self.r.tool("reply_to_test_message", {"message_id": mid, "reply": "Synthetic fixture reply"})
        with self.assertRaises(relay.RelayError):
            self.r.tool("reply_to_test_message", {"message_id": mid, "reply": "Changed reply"})
        self.assertEqual(self.r.status()["tool_replies"], 1)

    def test_offline_queue_and_retry_preserve_event_id(self):
        self.r.subscribe(self.params)
        self.r.queue("Synthetic offline test")
        seen = []

        def failing(*args):
            seen.append(args[3])
            return 503, b""

        self.r.post = failing
        for _ in range(2):
            with self.assertRaises(relay.RelayError):
                self.r.flush()
        self.assertEqual(seen[0], seen[1])
        self.assertEqual(self.r.status()["acknowledged_events"], 0)

    def test_expiry_and_unsubscribe_stop_delivery(self):
        self.r.subscribe(self.params)
        self.r.queue("Synthetic expiry fixture")
        self.r.db.execute("UPDATE subscription SET expires=0")
        self.r.db.commit()
        with self.assertRaises(relay.RelayError):
            self.r.flush()
        self.r.dispatch("events/unsubscribe", self.params)
        self.r.dispatch("events/unsubscribe", self.params)
        self.assertFalse(self.r.status()["active_subscription"])

    def test_refresh_and_restart_cannot_extend_absolute_hour(self):
        with patch("relay.time.time", return_value=1000):
            first = self.r.subscribe(self.params)
            mid = self.r.queue("Synthetic fixed deadline fixture")
        self.r.close()
        self.r = relay.Relay(self.temp.name, lambda *args: (200, relay.encode({"challenge": args[-1]["challenge"]})))
        with patch("relay.time.time", return_value=2000):
            refreshed = self.r.subscribe(self.params)
            self.assertEqual(first["refreshBefore"], refreshed["refreshBefore"])
        with patch("relay.time.time", return_value=4601):
            for action in (lambda: self.r.subscribe(self.params), lambda: self.r.flush(),
                           lambda: self.r.tool("reply_to_test_message", {"message_id": mid, "reply": "Late synthetic answer"})):
                with self.assertRaises(relay.RelayError):
                    action()
            self.r.dispatch("events/unsubscribe", self.params)
            with self.assertRaises(relay.RelayError):
                self.r.subscribe(self.params)

    def test_oversized_event_rejection_is_not_retried(self):
        self.r.subscribe(self.params)
        self.r.queue("Synthetic terminal delivery failure")
        attempts = []

        def rejected(*args):
            attempts.append(1)
            return 413, b""

        self.r.post = rejected
        with self.assertRaises(relay.RelayError):
            self.r.flush()
        self.r.flush()
        self.assertEqual(len(attempts), 1)
        self.assertEqual(self.r.status()["terminal_delivery_failures"], 1)
        self.assertEqual(self.r.status()["acknowledged_events"], 0)

    def test_non_public_or_untrusted_callbacks_rejected(self):
        for url in ("http://chatgpt.com/synthetic", "https://user:pass@chatgpt.com/synthetic",
                    "https://127.0.0.1/synthetic", "https://chatgpt.com.attacker.example/synthetic",
                    "https://chatgpt.com:8443/synthetic", "https://chatgpt.com/synthetic#secret"):
            with self.assertRaises(relay.RelayError):
                relay.validate_callback(url)
        with patch("relay.socket.getaddrinfo", return_value=[(2, 1, 6, "", ("127.0.0.1", 443))]):
            with self.assertRaises(relay.RelayError):
                relay.PinnedHTTPS("chatgpt.com").connect()

    def test_signature_covers_exact_bytes_and_no_redirect_follow(self):
        captured = {}

        class Connection:
            def __init__(self, *args, **kwargs):
                pass

            def request(self, method, path, body, headers):
                captured.update(body=body, headers=headers)

            def getresponse(self):
                class Response:
                    status = 302

                    def read(self, limit):
                        return b""
                return Response()

            def close(self):
                pass

        with patch("relay.PinnedHTTPS", Connection):
            status, _ = relay.post_webhook(self.params["delivery"]["url"], self.params["delivery"]["secret"],
                                           "synthetic-subscription", "synthetic-event", {"text": "Synthetic ✓"})
        self.assertEqual(status, 302)
        headers = captured["headers"]
        payload = ("synthetic-event." + headers["webhook-timestamp"] + ".").encode() + captured["body"]
        expected = "v1," + base64.b64encode(hmac.new(bytes(range(32)), payload, hashlib.sha256).digest()).decode()
        self.assertEqual(headers["webhook-signature"], expected)
        altered = payload + b" "
        self.assertNotEqual(expected, "v1," + base64.b64encode(hmac.new(bytes(range(32)), altered, hashlib.sha256).digest()).decode())

    def test_unknown_message_tool_and_oversized_text_rejected(self):
        for name, args in (("run_shell", {}), ("read_test_message", {"message_id": "synthetic-missing"})):
            with self.assertRaises(relay.RelayError):
                self.r.tool(name, args)
        with self.assertRaises(relay.RelayError):
            self.r.queue("x" * (relay.MAX_TEXT + 1))

    def test_private_state_and_no_repository_database(self):
        self.assertEqual((Path(self.temp.name) / "proof.sqlite3").stat().st_mode & 0o077, 0)
        with self.assertRaises(relay.RelayError):
            relay.Relay(relay.REPO / "synthetic-test-state")


if __name__ == "__main__":
    unittest.main()
