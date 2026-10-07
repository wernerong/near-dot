"""Synthetic missing-event-data and stalled-reply regressions; no live-dot claims."""
import json
import unittest
from unittest.mock import patch

import relay
import test_relay as fixtures
from desktop import dispatch


class RecoveryTests(unittest.TestCase):
    setUp = fixtures.RelayTests.setUp
    tearDown = fixtures.RelayTests.tearDown

    def submitted(self, text='Synthetic submitted message'):
        self.r.subscribe(self.params)
        mid = self.r.queue(text)
        self.r.flush(mid)
        return mid

    def test_missing_event_data_recovers_only_submitted_unanswered_messages(self):
        mid = self.submitted()
        draft = self.r.queue('Synthetic unsent draft')
        answered = self.submitted('Synthetic answered message')
        self.r.tool('reply_to_test_message', {'message_id': answered, 'reply': 'Synthetic answer'})
        terminal = self.submitted('Synthetic terminal failure')
        self.r.db.execute('UPDATE messages SET delivered=2 WHERE id=?', (terminal,))
        self.r.db.commit()
        expected = {'messages': [{'message_id': mid, 'text': 'Synthetic submitted message'}], 'has_more': False}
        for args in ({}, {'message_id': 'pending'}):
            result = self.r.dispatch('tools/call', {'name': 'read_test_message', 'arguments': args})
            self.assertEqual(json.loads(result['content'][0]['text']), expected)
        self.assertEqual(self.r.db.execute('SELECT delivered FROM messages WHERE id=?', (draft,)).fetchone()[0], 0)
        with self.assertRaises(relay.RelayError):
            self.r.tool('read_test_message', {'message_id': 'synthetic-unknown-id'})

    def test_pending_batch_is_bounded_and_drains_using_original_reply_ids(self):
        self.r.subscribe(self.params)
        for _ in range(relay.PENDING_LIMIT + 1):
            self.r.queue('Synthetic batch message')
        self.r.flush()
        batch = self.r.tool('read_test_message', {})
        self.assertEqual(len(batch['messages']), relay.PENDING_LIMIT)
        self.assertTrue(batch['has_more'])
        for item in batch['messages']:
            self.r.tool('reply_to_test_message', {'message_id': item['message_id'], 'reply': 'Synthetic answer'})
        rest = self.r.tool('read_test_message', {})
        self.assertEqual(len(rest['messages']), 1)
        self.assertFalse(rest['has_more'])

    def test_pending_recovery_respects_expired_owner_grant(self):
        self.submitted()
        self.r.db.execute('UPDATE proof_window SET deadline=0')
        self.r.db.commit()
        for args in ({}, {'message_id': 'pending'}):
            with self.assertRaisesRegex(relay.RelayError, 'proof_window_expired'):
                self.r.tool('read_test_message', args)

    def test_stalled_reply_reminder_preserves_message_and_restarts_wait_after_restart(self):
        with patch('relay.time.time', return_value=1000):
            mid = self.submitted()
        event_id = self.calls[-1]['eventId']
        with patch('relay.time.time', return_value=1179):
            with self.assertRaisesRegex(relay.RelayError, 'reply_retry_too_soon'):
                self.r.retry(mid)
        with patch('relay.time.time', return_value=1180):
            self.r.retry(mid)
        reminder = self.calls[-1]
        self.assertEqual(reminder['data']['message_id'], mid)
        self.assertNotEqual(reminder['eventId'], event_id)
        self.assertEqual(self.r.status()['messages'], 1)
        self.r.close()
        self.r = relay.Relay(self.temp.name)
        with patch('relay.time.time', return_value=1181):
            with self.assertRaisesRegex(relay.RelayError, 'reply_retry_too_soon'):
                self.r.retry(mid)
            self.assertEqual(self.r.tool('read_test_message', {})['messages'][0]['message_id'], mid)
            self.r.tool('reply_to_test_message', {'message_id': mid, 'reply': 'Synthetic recovered answer'})
            self.r.tool('reply_to_test_message', {'message_id': mid, 'reply': 'Synthetic recovered answer'})
        self.assertEqual(self.r.status()['tool_replies'], 1)

    def test_failed_reminder_transport_retry_keeps_new_event_id(self):
        with patch('relay.time.time', return_value=1000):
            mid = self.submitted()
        seen = []
        def offline(*args):
            seen.append(args[3])
            return 503, b''
        self.r.post = offline
        with patch('relay.time.time', return_value=1200):
            for _ in range(2):
                with self.assertRaises(relay.RelayError):
                    self.r.retry(mid)
            # Receipt can fail after the host has already processed the event.
            self.assertEqual(self.r.tool('read_test_message', {})['messages'][0]['message_id'], mid)
        self.assertEqual(seen[0], seen[1])
        self.assertEqual(self.r.status()['messages'], 1)

    def test_delayed_reply_wins_over_retry_and_unsent_replied_rows_are_not_delivered(self):
        mid = self.submitted()
        self.r.tool('reply_to_test_message', {'message_id': mid, 'reply': 'Synthetic late reply'})
        before = len(self.calls)
        self.r.retry(mid)
        self.r.db.execute('UPDATE messages SET delivered=0 WHERE id=?', (mid,))
        self.r.db.commit()
        self.r.flush(mid)
        self.assertEqual(len(self.calls), before)

    def test_terminal_rejection_cannot_be_reminded(self):
        mid = self.submitted()
        self.r.db.execute('UPDATE messages SET delivered=2 WHERE id=?', (mid,))
        self.r.db.commit()
        with self.assertRaisesRegex(relay.RelayError, 'message_not_retryable'):
            self.r.retry(mid)

    def test_desktop_retry_recovers_acknowledged_message_and_honors_disconnect(self):
        with patch('relay.time.time', return_value=1000):
            mid = self.submitted()
        with patch('desktop.snapshot', return_value={'connected': False}):
            with self.assertRaisesRegex(relay.RelayError, 'connection_unavailable'):
                dispatch(self.r, {'operation': 'retry', 'messageId': mid})
        with patch('desktop.snapshot', return_value={'connected': True}), patch('relay.time.time', return_value=1200):
            dispatch(self.r, {'operation': 'retry', 'messageId': mid})
        self.assertEqual(len([c for c in self.calls if 'eventId' in c]), 2)
        self.assertEqual(self.r.status()['messages'], 1)

    def test_legacy_mailbox_migration_retains_content_and_recovery(self):
        with patch('relay.time.time', return_value=1000):
            mid = self.submitted()
        self.r.db.execute('ALTER TABLE messages DROP COLUMN last_attempt')
        self.r.db.commit()
        self.r.close()
        self.r = relay.Relay(self.temp.name, lambda *args: (200, b''))
        row = self.r.db.execute('SELECT body,delivered,last_attempt FROM messages WHERE id=?', (mid,)).fetchone()
        self.assertEqual(tuple(row), ('Synthetic submitted message', 1, 0))
        with patch('relay.time.time', return_value=1200):
            self.r.retry(mid)
            self.assertEqual(self.r.tool('read_test_message', {})['messages'][0]['message_id'], mid)


if __name__ == '__main__':
    unittest.main()
