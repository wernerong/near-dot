"""Native per-user connection prompt. Credentials never pass through the webview."""
import json
import os
from pathlib import Path
import sys
import threading
from privacy import private_directory, private_path, state_directory, write_new


def watch_parent_input():
    def wait_for_exit():
        try:
            os.read(0, 1)
        finally:
            os._exit(1)
    threading.Thread(target=wait_for_exit, daemon=True).start()


def credentials():
    if os.name != 'nt':
        raise ValueError('Use the reviewed local Mac connection setup.')
    import ctypes as c
    from ctypes import wintypes as w
    class Info(c.Structure):
        _fields_ = [('size', w.DWORD), ('parent', w.HWND), ('message', w.LPCWSTR),
                    ('caption', w.LPCWSTR), ('banner', w.HANDLE)]
    api = c.WinDLL('credui')
    api.CredUIPromptForCredentialsW.argtypes = [c.POINTER(Info), w.LPCWSTR, c.c_void_p, w.DWORD,
                                               w.LPWSTR, w.DWORD, w.LPWSTR, w.DWORD, c.POINTER(w.BOOL), w.DWORD]
    api.CredUIPromptForCredentialsW.restype = w.DWORD
    info = Info(c.sizeof(Info), None,
                'Username: your tunnel ID (tunnel_…). Password: your runtime key.\n'
                'Use your own OpenAI tunnel with Tunnels Read + Use permission.\n'
                'Connect enables this device until you disconnect or revoke the key.', 'Connect my dot', None)
    username, password, save = c.create_unicode_buffer(513), c.create_unicode_buffer(2561), w.BOOL(False)
    try:
        result = api.CredUIPromptForCredentialsW(c.byref(info), 'Near Dot local connection', None, 0,
                                                username, len(username), password, len(password), c.byref(save),
                                                0x40000 | 0x2 | 0x80)  # Generic, do not persist, always show.
        if result == 1223:
            raise ValueError('Connection setup cancelled. Nothing was saved.')
        if result:
            raise ValueError('The native connection prompt could not open.')
        return username.value.strip(), password.value.strip()
    finally:
        c.memset(c.addressof(password), 0, c.sizeof(password))


def configure(state, tunnel_id, key):
    if (not tunnel_id.startswith('tunnel_') or len(tunnel_id) > 200 or
            not all(ch.isascii() and (ch.isalnum() or ch in '_-') for ch in tunnel_id)):
        raise ValueError('Enter the tunnel ID from your own OpenAI setup.')
    if not key.startswith('sk-') or not 30 <= len(key) <= 2560 or any(ch.isspace() for ch in key):
        raise ValueError('The runtime key format was not recognized.')
    private_directory(state)
    # Never silently replace an existing connection or its key/history.
    paths = [private_path(state / name) for name in ('runtime.key', 'connection.json', 'consent.json')]
    if any(path.exists() for path in paths):
        raise ValueError('This device already has a connection. Reconnect, or choose Forget connection before replacing credentials.')
    created = []
    try:
        for path, value in zip(paths, [key, json.dumps({'tunnel_id': tunnel_id}), json.dumps({'schema': 1, 'persistent': True})]):
            write_new(path, value)
            created.append(path)
    except Exception:
        for path in created:
            path.unlink()
        raise


def main():
    try:
        state = state_directory()
        if sys.argv[1:] in (['check'], ['automatic-check']):
            private_path(state)
            for name in ('runtime.key', 'connection.json', 'consent.json'):
                private_path(state / name)
            if not all((state / name).is_file() for name in ('runtime.key', 'connection.json')):
                raise ValueError('Choose Connect my dot to authorize this device first.')
            if sys.argv[1:] == ['automatic-check'] and private_path(state / 'paused').exists():
                raise ValueError('This device is disconnected. Use Reconnect to resume.')
        elif sys.argv[1:] == ['configure']:
            watch_parent_input()
            configure(state, *credentials())
        elif sys.argv[1:] == ['pause']:
            private_directory(state)
            paused = private_path(state / 'paused')
            if not paused.exists():
                write_new(paused, 'paused')
        elif sys.argv[1:] == ['resume']:
            paused = private_path(state / 'paused')
            if paused.exists():
                paused.unlink()
        elif sys.argv[1:] == ['forget']:
            private_directory(state)
            from relay import Relay
            mailbox = Relay(state)
            try:
                with mailbox.db:
                    mailbox.db.execute('DELETE FROM subscription')
                    mailbox.db.execute('DELETE FROM proof_window')
            finally:
                mailbox.close()
            for name in ('runtime.key', 'connection.json', 'consent.json', 'paused', 'health.url'):
                path = private_path(state / name)
                if path.exists():
                    path.unlink()
        else:
            raise ValueError('Setup operation unavailable.')
        print(json.dumps({'ok': True}), flush=True)
        return 0
    except ValueError as error:
        print(json.dumps({'error': str(error)}), flush=True)
    except Exception:
        print(json.dumps({'error': 'Connection setup failed. Private details were suppressed.'}), flush=True)
    return 1


if __name__ == '__main__':
    sys.exit(main())
