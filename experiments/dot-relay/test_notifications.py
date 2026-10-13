"""Synthetic receiver, opt-in, restart, deduplication and bounded-storage tests."""
import json
import sqlite3
from pathlib import Path
import tempfile
import unittest
from notifications import Notifications, NotificationError, LIMIT
from privacy import private_directory, write_new
from relay import Relay, RelayError
from desktop import dispatch
from unittest.mock import patch


class NotificationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.state = private_directory(Path(self.temp.name).resolve() / 'synthetic-notifications')
        self.inbox = Notifications(self.state)

    def test_disabled_receiver_has_no_database_and_rejects_remote_writes(self):
        self.assertEqual(self.inbox.pending(), [])
        with self.assertRaises(NotificationError):
            self.inbox.notify({'notification_id': 'synthetic_001'})
        self.assertFalse(self.inbox.path.exists())

    def test_received_notice_survives_restart_and_ack_does_not_consume_a_late_notice(self):
        self.inbox.configure(True)
        self.inbox.notify({'notification_id': 'synthetic_first', 'preview': 'Synthetic reply'})
        seen = [row['id'] for row in Notifications(self.state).pending()]
        self.inbox.notify({'notification_id': 'synthetic_later'})
        self.inbox.acknowledge(seen)
        self.assertEqual([row['id'] for row in Notifications(self.state).pending()], ['synthetic_later'])

    def test_repeated_notice_keeps_one_slot_and_cannot_replace_its_preview(self):
        self.inbox.configure(True)
        value = {'notification_id': 'synthetic_repeat', 'preview': 'Synthetic original'}
        self.assertEqual(self.inbox.notify(value), self.inbox.notify(value))
        self.assertEqual(len(self.inbox.pending()), 1)
        with self.assertRaises(NotificationError):
            self.inbox.notify({**value, 'preview': 'Synthetic replacement'})
        self.inbox.acknowledge(['synthetic_repeat'])
        self.inbox.notify(value)
        self.assertEqual(self.inbox.pending(), [])

    def test_capacity_preserves_unseen_notices_and_only_recycles_consumed_notices(self):
        self.inbox.configure(True)
        for index in range(LIMIT):
            self.inbox.notify({'notification_id': f'synthetic_{index:03d}'})
        with self.assertRaises(NotificationError):
            self.inbox.notify({'notification_id': 'synthetic_overflow'})
        self.inbox.acknowledge(['synthetic_000'])
        self.inbox.notify({'notification_id': 'synthetic_overflow'})
        self.assertEqual(len(self.inbox.pending()), LIMIT)
        self.assertNotIn('synthetic_000', [row['id'] for row in self.inbox.pending()])

    def test_disable_preserves_pending_notice_and_history(self):
        self.inbox.configure(True)
        self.inbox.notify({'notification_id': 'synthetic_saved'})
        self.inbox.configure(False)
        self.assertEqual(self.inbox.pending(), [])
        self.inbox.configure(True)
        self.assertEqual(len(self.inbox.pending()), 1)

    def test_unknown_and_corrupt_notification_settings_are_preserved(self):
        for raw in ['broken', json.dumps({'schema': 99, 'enabled': True})]:
            if self.inbox.config.exists():
                self.inbox.config.unlink()
            write_new(self.inbox.config, raw)
            with self.assertRaises(NotificationError):
                self.inbox.configure(False)
            self.assertEqual(self.inbox.config.read_text(), raw)

    def test_future_notification_database_is_preserved(self):
        self.inbox.configure(True)
        self.inbox.notify({'notification_id': 'synthetic_future'})
        db = sqlite3.connect(self.inbox.path)
        try:
            db.execute('PRAGMA user_version=99')
            db.commit()
        finally:
            db.close()
        original = self.inbox.path.read_bytes()
        with self.assertRaises(NotificationError):
            self.inbox.pending()
        with self.assertRaises(NotificationError):
            self.inbox.notify({'notification_id': 'synthetic_new'})
        self.assertEqual(self.inbox.path.read_bytes(), original)
        self.inbox.configure(False)
        with self.assertRaises(NotificationError):
            self.inbox.configure(True)
        self.assertFalse(self.inbox.enabled())
        self.assertEqual(self.inbox.path.read_bytes(), original)

    def test_remote_input_cannot_supply_paths_history_or_executable_arguments(self):
        self.inbox.configure(True)
        for value in [{'notification_id': '../synthetic'}, {'notification_id': 'synthetic_001', 'preview': 'x' * 161},
                      {'notification_id': 'synthetic_001', 'path': '/synthetic'}, {'notification_id': 12345678},
                      {'notification_id': 'synthetic_001', 'preview': '<synthetic>\x00'}]:
            with self.assertRaises(NotificationError):
                self.inbox.notify(value)
        self.assertEqual(self.inbox.pending(), [])

    def test_plugin_notification_does_not_queue_messages_or_require_an_event_subscription(self):
        mailbox = Relay(self.state, post=lambda *args: self.fail('A notification must not send a webhook'))
        self.addCleanup(mailbox.close)
        self.assertNotIn('notify_reply', [tool['name'] for tool in mailbox.dispatch('tools/list', {})['tools']])
        self.inbox.configure(True)
        self.assertIn('notify_reply', [tool['name'] for tool in mailbox.dispatch('tools/list', {})['tools']])
        mailbox.tool('notify_reply', {'notification_id': 'synthetic_plugin_reply', 'preview': 'Synthetic normal-chat reply'})
        self.assertEqual(mailbox.status()['messages'], 0)
        self.assertFalse(mailbox.status()['active_subscription'])
        with patch('desktop.local_health', return_value={'live': False}):
            value = dispatch(mailbox, {'operation': 'notification-snapshot'})
            self.assertEqual(value['messages'], [])
            self.assertEqual(value['notifications'][0]['preview'], 'Synthetic normal-chat reply')
            dispatch(mailbox, {'operation': 'ack-notifications', 'notificationIds': ['synthetic_plugin_reply']})
        self.assertEqual(self.inbox.pending(), [])

    def test_notification_tool_respects_the_existing_fixed_proof_deadline(self):
        mailbox = Relay(self.state)
        self.addCleanup(mailbox.close)
        self.inbox.configure(True)
        with mailbox.db:
            mailbox.db.execute('INSERT INTO proof_window VALUES(1,0)')
        with self.assertRaises(RelayError):
            mailbox.tool('notify_reply', {'notification_id': 'synthetic_expired'})
        self.assertEqual(self.inbox.pending(), [])
        write_new(self.state / 'connection.json', '{"tunnel_id":"synthetic-expired"}')
        write_new(self.state / 'runtime.key', 'synthetic-expired-runtime-key')
        with patch('desktop.local_health', return_value={'live': True, 'startup_ready': True, 'poll_failures': 0}):
            value = dispatch(mailbox, {'operation': 'notification-snapshot'})
        self.assertFalse(value['connected'])
        self.assertEqual(value['state'], 'expired')

    def test_cached_two_tool_catalog_can_send_an_idempotent_notification_without_chat_or_events(self):
        mailbox = Relay(self.state, post=lambda *args: self.fail('A notice must not send an event'))
        self.addCleanup(mailbox.close)
        self.assertNotIn('reply_notification', mailbox.tool('read_test_message', {'message_id': 'connection-check'}))
        self.assertFalse(self.inbox.path.exists())
        self.inbox.configure(True)
        check = mailbox.tool('read_test_message', {'message_id': 'connection-check'})
        slot = check['reply_notification']
        self.assertFalse(check['is_message'])
        self.assertFalse(slot['is_chat_message'])
        self.assertEqual(slot['max_preview_characters'], 160)
        self.assertEqual(slot['reply_tool'], 'reply_to_test_message')
        self.assertEqual(self.inbox.pending(), [])
        self.assertNotEqual(slot['message_id'], mailbox.tool('read_test_message', {'message_id': 'connection-check'})['reply_notification']['message_id'])
        arguments = {'message_id': slot['message_id'], 'reply': 'Synthetic cached-catalog reply'}
        first = mailbox.tool('reply_to_test_message', arguments)
        self.assertEqual(first, mailbox.tool('reply_to_test_message', arguments))
        self.assertEqual(first['kind'], 'reply_notification')
        self.assertEqual(len(self.inbox.pending()), 1)
        self.assertEqual(mailbox.status()['messages'], 0)
        self.assertFalse(mailbox.status()['active_subscription'])
        with self.assertRaises(NotificationError):
            mailbox.tool('reply_to_test_message', {**arguments, 'reply': 'Synthetic conflicting reply'})
        self.inbox.acknowledge([first['notification_id']])
        mailbox.tool('reply_to_test_message', arguments)
        self.assertEqual(self.inbox.pending(), [])

    def test_compatibility_slot_rejects_disabled_expired_invalid_or_oversized_notices(self):
        mailbox = Relay(self.state)
        self.addCleanup(mailbox.close)
        self.inbox.configure(True)
        slot = mailbox.tool('read_test_message', {'message_id': 'connection-check'})['reply_notification']
        arguments = {'message_id': slot['message_id'], 'reply': 'Synthetic notice'}
        with self.assertRaises(NotificationError):
            mailbox.tool('reply_to_test_message', {**arguments, 'reply': 'x' * 161})
        with self.assertRaises(RelayError):
            mailbox.tool('reply_to_test_message', {**arguments, 'message_id': 'notification:../synthetic'})
        self.inbox.configure(False)
        with self.assertRaises(NotificationError):
            mailbox.tool('reply_to_test_message', arguments)
        self.inbox.configure(True)
        with mailbox.db:
            mailbox.db.execute('INSERT INTO proof_window VALUES(1,0)')
        self.assertNotIn('reply_notification', mailbox.tool('read_test_message', {'message_id': 'connection-check'}))
        with self.assertRaises(RelayError):
            mailbox.tool('reply_to_test_message', arguments)
        self.assertEqual(self.inbox.pending(), [])
        self.assertEqual(mailbox.status()['messages'], 0)


if __name__ == '__main__':
    unittest.main()
