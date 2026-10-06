#!/usr/bin/env python3
"""Private, single-user MCP transport experiment. Not part of the desktop app.

Only an explicitly authorized tunnel may launch the stdio server. There is no
model, ChatGPT session access, public listener, or synthetic reply generator.
"""

import argparse
import base64
import datetime
import hashlib
import hmac
import http.client
import ipaddress
import json
import os
from pathlib import Path
import secrets
import socket
import sqlite3
import ssl
import sys
import time
from urllib.parse import urlsplit
from privacy import private_directory, private_path, write_new


PROTOCOL = "2026-07-28"
EVENT = "near_dot.message_created"
MAILBOX = "near-dot-proof"
MAX_TEXT = 1024
MAX_BODY = 262144
REPO = Path(__file__).resolve().parents[2]


def encode(value):
    return json.dumps(value, separators=(",", ":"), ensure_ascii=True).encode()


def utc(timestamp):
    return datetime.datetime.fromtimestamp(timestamp, datetime.timezone.utc).isoformat()


class RelayError(Exception):
    """Only constant, non-sensitive error codes may reach diagnostics."""


def validate_callback(url):
    try:
        p = urlsplit(url)
        host = p.hostname or ""
        if (p.scheme != "https" or p.username or p.password or p.fragment
                or p.port not in (None, 443) or not p.path
                or any(c.isspace() or ord(c) < 32 for c in url)
                or not any(host == d or host.endswith("." + d)
                           for d in ("openai.com", "chatgpt.com"))):
            raise ValueError()
        return p
    except (ValueError, TypeError):
        raise RelayError("callback_not_allowed") from None


def webhook_key(secret):
    try:
        if not isinstance(secret, str) or not secret.startswith("whsec_"):
            raise ValueError()
        key = base64.b64decode(secret[6:], validate=True)
        if not 24 <= len(key) <= 64:
            raise ValueError()
        return key
    except (ValueError, TypeError):
        raise RelayError("invalid_signing_secret") from None


class PinnedHTTPS(http.client.HTTPSConnection):
    def connect(self):
        addresses = socket.getaddrinfo(self.host, 443, type=socket.SOCK_STREAM)
        if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global
                                for a in addresses):
            raise RelayError("callback_address_not_public")
        # Connect to this already validated address; TLS still checks original host.
        family, socktype, proto, _, address = addresses[0]
        sock = socket.socket(family, socktype, proto)
        sock.settimeout(self.timeout)
        try:
            sock.connect(address)
            self.sock = self._context.wrap_socket(sock, server_hostname=self.host)
        except Exception:
            sock.close()
            raise


def post_webhook(url, secret, subscription_id, event_id, body):
    p = validate_callback(url)
    payload = encode(body)
    if len(payload) > MAX_BODY:
        raise RelayError("payload_too_large")
    stamp = str(int(time.time()))
    signed = event_id.encode() + b"." + stamp.encode() + b"." + payload
    signature = base64.b64encode(hmac.new(webhook_key(secret), signed, hashlib.sha256).digest()).decode()
    connection = PinnedHTTPS(p.hostname, timeout=10, context=ssl.create_default_context())
    try:
        connection.request("POST", p.path + ("?" + p.query if p.query else ""), body=payload,
                           headers={"Content-Type": "application/json", "webhook-id": event_id,
                                    "webhook-timestamp": stamp, "webhook-signature": "v1," + signature,
                                    "X-MCP-Subscription-Id": subscription_id})
        response = connection.getresponse()
        data = response.read(MAX_BODY + 1)
        if len(data) > MAX_BODY:
            raise RelayError("callback_response_too_large")
        # http.client does not follow redirects or use environment HTTP proxies.
        return response.status, data
    finally:
        connection.close()


class Relay:
    def __init__(self, state, post=post_webhook):
        state = Path(state).expanduser().absolute()
        if state == REPO or REPO in state.parents:
            raise RelayError("state_must_be_outside_repository")
        os.umask(0o077)
        try:
            private_directory(state)
            private_path(state / 'proof.sqlite3')
            consent = private_path(state / 'consent.json')
            self.persistent = False
            if consent.exists():
                value = json.loads(consent.read_text())
                if value != {'schema': 1, 'persistent': True}:
                    raise ValueError('Unknown consent schema.')
                self.persistent = True
        except ValueError:
            raise RelayError('state_directory_not_private') from None
        self.state = state
        dbpath = state / "proof.sqlite3"
        if not dbpath.exists():
            try:
                write_new(dbpath, '')
            except FileExistsError:
                # Desktop and tunnel helpers can initialize concurrently.
                private_path(dbpath)
        self.db = sqlite3.connect(dbpath, timeout=10)
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
          CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY, body TEXT NOT NULL, created REAL NOT NULL,
            event_id TEXT NOT NULL, delivered INTEGER NOT NULL DEFAULT 0, reply TEXT);
          CREATE TABLE IF NOT EXISTS subscription (
            id TEXT PRIMARY KEY, url TEXT NOT NULL, secret TEXT NOT NULL,
            previous_secret TEXT, rotate_until REAL NOT NULL DEFAULT 0,
            expires REAL NOT NULL);
          CREATE TABLE IF NOT EXISTS proof_window (
            singleton INTEGER PRIMARY KEY CHECK(singleton=1), deadline REAL NOT NULL);
        """)
        self.post = post

    def close(self):
        self.db.close()

    def queue(self, text):
        if not isinstance(text, str) or not text.strip() or len(text) > MAX_TEXT:
            raise RelayError("invalid_message")
        message_id = secrets.token_hex(16)
        with self.db:
            self.db.execute("INSERT INTO messages(id,body,created,event_id) VALUES(?,?,?,?)",
                            (message_id, text, time.time(), "evt_" + secrets.token_hex(16)))
        return message_id

    def extend_local_window(self, hours):
        # Local CLI only. No MCP tool or renderer operation can extend access.
        if type(hours) is not int or not 1 <= hours <= 24:
            raise RelayError("invalid_extension")
        deadline = time.time() + hours * 3600
        with self.db:
            self.db.execute("INSERT OR REPLACE INTO proof_window VALUES(1,?)", (deadline,))
            self.db.execute("UPDATE subscription SET expires=?", (deadline,))
        return {"local_window_extended_hours": hours, "runtime_key_unchanged": True}

    def status(self):
        rows = self.db.execute("SELECT delivered,reply FROM messages").fetchall()
        window = self.db.execute("SELECT deadline FROM proof_window WHERE singleton=1").fetchone()
        return {"active_subscription": self.db.execute("SELECT 1 FROM subscription WHERE expires>?",
                                                      (time.time(),)).fetchone() is not None,
                "proof_seconds_remaining": max(0, int(window[0] - time.time())) if window and not self.persistent else None,
                "messages": len(rows), "acknowledged_events": sum(r[0] == 1 for r in rows),
                "terminal_delivery_failures": sum(r[0] == 2 for r in rows),
                "tool_replies": sum(r[1] is not None for r in rows),
                "origin_attested_by_transport": False}

    def subscribe(self, params):
        window = self.db.execute("SELECT deadline FROM proof_window WHERE singleton=1").fetchone()
        if not self.persistent and window and time.time() >= window[0]:
            raise RelayError("proof_window_expired")
        delivery = self.check_event_args(params)
        secret = delivery.get("secret")
        webhook_key(secret)
        url = delivery["url"]
        sid = "sub_" + hashlib.sha256(encode([MAILBOX, url, EVENT])).hexdigest()
        ttl = params.get("ttlMs", 86400000)
        if ttl is None:
            ttl = 86400000  # Always capped by the owner-controlled fixed deadline.
        if type(ttl) not in (int, float) or not 1000 <= ttl <= 86400000:
            raise RelayError("invalid_subscription_lifetime")
        challenge = secrets.token_urlsafe(32)
        status, data = self.post(url, secret, sid, "verify_" + secrets.token_hex(16),
                                 {"type": "verification", "challenge": challenge})
        try:
            echoed = json.loads(data).get("challenge", "")
            verified = isinstance(echoed, str) and hmac.compare_digest(challenge, echoed)
        except (ValueError, AttributeError):
            verified = False
        if not 200 <= status < 300 or not verified:
            raise RelayError("callback_challenge_failed")
        existing = self.db.execute("SELECT * FROM subscription").fetchone()
        if existing and existing["id"] != sid:
            raise RelayError("single_subscription_only")
        previous = existing["secret"] if existing and existing["secret"] != secret else None
        with self.db:
            # This is an absolute cap for this entire private proof, not a rolling
            # TTL. Automatic refreshes and unsubscribe/re-subscribe cannot extend it.
            expires = time.time() + ttl / 1000
            if not self.persistent:
                self.db.execute("INSERT OR IGNORE INTO proof_window VALUES(1,?)", (time.time() + 3600,))
                deadline = self.db.execute("SELECT deadline FROM proof_window WHERE singleton=1").fetchone()[0]
                if time.time() >= deadline:
                    raise RelayError("proof_window_expired")
                expires = min(expires, deadline)
            self.db.execute("INSERT OR REPLACE INTO subscription VALUES(?,?,?,?,?,?)",
                            (sid, url, secret, previous, time.time() + 300 if previous else 0, expires))
        return {"id": sid, "refreshBefore": utc(expires), "cursor": None, "truncated": False}

    def check_event_args(self, params):
        delivery = params.get("delivery", {})
        if (params.get("name") != EVENT or params.get("arguments") != {"mailbox": MAILBOX}
                or delivery.get("mode") != "webhook"):
            raise RelayError("invalid_subscription")
        validate_callback(delivery.get("url"))
        return delivery

    def flush(self, message_id=None):
        subscription = self.db.execute("SELECT * FROM subscription WHERE expires>?", (time.time(),)).fetchone()
        if not subscription:
            raise RelayError("no_active_subscription")
        # Secret rotation is deliberately paused until a fresh delivery can use only
        # the new secret. The old key remains private for the bounded overlap period.
        if subscription["rotate_until"] > time.time():
            raise RelayError("secret_rotation_delivery_paused")
        if message_id is None:
            pending = self.db.execute("SELECT * FROM messages WHERE delivered=0 ORDER BY created").fetchall()
        else:
            pending = self.db.execute("SELECT * FROM messages WHERE id=? AND delivered=0", (message_id,)).fetchall()
        for message in pending:
            event = {"eventId": message["event_id"], "name": EVENT,
                     "timestamp": utc(message["created"]),
                     "data": {"mailbox": MAILBOX, "message_id": message["id"]}, "cursor": None}
            status, _ = self.post(subscription["url"], subscription["secret"], subscription["id"],
                                  message["event_id"], event)
            if status == 410:
                with self.db:
                    self.db.execute("DELETE FROM subscription")
                raise RelayError("subscription_gone")
            if status == 413:
                with self.db:
                    self.db.execute("UPDATE messages SET delivered=2 WHERE id=?", (message["id"],))
                raise RelayError("event_rejected_too_large")
            if not 200 <= status < 300:
                raise RelayError("delivery_failed_no_automatic_retry")
            with self.db:
                self.db.execute("UPDATE messages SET delivered=1 WHERE id=?", (message["id"],))
        return self.status()

    def tool(self, name, arguments):
        if name not in ("read_test_message", "reply_to_test_message"):
            raise RelayError("unknown_tool")
        if name == "read_test_message" and arguments == {"message_id": "connection-check"}:
            grant = self.db.execute("SELECT deadline FROM proof_window WHERE singleton=1").fetchone()
            return {"kind": "connection_check", "relay_reachable": True,
                    "connection_deadline": utc(grant[0]) if grant and not self.persistent else None,
                    "remaining_seconds": self.status()["proof_seconds_remaining"],
                    "owner_controlled_deadline": not self.persistent, "is_message": False}
        window = self.db.execute("SELECT deadline FROM proof_window WHERE singleton=1").fetchone()
        if not self.persistent and window and time.time() >= window[0]:
            raise RelayError("proof_window_expired")
        expected = {"message_id"} if name == "read_test_message" else {"message_id", "reply"}
        if set(arguments) != expected:
            raise RelayError("invalid_tool_arguments")
        message = self.db.execute("SELECT * FROM messages WHERE id=?", (arguments["message_id"],)).fetchone()
        if not message:
            raise RelayError("unknown_message")
        if name == "read_test_message":
            return {"message_id": message["id"], "text": message["body"]}
        reply = arguments["reply"]
        if not isinstance(reply, str) or not reply.strip() or len(reply) > MAX_TEXT:
            raise RelayError("invalid_reply")
        # Atomic compare-and-set makes retries idempotent, even across processes.
        with self.db:
            self.db.execute("UPDATE messages SET reply=? WHERE id=? AND reply IS NULL", (reply, message["id"]))
            saved = self.db.execute("SELECT reply FROM messages WHERE id=?", (message["id"],)).fetchone()[0]
            if saved != reply:
                raise RelayError("conflicting_duplicate_reply")
        return {"accepted": True, "message_id": message["id"]}

    def dispatch(self, method, params):
        if method == "server/discover":
            return {"resultType": "complete", "supportedVersions": [PROTOCOL],
                    "capabilities": {"tools": {}, "events": {}}}
        if method == "initialize":
            return {"protocolVersion": "2025-11-25", "capabilities": {"tools": {}},
                    "serverInfo": {"name": "near-dot-transport-proof", "version": "0.0.1"}}
        if method == "ping":
            return {}
        if method == "tools/list":
            tools = []
            for name in ("read_test_message", "reply_to_test_message"):
                read = name == "read_test_message"
                properties = {"message_id": {"type": "string"}}
                if not read:
                    properties["reply"] = {"type": "string", "minLength": 1, "maxLength": MAX_TEXT}
                tools.append({"name": name,
                              "description": ("Read one locally queued Near Dot test message by its event ID. For a harmless access check, use message_id connection-check; this returns relay readiness, not a message."
                                              if read else "Return your response to one Near Dot test message to the user's local CLI. Only include the non-sensitive test answer; never unrelated chat history, credentials or private account data."),
                              "inputSchema": {"type": "object", "properties": properties,
                                              "required": list(properties), "additionalProperties": False},
                              "annotations": {"readOnlyHint": read, "destructiveHint": False,
                                              "idempotentHint": True, "openWorldHint": False}})
            return {"tools": tools}
        if method == "tools/call":
            result = self.tool(params.get("name"), params.get("arguments", {}))
            return {"content": [{"type": "text", "text": encode(result).decode()}], "isError": False}
        if method == "events/list":
            return {"events": [{"name": EVENT, "description": "A local Near Dot message is ready. Subscribe to receive message IDs, then read and reply using the tools. Subscriptions require renewal before refreshBefore.",
                                "delivery": ["webhook"],
                                "inputSchema": {"type": "object", "properties": {"mailbox": {"type": "string", "const": MAILBOX}},
                                                "required": ["mailbox"], "additionalProperties": False},
                                "payloadSchema": {"type": "object", "properties": {"mailbox": {"type": "string"}, "message_id": {"type": "string"}},
                                                  "required": ["mailbox", "message_id"], "additionalProperties": False}}]}
        if method == "events/subscribe":
            return self.subscribe(params)
        if method == "events/unsubscribe":
            delivery = self.check_event_args(params)
            with self.db:
                self.db.execute("DELETE FROM subscription WHERE url=?", (delivery["url"],))
            return {}
        raise RelayError("method_not_supported")

    def stdio(self):
        while True:
            line = sys.stdin.buffer.readline(MAX_BODY + 1)
            if not line:
                return
            if len(line) > MAX_BODY:
                raise RelayError("request_too_large")
            request_id = None
            try:
                request = json.loads(line)
                if not isinstance(request, dict) or request.get("jsonrpc") != "2.0":
                    raise RelayError("invalid_request")
                request_id = request.get("id")
                if request_id is None:
                    continue
                if type(request_id) not in (str, int):
                    request_id = None
                    raise RelayError("invalid_request_id")
                result = self.dispatch(request.get("method"), request.get("params", {}))
                response = {"jsonrpc": "2.0", "id": request_id, "result": result}
            except Exception as error:
                # No exception text: requests can contain credentials or message text.
                response = {"jsonrpc": "2.0", "id": request_id,
                            "error": {"code": -32602, "message": "Request rejected; inspect local status."}}
                if isinstance(error, RelayError) and str(error).startswith("callback_"):
                    response["error"] = {"code": -32015, "message": "Callback verification failed.",
                                         "data": {"reason": "challenge_failed"}}
            sys.stdout.buffer.write(encode(response) + b"\n")
            sys.stdout.buffer.flush()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", required=True, help="Private directory outside this repository; holds only this proof's mailbox and subscription.")
    parser.add_argument("command", choices=("serve", "status", "queue", "deliver", "read", "revoke", "extend"))
    parser.add_argument("--message-id", help="ID returned by queue; never a ChatGPT conversation ID.")
    parser.add_argument("--hours", type=int, default=24, help="Explicit local owner extension, 1–24 hours; never renews the runtime key.")
    args = parser.parse_args()
    relay = None
    try:
        relay = Relay(args.state)
        if args.command == "serve":
            relay.stdio()
            return
        if args.command == "extend":
            result = relay.extend_local_window(args.hours)
        elif args.command == "queue":
            result = {"message_id": relay.queue(sys.stdin.read(MAX_TEXT + 1)), "delivered": False}
        elif args.command == "deliver":
            result = relay.flush()
        elif args.command == "read":
            row = relay.db.execute("SELECT reply FROM messages WHERE id=?", (args.message_id,)).fetchone()
            if not row:
                raise RelayError("unknown_message")
            result = {"reply": row[0], "source": "MCP tool call; independently verify existing-dot origin"}
        elif args.command == "revoke":
            with relay.db:
                relay.db.execute("DELETE FROM subscription")
            result = {"local_subscription_revoked": True}
        else:
            result = relay.status()
        print(encode(result).decode())
    except RelayError as error:
        print(encode({"error": str(error)}).decode(), file=sys.stderr)
        return 1
    except Exception:
        print('{"error":"operation_failed_details_redacted"}', file=sys.stderr)
        return 1
    finally:
        if relay:
            relay.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
