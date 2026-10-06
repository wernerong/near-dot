#!/usr/bin/env python3
"""Private desktop preview adapter. Fixed operations, no credentials in responses."""
import json
import os
import sys
from pathlib import Path
from relay import Relay, RelayError, MAX_TEXT
from connect import local_health
from privacy import state_directory, private_path

STATE = state_directory()


def snapshot(mailbox):
    status = mailbox.status()
    health = local_health()
    remaining = status['proof_seconds_remaining']
    paused = private_path(mailbox.state / 'paused').exists()
    configured = os.name != 'nt' or private_path(mailbox.state / 'connection.json').exists()
    connected = bool(configured and not paused and status['active_subscription'] and health.get('live') and
                     health.get('startup_ready') and health.get('poll_failures') == 0)
    rows = mailbox.db.execute('SELECT id,body,created,delivered,reply FROM messages ORDER BY created DESC LIMIT 50').fetchall()
    return {'connected': connected, 'transportRunning': bool(health.get('live')), 'expiresIn': remaining,
            'state': 'paused' if paused else ('unconfigured' if not configured else ('connected' if connected else ('expired' if remaining == 0 else ('awaiting-dot' if health.get('live') else 'disconnected')))),
            'messages': [{'id': r['id'], 'text': r['body'], 'created': r['created'],
                          'delivered': r['delivered'], 'reply': r['reply']} for r in reversed(rows)]}


def dispatch(mailbox, request):
    if request == {'operation': 'snapshot'}:
        return snapshot(mailbox)
    if set(request) == {'operation', 'text'} and request['operation'] == 'send':
        text = request['text']
        if not isinstance(text, str) or not text.strip() or len(text) > MAX_TEXT:
            raise RelayError('invalid_message')
        if not snapshot(mailbox)['connected']:
            raise RelayError('connection_unavailable')
        mid = mailbox.queue(text.strip())
        # Queue is durable before delivery. A failed delivery is returned as a
        # queued message so the UI never invites an accidental duplicate send.
        try:
            mailbox.flush(mid)
        except Exception:
            pass
        return snapshot(mailbox)
    if set(request) == {'operation', 'messageId'} and request['operation'] == 'retry':
        if not snapshot(mailbox)['connected']:
            raise RelayError('connection_unavailable')
        mid = request['messageId']
        row = mailbox.db.execute('SELECT delivered,reply FROM messages WHERE id=?', (mid,)).fetchone()
        if row is None or row['delivered'] != 0 or row['reply'] is not None:
            raise RelayError('message_not_retryable')
        mailbox.flush(mid)
        return snapshot(mailbox)
    raise RelayError('operation_not_allowed')


def main():
    # Do not create a mailbox merely because the application was opened.
    mailbox = Relay(STATE) if (STATE / 'proof.sqlite3').exists() or (STATE / 'connection.json').exists() else None
    try:
        while True:
            line = sys.stdin.buffer.readline(16385)
            if not line:
                break
            if len(line) > 16384:
                break
            try:
                request = json.loads(line)
                if not isinstance(request, dict):
                    raise RelayError('invalid_request')
                if mailbox is None:
                    if request != {'operation': 'snapshot'}:
                        raise RelayError('connection_unavailable')
                    value = {'connected': False, 'transportRunning': False, 'state': 'unconfigured', 'expiresIn': None, 'messages': []}
                else:
                    value = dispatch(mailbox, request)
                result = {'ok': value}
            except Exception:
                result = {'error': 'The private connection is unavailable. Your saved messages are preserved.'}
            print(json.dumps(result), flush=True)
    finally:
        if mailbox:
            mailbox.close()


if __name__ == '__main__':
    main()
