#!/usr/bin/env python3
"""Send a non-sensitive test message to the connected dot and wait for its reply.

No model or synthetic reply runs here. Connection/subscription setup is required.
"""

import argparse
import json
from pathlib import Path
import sys
import time

from relay import MAX_TEXT, Relay, RelayError


def wait_for_reply(mailbox, message_id, timeout):
    deadline = time.monotonic() + timeout
    while True:
        row = mailbox.db.execute("SELECT reply FROM messages WHERE id=?", (message_id,)).fetchone()
        if row is None:
            raise RelayError("unknown_message")
        if row[0] is not None:
            return row[0]
        if time.monotonic() >= deadline:
            return None
        time.sleep(1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", default=str(Path.home() / "Library/Application Support/Near Dot/transport-proof"))
    parser.add_argument("--resume", help="Resume waiting for a previously queued mailbox message ID.")
    parser.add_argument("--timeout", type=int, default=180, help="Maximum reply wait in seconds (1–300).")
    args = parser.parse_args()
    mailbox = None
    try:
        if not 1 <= args.timeout <= 300:
            raise RelayError("invalid_timeout")
        mailbox = Relay(args.state)
        if args.resume:
            mid = args.resume
            if not mailbox.db.execute("SELECT 1 FROM messages WHERE id=?", (mid,)).fetchone():
                raise RelayError("unknown_message")
        else:
            if not mailbox.status()["active_subscription"]:
                raise RelayError("no_active_subscription")
            text = input("Non-sensitive test message: ") if sys.stdin.isatty() else sys.stdin.read(MAX_TEXT + 1)
            mid = mailbox.queue(text)
        saved = mailbox.db.execute("SELECT delivered,reply FROM messages WHERE id=?", (mid,)).fetchone()
        if saved[1] is not None:
            print(saved[1], flush=True)
            return 0
        if saved[0] == 2:
            raise RelayError("terminal_delivery_failure")
        # Only this message is delivered. Other queued drafts remain untouched.
        print(json.dumps({"message_id": mid, "state": "queued"}), file=sys.stderr, flush=True)
        if saved[0] == 0:
            mailbox.flush(mid)
        print("Waiting for the connected dot's actual reply…", file=sys.stderr, flush=True)
        reply = wait_for_reply(mailbox, mid, args.timeout)
        if reply is None:
            print(json.dumps({"message_id": mid, "state": "pending", "resume_supported": True}), file=sys.stderr)
            return 2
        print(reply, flush=True)
        return 0
    except RelayError as error:
        print(json.dumps({"error": str(error)}), file=sys.stderr)
        return 1
    except (KeyboardInterrupt, EOFError):
        print("Stopped waiting. An already delivered request may still receive a reply.", file=sys.stderr)
        return 130
    except Exception:
        print('{"error":"operation_failed_details_redacted"}', file=sys.stderr)
        return 1
    finally:
        if mailbox:
            mailbox.close()


if __name__ == "__main__":
    sys.exit(main())
