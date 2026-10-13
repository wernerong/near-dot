"""Opt-in local reply notifications. No browser access or conversation export."""
import json
import os
from pathlib import Path
import re
import sqlite3
import time
import uuid
from privacy import private_directory, private_path, write_new

LIMIT = 50
MAX_PREVIEW = 160
ID = re.compile(r'[A-Za-z0-9_-]{8,128}')


class NotificationError(ValueError):
    pass


class Notifications:
    def __init__(self, state):
        self.state = Path(state)
        self.config = private_path(self.state / 'notifications.json')
        self.path = private_path(self.state / 'notifications.sqlite3')

    def enabled(self):
        if not self.config.exists():
            return False
        if self.config.stat().st_size > 4096:
            raise NotificationError('Invalid notification settings; preserved.')
        try:
            value = json.loads(self.config.read_text(encoding='utf-8'))
            if set(value) != {'schema', 'enabled'} or type(value['schema']) is not int or value['schema'] != 1 or type(value['enabled']) is not bool:
                raise ValueError()
            return value['enabled']
        except (OSError, ValueError, KeyError, TypeError):
            raise NotificationError('Invalid notification settings; preserved.') from None

    def configure(self, enabled):
        if type(enabled) is not bool:
            raise NotificationError('Invalid notification choice.')
        current = self.enabled()  # Preserve unknown/corrupt settings, including on disable.
        if current == enabled:
            return
        if enabled and self.path.exists():
            db = self.database()  # Reject a future inbox before changing the opt-in.
            db.close()
        private_directory(self.state)
        staging = self.state / ('.notifications-' + uuid.uuid4().hex)
        try:
            write_new(staging, json.dumps({'schema': 1, 'enabled': enabled}))
            os.replace(staging, self.config)
            private_path(self.config)
        finally:
            if staging.exists():
                staging.unlink()

    def database(self):
        private_directory(self.state)
        private_path(self.path)
        if not self.path.exists():
            try:
                write_new(self.path, '')
            except FileExistsError:
                private_path(self.path)
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            version = db.execute('PRAGMA user_version').fetchone()[0]
            if version not in (0, 1):
                raise NotificationError('Notification storage needs a newer release; preserved.')
            columns = db.execute('PRAGMA table_info(notifications)').fetchall()
            if columns and [row['name'] for row in columns] != ['id', 'preview', 'created', 'seen']:
                raise NotificationError('Notification storage needs a newer release; preserved.')
            if version == 1 and not columns:
                raise NotificationError('Notification storage is invalid; preserved.')
            with db:
                if not columns:
                    db.execute('''CREATE TABLE IF NOT EXISTS notifications (
                        id TEXT PRIMARY KEY, preview TEXT NOT NULL, created REAL NOT NULL,
                        seen INTEGER NOT NULL DEFAULT 0)''')
                if version == 0:
                    db.execute('PRAGMA user_version=1')
        except Exception:
            db.close()
            raise
        return db

    def notify(self, arguments):
        if not self.enabled():
            raise NotificationError('Reply notifications are disabled in Near Dot Settings.')
        if not isinstance(arguments, dict) or not {'notification_id'} <= set(arguments) <= {'notification_id', 'preview'}:
            raise NotificationError('Invalid notification arguments.')
        notice_id = arguments['notification_id']
        preview = arguments.get('preview', '')
        if not isinstance(notice_id, str) or not ID.fullmatch(notice_id):
            raise NotificationError('Invalid notification ID.')
        if not isinstance(preview, str) or len(preview) > MAX_PREVIEW or '\x00' in preview:
            raise NotificationError('Invalid reply preview.')
        db = self.database()
        try:
            with db:
                db.execute('BEGIN IMMEDIATE')
                old = db.execute('SELECT preview FROM notifications WHERE id=?', (notice_id,)).fetchone()
                if old:
                    if old['preview'] != preview:
                        raise NotificationError('Conflicting repeated notification.')
                else:
                    count = db.execute('SELECT COUNT(*) FROM notifications').fetchone()[0]
                    if count >= LIMIT:
                        consumed = db.execute('SELECT id FROM notifications WHERE seen=1 ORDER BY created,id LIMIT 1').fetchone()
                        if not consumed:
                            raise NotificationError('The notification inbox is full. Open Near Dot before retrying.')
                        db.execute('DELETE FROM notifications WHERE id=?', (consumed['id'],))
                    db.execute('INSERT INTO notifications(id,preview,created) VALUES(?,?,?)',
                               (notice_id, preview, time.time()))
        finally:
            db.close()
        return {'accepted': True, 'notification_id': notice_id, 'kind': 'reply_notification'}

    def pending(self):
        if not self.enabled() or not self.path.exists():
            return []
        db = self.database()
        try:
            rows = db.execute('SELECT id,preview,created FROM notifications WHERE seen=0 ORDER BY created,id LIMIT ?', (LIMIT,)).fetchall()
            return [dict(row) for row in rows]
        finally:
            db.close()

    def acknowledge(self, ids):
        if not isinstance(ids, list) or not 1 <= len(ids) <= LIMIT or any(not isinstance(value, str) or not ID.fullmatch(value) for value in ids):
            raise NotificationError('Invalid notification acknowledgement.')
        if not self.enabled() or not self.path.exists():
            raise NotificationError('Notifications are unavailable.')
        db = self.database()
        try:
            with db:
                for notice_id in ids:
                    db.execute('UPDATE notifications SET seen=1 WHERE id=?', (notice_id,))
        finally:
            db.close()
