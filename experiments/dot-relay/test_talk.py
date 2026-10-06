"""Synthetic CLI persistence test, separate from the live dot evidence."""

import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from relay import Relay
import talk


class TalkTests(unittest.TestCase):
    def test_saved_reply_can_be_read_offline_without_redelivery(self):
        with tempfile.TemporaryDirectory() as state:
            state = str(Path(state).resolve() / "synthetic-fixture")
            mailbox = Relay(state)
            mid = mailbox.queue("Explicit synthetic persistence fixture")
            mailbox.tool("reply_to_test_message", {"message_id": mid, "reply": "Synthetic unit fixture reply"})
            mailbox.close()
            output = io.StringIO()
            with patch("sys.argv", ["talk.py", "--state", state, "--resume", mid]), \
                    patch.object(Relay, "flush", side_effect=AssertionError("Must not redeliver")), \
                    contextlib.redirect_stdout(output):
                self.assertEqual(talk.main(), 0)
            self.assertEqual(output.getvalue().strip(), "Synthetic unit fixture reply")


if __name__ == "__main__":
    unittest.main()
