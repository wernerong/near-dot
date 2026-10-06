"""Synthetic adapter security and delivery tests, not live-dot evidence."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from relay import Relay, RelayError
from desktop import dispatch, snapshot


class DesktopTests(unittest.TestCase):
    def test_snapshot_omits_callback_secrets_and_contains_only_mailbox_history(self):
        with tempfile.TemporaryDirectory() as state:
            state = str(Path(state).resolve() / "synthetic-fixture")
            relay = Relay(state)
            mid = relay.queue('Explicit synthetic desktop test')
            relay.tool('reply_to_test_message', {'message_id':mid, 'reply':'Synthetic reply fixture'})
            with patch('desktop.local_health', return_value={'live':False}):
                value = snapshot(relay)
            self.assertFalse(value['connected'])
            self.assertEqual(set(value), {'connected','transportRunning','expiresIn','state','messages'})
            self.assertEqual(value['messages'][0]['reply'], 'Synthetic reply fixture')
            relay.close()

    def test_disconnected_send_and_unknown_operations_do_not_queue(self):
        with tempfile.TemporaryDirectory() as state:
            state = str(Path(state).resolve() / "synthetic-fixture")
            relay = Relay(state)
            with patch('desktop.local_health', return_value={'live':False}):
                for request in [{'operation':'send','text':'Explicit synthetic fixture'},
                                {'operation':'extend','hours':24},
                                {'operation':'send','text':'fixture','command':'untrusted'}]:
                    with self.assertRaises(RelayError): dispatch(relay,request)
            self.assertEqual(relay.status()['messages'],0)
            relay.close()

    def test_delivery_failure_preserves_queued_message_for_same_id_retry(self):
        with tempfile.TemporaryDirectory() as state:
            state = str(Path(state).resolve() / "synthetic-fixture")
            relay = Relay(state)
            with patch('desktop.snapshot', return_value={'connected':True}), patch.object(relay,'flush',side_effect=RelayError('synthetic_failure')):
                dispatch(relay, {'operation':'send','text':'Explicit synthetic fixture'})
            self.assertEqual(relay.status()['messages'],1)
            self.assertEqual(relay.status()['acknowledged_events'],0)
            relay.close()


if __name__ == '__main__': unittest.main()
