"""Owner-only relay storage on POSIX and Windows. No credential diagnostics."""
import os
from pathlib import Path
import stat


def state_directory():
    if os.name == 'nt':
        return Path(os.environ['LOCALAPPDATA']) / 'Near Dot/live-connection'
    return Path.home() / 'Library/Application Support/Near Dot/transport-proof'


if os.name == 'nt':
    import ctypes as c
    from ctypes import wintypes as w
    adv = c.WinDLL('advapi32', use_last_error=True)
    kernel = c.WinDLL('kernel32', use_last_error=True)
    adv.ConvertStringSecurityDescriptorToSecurityDescriptorW.argtypes = [w.LPCWSTR, w.DWORD, c.POINTER(c.c_void_p), c.c_void_p]
    adv.ConvertStringSecurityDescriptorToSecurityDescriptorW.restype = w.BOOL
    adv.GetNamedSecurityInfoW.argtypes = [w.LPCWSTR, w.DWORD, w.DWORD, c.POINTER(c.c_void_p), c.c_void_p, c.POINTER(c.c_void_p), c.c_void_p, c.POINTER(c.c_void_p)]
    adv.GetNamedSecurityInfoW.restype = w.DWORD
    adv.ConvertSecurityDescriptorToStringSecurityDescriptorW.argtypes = [c.c_void_p, w.DWORD, w.DWORD, c.POINTER(w.LPWSTR), c.c_void_p]
    adv.ConvertSecurityDescriptorToStringSecurityDescriptorW.restype = w.BOOL
    adv.SetFileSecurityW.argtypes = [w.LPCWSTR, w.DWORD, c.c_void_p]
    adv.SetFileSecurityW.restype = w.BOOL
    kernel.LocalFree.argtypes = [c.c_void_p]
    kernel.LocalFree.restype = c.c_void_p
    kernel.GetCurrentProcess.restype = w.HANDLE
    kernel.CloseHandle.argtypes = [w.HANDLE]
    adv.OpenProcessToken.argtypes = [w.HANDLE, w.DWORD, c.POINTER(w.HANDLE)]
    adv.GetTokenInformation.argtypes = [w.HANDLE, c.c_int, c.c_void_p, w.DWORD, c.POINTER(w.DWORD)]
    adv.ConvertSidToStringSidW.argtypes = [c.c_void_p, c.POINTER(w.LPWSTR)]

    def user_sid():
        token = w.HANDLE()
        if not adv.OpenProcessToken(kernel.GetCurrentProcess(), 8, c.byref(token)):
            raise ValueError('Private storage unavailable.')
        try:
            length = w.DWORD()
            adv.GetTokenInformation(token, 1, None, 0, c.byref(length))
            buffer = c.create_string_buffer(length.value)
            if not adv.GetTokenInformation(token, 1, buffer, length, c.byref(length)):
                raise ValueError('Private storage unavailable.')
            sid = c.cast(buffer, c.POINTER(c.c_void_p))[0]
            value = w.LPWSTR()
            if not adv.ConvertSidToStringSidW(sid, c.byref(value)):
                raise ValueError('Private storage unavailable.')
            try:
                return value.value
            finally:
                kernel.LocalFree(value)
        finally:
            kernel.CloseHandle(token)

    def protect_new_directory(path):
        # Protect the empty directory before writing any private data. No broad
        # administrators/SYSTEM grants: only this user's SID can read it.
        descriptor = c.c_void_p()
        sddl = 'D:P(A;OICI;FA;;;' + user_sid() + ')'
        if not adv.ConvertStringSecurityDescriptorToSecurityDescriptorW(sddl, 1, c.byref(descriptor), None):
            raise ValueError('Private storage unavailable.')
        try:
            if not adv.SetFileSecurityW(str(path), 4 | 0x80000000, descriptor):
                raise ValueError('Private storage unavailable.')
        finally:
            kernel.LocalFree(descriptor)

    def check_windows(path):
        owner, acl, descriptor = c.c_void_p(), c.c_void_p(), c.c_void_p()
        if adv.GetNamedSecurityInfoW(str(path), 1, 1 | 4, c.byref(owner), None, c.byref(acl), None, c.byref(descriptor)):
            raise ValueError('Private file permissions required.')
        value = w.LPWSTR()
        try:
            if not acl.value or not adv.ConvertSecurityDescriptorToStringSecurityDescriptorW(descriptor, 1, 1 | 4, c.byref(value), None):
                raise ValueError('Private file permissions required.')
            import re
            sddl = value.value
            sid = user_sid()
            # Reject every ACE other than an allow for the current user. This
            # also rejects a null DACL, Everyone, inherited public access and
            # unfamiliar conditional/object ACEs rather than guessing.
            aces = re.findall(r'\(([^()]*)\)', sddl)
            if not sddl.startswith('O:' + sid + 'D:') or not aces:
                raise ValueError('Private file permissions required.')
            for ace in aces:
                fields = ace.split(';')
                if len(fields) != 6 or fields[0] != 'A' or fields[5] != sid:
                    raise ValueError('Private file permissions required.')
        finally:
            if value:
                kernel.LocalFree(value)
            kernel.LocalFree(descriptor)


def reject_links(path):
    for item in [path, *path.parents]:
        if item.is_symlink() or (item.exists() and getattr(item.lstat(), 'st_file_attributes', 0) & 0x400):
            raise ValueError('Private files cannot use links or reparse points.')


def private_path(path):
    path = Path(path).absolute()
    reject_links(path)
    if path.exists():
        if os.name == 'nt':
            check_windows(path)
        elif path.stat().st_uid != os.getuid() or stat.S_IMODE(path.stat().st_mode) & 0o077:
            raise ValueError('Private file permissions required.')
    return path


def private_directory(path):
    path = Path(path).absolute()
    reject_links(path)
    if not path.exists():
        path.mkdir(parents=True, mode=0o700)
        if os.name == 'nt':
            protect_new_directory(path)
    return private_path(path)


def write_new(path, value):
    path = private_path(path)
    private_path(path.parent)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0), 0o600)
    with os.fdopen(descriptor, 'w', encoding='utf-8') as stream:
        stream.write(value)
        stream.flush()
        os.fsync(stream.fileno())
    private_path(path)
